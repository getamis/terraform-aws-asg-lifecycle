import logging
import time

from kubernetes.client.rest import ApiException

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

MIRROR_POD_ANNOTATION_KEY = "kubernetes.io/config.mirror"
CONTROLLER_KIND_DAEMON_SET = "DaemonSet"

def cordon_node(api, node_name):
    """Marks the specified node as unschedulable, which means that no new pods can be launched on the
    node by the Kubernetes scheduler.
    """
    patch_body = {
        'apiVersion': 'v1',
        'kind': 'Node',
        'metadata': {
            'name': node_name
        },
        'spec': {
            'unschedulable': True
        }
    }

    api.patch_node(node_name, patch_body)


def remove_all_pods(api, node_name, poll=5):
    """Removes all Kubernetes pods from the specified node."""
    pods = get_evictable_pods(api, node_name)

    logger.debug('Number of pods to delete: ' + str(len(pods)))

    evict_until_completed(api, pods, poll)
    wait_until_empty(api, node_name, poll)


def pod_is_evictable(pod):
    if pod.metadata.annotations is not None and pod.metadata.annotations.get(MIRROR_POD_ANNOTATION_KEY):
        logger.info("Skipping mirror pod {}/{}".format(pod.metadata.namespace, pod.metadata.name))
        return False
    if pod.metadata.owner_references is None:
        return True
    for ref in pod.metadata.owner_references:
        if ref.controller is not None and ref.controller:
            if ref.kind == CONTROLLER_KIND_DAEMON_SET:
                logger.info("Skipping DaemonSet {}/{}".format(pod.metadata.namespace, pod.metadata.name))
                return False
    return True


def get_evictable_pods(api, node_name):
    field_selector = 'spec.nodeName=' + node_name
    pods = api.list_pod_for_all_namespaces(watch=False, field_selector=field_selector)
    return [pod for pod in pods.items if pod_is_evictable(pod)]


def evict_until_completed(api, pods, poll):
    pending = pods
    while True:
        pending = evict_pods(api, pending)
        if (len(pending)) <= 0:
            return
        time.sleep(poll)


def evict_pods(api, pods):
    remaining = []
    for pod in pods:
        logger.info('Evicting pod {} in namespace {}'.format(pod.metadata.name, pod.metadata.namespace))
        body = {
            'apiVersion': 'policy/v1beta1',
            'kind': 'Eviction',
            'deleteOptions': {},
            'metadata': {
                'name': pod.metadata.name,
                'namespace': pod.metadata.namespace
            }
        }
        try:
            api.create_namespaced_pod_eviction(pod.metadata.name, pod.metadata.namespace, body)
        except ApiException as err:
            if err.status == 429:
                remaining.append(pod)
                logger.warning("Pod {}/{} could not be evicted due to disruption budget. Will retry.".format(pod.metadata.namespace, pod.metadata.name))
            else:
                logger.exception("Unexpected error adding eviction for pod {}/{}".format(pod.metadata.namespace, pod.metadata.name))
        except:
            logger.exception("Unexpected error adding eviction for pod {}/{}".format(pod.metadata.namespace, pod.metadata.name))
    return remaining


def wait_until_empty(api, node_name, poll):
    logger.info("Waiting for evictions to complete")
    while True:
        pods = get_evictable_pods(api, node_name)
        if len(pods) <= 0:
            logger.info("All pods evicted successfully")
            return
        logger.debug("Still waiting for deletion of the following pods: {}".format(", ".join(map(lambda pod: pod.metadata.namespace + "/" + pod.metadata.name, pods))))
        time.sleep(poll)

