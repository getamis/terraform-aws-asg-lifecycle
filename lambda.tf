resource "aws_sns_topic" "lifecycle" {
  name              = var.name
  kms_master_key_id = var.sns_topic_kms_key_id
  tags              = var.extra_tags
}

resource "aws_sns_topic_subscription" "lifecycle" {
  topic_arn = aws_sns_topic.lifecycle.arn
  protocol  = "lambda"
  endpoint  = module.lambda.lambda_function_arn
}

module "lambda" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "3.2.1"

  function_name = "${var.name}-lifecycle"

  handler                        = var.lambda_handler
  source_path                    = var.lambda_source_path
  runtime                        = var.lambda_runtime
  timeout                        = var.lambda_timeout
  kms_key_arn                    = var.kms_key_arn
  reserved_concurrent_executions = var.reserved_concurrent_executions

  # If publish is disabled, there will be "Error adding new Lambda Permission for notify_slack: InvalidParameterValueException: We currently do not support adding policies for $LATEST."
  publish = true

  environment_variables = var.lambda_environment_variables

  create_role               = var.lambda_role == ""
  lambda_role               = var.lambda_role
  role_name                 = "${var.name}-lifecycle"
  role_permissions_boundary = var.iam_role_boundary_policy_arn
  role_tags                 = var.iam_role_tags

  attach_network_policy = var.lambda_function_vpc_subnet_ids != null

  allowed_triggers = {
    AllowExecutionFromSNS = {
      principal  = "sns.amazonaws.com"
      source_arn = aws_sns_topic.lifecycle.arn
    }
  }

  store_on_s3 = var.lambda_function_store_on_s3
  s3_bucket   = var.lambda_function_s3_bucket

  vpc_subnet_ids         = var.lambda_function_vpc_subnet_ids
  vpc_security_group_ids = var.lambda_function_vpc_security_group_ids

  tags = var.extra_tags
}

data "aws_region" "current" {}

resource "null_resource" "assign_default_sg" {
  # workaround for sg still attached to eni created by lambda function
  # https://github.com/hashicorp/terraform-provider-aws/issues/10329
  triggers = {
    aws_region       = data.aws_region.current.name
    lambda_subnet_id = var.lambda_function_vpc_subnet_ids != null ? var.lambda_function_vpc_subnet_ids[0] : ""
    lambda_sg_id     = var.lambda_function_vpc_security_group_ids != null ? var.lambda_function_vpc_security_group_ids[0] : ""
  }

  provisioner "local-exec" {
    when    = destroy
    command = "/bin/bash ${path.module}/scripts/update-lambda-eni.sh ${self.triggers.aws_region} ${self.triggers.lambda_subnet_id} ${self.triggers.lambda_sg_id}"
  }
}