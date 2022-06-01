#!/bin/bash

export AWS_DEFAULT_REGION=${1:-us-west-2}
export SUBNET_ID=$2
export SG_ID=$3

VPC_ID=$(aws ec2 describe-subnets --filters Name=subnet-id,Values=${SUBNET_ID} --output text --query "Subnets[0].VpcId")

DEFAULT_SG_ID=$(aws ec2 describe-security-groups --filters Name=description,Values='default VPC security group' Name=vpc-id,Values=${VPC_ID} --output text --query 'SecurityGroups[0].GroupId')

ENIS=$(aws ec2 describe-network-interfaces --filters Name=group-id,Values=${SG_ID} --output text --query 'NetworkInterfaces[*].NetworkInterfaceId')

for ENI in ${ENIS}; do
    aws ec2 modify-network-interface-attribute --network-interface-id ${ENI} --groups ${DEFAULT_SG_ID}
done

echo "assign only ${DEFAULT_SG_ID} to ${ENIS}"