def master_ready(api, asg_client, lb_client, ec2_client, asg_name, node_name, node_role, timeout):
    """Determines whether the K8s master node are ready"""

    # The asg instance refresh operaiton is not for master role
    if 'master' not in node_role:
        return True

    asg_info = asg_client.describe_auto_scaling_groups(
        AutoScalingGroupNames=[asg_name]
    )['AutoScalingGroups'][0]
    asg_instances = asg_info['Instances']
    asg_desired_capacity = asg_info['DesiredCapacity']
    asg_remain_instances = [instance['InstanceId'] for instance in asg_instances if 'Terminating' not in instance['LifecycleState']]

    # The master asg contain multiple nodes
    if asg_desired_capacity > 1:
        return True
 
    # There is only one node in the master asg, waiting for the node bind to lb
    waiting_timeout = time.time() + timeout

    lb_name = asg_client.describe_load_balancers(AutoScalingGroupName=asg_name)['LoadBalancers'][0]['LoadBalancerName']

    while True:
        if time.time() > waiting_timeout:
            logger.exception('timeout waiting for master node {} ready'.format(node_name))
            return False                

        try:
            lb_instances = lb_client.describe_load_balancers(LoadBalancerNames = [lb_name])['LoadBalancerDescriptions'][0]['Instances']

            for target_instance in lb_instances:
                if target_instance['InstanceId'] in asg_remain_instances:

                    target_instance_state = lb_client.describe_instance_health(
                        LoadBalancerName=lb_name,
                        Instances=[
                            {
                                'InstanceId': target_instance['InstanceId']
                            },
                        ]
                    )['InstanceStates'][0]['State']

                    if target_instance_state == 'InService':
                        master_instance = ec2_client.describe_instances(InstanceIds=[target_instance['InstanceId']])['Reservations'][0]['Instances'][0]
                        node_name = master_instance['PrivateDnsName']
                        instance_lifecycle = 'Ec2Spot' if 'InstanceLifecycle' in master_instance else 'OnDemand'
                        append_node_labels(api, node_name, node_role, instance_lifecycle)

                        return True

            time.sleep(10)

        except:
            logger.exception('There was an error waiting the node {} ready'.format(node_name))
            return False

def node_ready(api, node_name, timeout):
    """Determines whether the specified node is ready."""

    waiting_timeout = time.time() + timeout
    field_selector = 'metadata.name=' + node_name

    while True:
        if time.time() > waiting_timeout:
            logger.exception('timeout waiting for node {} launch'.format(node_name))
            return False

        try:
            # The node is still not been registered to K8s
            if not node_exists(api, node_name):
                time.sleep(10)
                continue

            node = api.list_node(pretty=True, field_selector=field_selector).items[0]

            for condition in node.status.conditions:
                if condition.type == 'Ready' and condition.status == 'True':
                    return True
                
            time.sleep(10)
        except:
            logger.exception('There was an error waiting the node {} ready'.format(node_name))
            return False

def node_exists(api, node_name):
    """Determines whether the specified node is still part of the cluster."""

    try:
        nodes = api.list_node(pretty=True).items
        node = next((n for n in nodes if n.metadata.name == node_name), None)

        return False if not node else True
    except:
        return False      

def append_node_labels(api, node_name, node_role, instance_lifecycle):

    node_role_label = "node-role.kubernetes.io/%s" % (node_role)
    
    patch_body = {
        "metadata": {
            "labels": {
                "lifecycle": instance_lifecycle,
                node_role_label: ""
            }
        }
    }

    try:
        api.patch_node(node_name, patch_body)
    except:
        logger.exception('There was an error appending labels to the node {} '.format(node_name))

def abandon_lifecycle_action(asg_client, auto_scaling_group_name, lifecycle_hook_name, instance_id):
    """Completes the lifecycle action with the ABANDON result, which stops any remaining actions,
    such as other lifecycle hooks.
    """
    asg_client.complete_lifecycle_action(LifecycleHookName=lifecycle_hook_name,
                                         AutoScalingGroupName=auto_scaling_group_name,
                                         LifecycleActionResult='ABANDON',
                                         InstanceId=instance_id)

def continue_lifecycle_action(asg_client, auto_scaling_group_name, lifecycle_hook_name, instance_id):
    """Completes the lifecycle action with the CONTINUE result, which continues the  remaining actions,
    such as other lifecycle hooks.
    """
    asg_client.complete_lifecycle_action(LifecycleHookName=lifecycle_hook_name,
                                         AutoScalingGroupName=auto_scaling_group_name,
                                         LifecycleActionResult='CONTINUE',
                                         InstanceId=instance_id)