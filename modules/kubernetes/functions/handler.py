import boto3
import json
import logging
import os.path
import time

from botocore.signers import RequestSigner
from kubernetes import client as k8s_client
from kubernetes import config as k8s_config
from kubernetes.client.rest import ApiException

from k8s_utils import (abandon_lifecycle_action, cordon_node, node_exists, node_ready, remove_all_pods)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

KUBE_FILEPATH = '/tmp/kubeconfig'
REGION = os.environ['AWS_REGION']

ec2 = boto3.client('ec2', region_name=REGION)
asg = boto3.client('autoscaling', region_name=REGION)
s3 = boto3.client('s3', region_name=REGION)

def k8s_api():

    env = {
        'cluster_name': os.environ.get('CLUSTER_NAME'),
        'kube_config_bucket': os.environ.get('KUBE_CONFIG_BUCKET'),
        'kube_config_object': os.environ.get('KUBE_CONFIG_OBJECT')
    }

    kube_config_bucket = env['kube_config_bucket']
    cluster_name = env['cluster_name']

    if not os.path.exists(KUBE_FILEPATH):
        if kube_config_bucket:
            logger.info('No kubeconfig file found. Downloading...')
            s3.download_file(kube_config_bucket, env['kube_config_object'], KUBE_FILEPATH)
        else:
            logger.info('No kubeconfig file found.')

    k8s_config.load_kube_config(KUBE_FILEPATH)

    return k8s_client.CoreV1Api()

def launch_node(k8s_api, auto_scaling_group_name, lifecycle_hook_name, instance_id, node_name, timeout):
    
    waiting_timeout = time.time() + timeout

    while True:
        if time.time() > waiting_timeout:
            logger.exception('timeout waiting for node {} launch'.format(node_name))
            break
        try:
            if node_exists(k8s_api, node_name):
                if node_ready(k8s_api, node_name):
                    logger.info('K8s node {} is ready'.format(node_name))
                    break
            
            time.sleep(10)
        except ApiException:
            logger.exception('There was an error waiting the node {} ready'.format(node_name))
            abandon_lifecycle_action(asg, auto_scaling_group_name, lifecycle_hook_name, instance_id)
            break

def terminate_node(k8s_api, auto_scaling_group_name, lifecycle_hook_name, instance_id, node_name, timeout):

    try:
        if not node_exists(k8s_api, node_name):
            logger.error('Node not found.')
            abandon_lifecycle_action(asg, auto_scaling_group_name, lifecycle_hook_name, instance_id)
            return

        cordon_node(k8s_api, node_name)

        remove_all_pods(k8s_api, node_name)

        asg.complete_lifecycle_action(LifecycleHookName=lifecycle_hook_name,
                                      AutoScalingGroupName=auto_scaling_group_name,
                                      LifecycleActionResult='CONTINUE',
                                      InstanceId=instance_id)
    except ApiException:
        logger.exception('There was an error removing the pods from the node {}'.format(node_name))
        abandon_lifecycle_action(asg, auto_scaling_group_name, lifecycle_hook_name, instance_id)

def lambda_handler(event, context):

    k8s_api_client = k8s_api()

    logger.info(event)

    # process asg lifecycle hooks
    for record in event['Records']:

        lifecycle_hook_name = ''
        lfiecycle_transition = ''
        auto_scaling_group_name = ''
        instance_id = ''
        node_name = ''
        instance_lifecycle = ''

        hook_payload = json.loads(record['Sns']['Message'])

        # initial variable from hook payload
        if 'LifecycleTransition' not in hook_payload:
            continue
        else:
            lifecycle_hook_name = hook_payload['LifecycleHookName']
            auto_scaling_group_name = hook_payload['AutoScalingGroupName']
            lfiecycle_transition = hook_payload['LifecycleTransition']
            instance_id = hook_payload['EC2InstanceId']
            instance = ec2.describe_instances(InstanceIds=[instance_id])['Reservations'][0]['Instances'][0]
            node_name = instance['PrivateDnsName']
            instance_lifecycle = instance['InstanceLifecycle']


            logger.info("Processing %s event from auto scaling group %s, and the instance id is %s, private dns name is %s" % (lfiecycle_transition, auto_scaling_group_name, instance_id, node_name))

        # execute specific action for lifecycle hook
        if lfiecycle_transition == 'autoscaling:EC2_INSTANCE_LAUNCHING':
            timeout = float(os.environ.get('LAUNCHING_TIMEOUT'))
            launch_node(k8s_api_client, auto_scaling_group_name, lifecycle_hook_name, instance_id, node_name, timeout)

        elif lfiecycle_transition == 'autoscaling:EC2_INSTANCE_TERMINATING':
            timeout = float(os.environ.get('TERMINATING_TIMEOUT'))
            terminate_node(k8s_api_client, auto_scaling_group_name, lifecycle_hook_name, instance_id, node_name, timeout)