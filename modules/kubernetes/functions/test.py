# This script is used to test the lambda_handler function from the functions module.
from typing import Dict, Any
from aws_lambda_typing.context import Context
from aws_lambda_typing.events import SNSEvent

from handler import lambda_handler

import json

"""data is a sample SNS event from asg autoscaling:EC2_INSTANCE_LAUNCHING"""
data = {'Records': [{}]}

event: Dict[str, Any] = SNSEvent(data)

context: Context = Context()

lambda_handler(event, context)
