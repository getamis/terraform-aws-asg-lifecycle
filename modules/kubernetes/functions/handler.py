import boto3
import json
import logging
import os.path
import time

from botocore.signers import RequestSigner
from kubernetes import client as k8s_client
from kubernetes import config as k8s_config
from kubernetes.client.rest import ApiException

from k8s_utils import (abandon_lifecycle_action, continue_lifecycle_action, cordon_node, node_exists, node_ready, append_node_labels, master_ready, remove_all_pods)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

KUBE_FILEPATH = '/tmp/kubeconfig'
REGION = os.environ['AWS_REGION']

ec2 = boto3.client('ec2', region_name=REGION)
asg = boto3.client('autoscaling', region_name=REGION)
elb = boto3.client('elb', region_name=REGION)
s3  = boto3.client('s3', region_name=REGION)

def hook_init(hook_payload):

    hook_info = {
        'cluster_name': os.environ.get('CLUSTER_NAME'),
        'kube_config_bucket': os.environ.get('KUBE_CONFIG_BUCKET'),
        'kube_config_object': os.environ.get('KUBE_CONFIG_OBJECT'),
        'node_role': os.environ.get('KUBERNETES_NODE_ROLE'),
        'launching_timeout': float(os.environ.get('LAUNCHING_TIMEOUT')),
        'terminating_timeout': float(os.environ.get('TERMINATING_TIMEOUT'))
    }

    hook_info['name'] = hook_payload['LifecycleHookName']
    hook_info['asg_name'] = hook_payload['AutoScalingGroupName']
    hook_info['transition'] = hook_payload['LifecycleTransition']
    hook_info['instance_id'] = hook_payload['EC2InstanceId']
    hook_info['destination'] = hook_payload['Destination']

    instance = ec2.describe_instances(InstanceIds=[hook_info['instance_id']])['Reservations'][0]['Instances'][0]

    hook_info['node_name'] = instance['PrivateDnsName']
    hook_info['instance_lifecycle'] = 'Ec2Spot' if 'InstanceLifecycle' in instance else 'OnDemand'

    logger.info("Processing %s event from auto scaling group %s, and the instance id is %s, private dns name is %s" % (hook_info['transition'], hook_info['asg_name'], hook_info['instance_id'], hook_info['node_name']))

    if not os.path.exists(KUBE_FILEPATH):
        if hook_info['kube_config_bucket']:
            logger.info('No kubeconfig file found. Downloading...')
            s3.download_file(hook_info['kube_config_bucket'], hook_info['kube_config_object'], KUBE_FILEPATH)
        else:
            logger.info('No kubeconfig file found.')

    k8s_config.load_kube_config(KUBE_FILEPATH)

    return k8s_client.CoreV1Api(), hook_info

def launch_node(k8s_api, hook_info):

    asg_desired_capacity = asg.describe_auto_scaling_groups(
        AutoScalingGroupNames=[hook_info['asg_name']]
    )['AutoScalingGroups'][0]['DesiredCapacity']

    if 'master' in hook_info['node_role'] and asg_desired_capacity == 1:
        continue_lifecycle_action(asg, hook_info['asg_name'], hook_info['name'], hook_info['instance_id'])

    else:
        if hook_info['destination'] == 'WarmPool':
            cordon_timeout = time.time() + hook_info['launching_timeout']
            loop = True
            while loop:
                try:
                    cordon_node(k8s_api, hook_info['node_name'])
                    loop = False
                except:
                    logger.warning('Attempting to cordon node {} failed, retrying ...'.format(hook_info['node_name']))
                    pass
                if time.time() < cordon_timeout:
                    time.sleep(1)
                else:
                    logger.exception('Exceeded the timeout of node {} cordoning, abandoning ...'.format(hook_info['node_name']))
                    abandon_lifecycle_action(asg, hook_info['asg_name'], hook_info['name'], hook_info['instance_id'])

            logger.info('Succeed in cordoning node {} in the warm pool.'.format(hook_info['node_name']))

        if node_ready(k8s_api, hook_info['node_name'], hook_info['launching_timeout']):
            append_node_labels(k8s_api, hook_info['node_name'], hook_info['node_role'], hook_info['instance_lifecycle'])
            logger.info('Success to append labels to node {}.'.format(hook_info['node_name']))
            continue_lifecycle_action(asg, hook_info['asg_name'], hook_info['name'], hook_info['instance_id'])
        else:
            abandon_lifecycle_action(asg, hook_info['asg_name'], hook_info['name'], hook_info['instance_id'])     

def terminate_node(k8s_api, hook_info):
    
    try:
        if not master_ready(k8s_api, asg, elb, ec2, hook_info['asg_name'], hook_info['node_name'], hook_info['node_role'], hook_info['launching_timeout']):
            logger.error('There is no master node.')
            abandon_lifecycle_action(asg, hook_info['asg_name'], hook_info['name'], hook_info['instance_id'])
            return

        if not node_exists(k8s_api, hook_info['node_name']):
            logger.error('Node not found.')
            abandon_lifecycle_action(asg, hook_info['asg_name'], hook_info['name'], hook_info['instance_id'])
            return

        cordon_node(k8s_api, hook_info['node_name'])
        remove_all_pods(k8s_api, hook_info['node_name'])

        continue_lifecycle_action(asg, hook_info['asg_name'], hook_info['name'], hook_info['instance_id'])
            
    except:
        logger.exception('There was an error removing the pods from the node {}'.format(hook_info['node_name']))
        abandon_lifecycle_action(asg, hook_info['asg_name'], hook_info['name'], hook_info['instance_id'])

def lambda_handler(event, context):

    logger.info(event)

    # process asg lifecycle hooks
    for record in event['Records']:
        k8s_api_client = None
        hook_info = {}
        hook_payload = json.loads(record['Sns']['Message'])

        # initial variable from hook payload
        if 'LifecycleTransition' not in hook_payload:
            continue
        else:
            k8s_api_client, hook_info = hook_init(hook_payload)

        # execute specific action for lifecycle hook
        if hook_info['transition'] == 'autoscaling:EC2_INSTANCE_LAUNCHING':
            launch_node(k8s_api_client, hook_info)

        elif hook_info['transition'] == 'autoscaling:EC2_INSTANCE_TERMINATING':
            terminate_node(k8s_api_client, hook_info)