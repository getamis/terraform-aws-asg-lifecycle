locals {
  lambda_environment_variables = {
    CLUSTER_NAME         = var.cluster_name
    KUBE_CONFIG_BUCKET   = var.kubeconfig_s3_bucket
    KUBE_CONFIG_OBJECT   = var.kubeconfig_s3_object
    KUBERNETES_NODE_ROLE = var.kubernetes_node_role 
    LAUNCHING_TIMEOUT    = var.heartbeat_timeout["launching"]
    TERMINATING_TIMEOUT  = var.heartbeat_timeout["terminating"]
  }
}

module "k8s_lifecycle_hooks" {
  source = "../../"
  
  name                                   = "${var.name}"
  autoscaling_group_name                 = var.autoscaling_group_name
  default_result                         = var.default_result
  heartbeat_timeout                      = var.heartbeat_timeout
  lambda_handler                         = var.lambda_handler
  lambda_runtime                         = var.lambda_runtime
  lambda_source_path                     = "${path.module}/functions"
  lambda_environment_variables           = local.lambda_environment_variables
  lambda_function_vpc_subnet_ids         = var.lambda_function_vpc_subnet_ids
  lambda_function_vpc_security_group_ids = [ aws_security_group.k8s_lifecycle.id ]
  extra_tags                             = var.extra_tags
}

data "aws_subnet" "k8s_lifecycle" {
  id = var.lambda_function_vpc_subnet_ids[0]
}
 
resource "aws_security_group" "k8s_lifecycle" {
  name_prefix = "${var.name}-lifecycle-"
  vpc_id      = data.aws_subnet.k8s_lifecycle.vpc_id

  tags = merge(var.extra_tags, map(
    "Name", "${var.name}-lifecycle",
    "kubernetes.io/cluster/${var.cluster_name}", "owned"
  ))
}

resource "aws_security_group_rule" "k8s_lifecycle_egress" {
  type              = "egress"
  security_group_id = aws_security_group.k8s_lifecycle.id

  protocol    = "-1"
  cidr_blocks = ["0.0.0.0/0"]
  from_port   = 0
  to_port     = 0
}

data "aws_iam_policy_document" "k8s_lifecycle" {
  statement {
    sid = "EC2"

    actions = [
      "autoscaling:DescribeTags",
      "autoscaling:DescribeAutoScalingGroups",
      "autoscaling:DescribeLoadBalancers",
      "autoscaling:CompleteLifecycleAction",
      "ec2:DescribeInstances",
      "ec2:CreateTags"
    ]
    resources = [
      "*"
    ]
  }
  statement {
    sid = "ELB"
    actions = [
      "elasticloadbalancing:DescribeLoadBalancers",
      "elasticloadbalancing:DescribeInstanceHealth"
    ]
    resources = [
      "*"
    ]
  }
  statement {
    sid = "S3"
    actions = [
      "s3:GetObject",
    ]
    resources = [
      "arn:aws:s3:::${var.kubeconfig_s3_bucket}/*"
    ]
  }
}

resource "aws_iam_policy" "k8s_lifecycle" {
  name        = "${var.name}-lifecycle"
  path        = "/"
  description = "policy for kubernetes lifecycle hook"
  policy      = data.aws_iam_policy_document.k8s_lifecycle.json
}

resource "aws_iam_role_policy_attachment" "k8s_lifecycle" {
  policy_arn = aws_iam_policy.k8s_lifecycle.arn
  role       = module.k8s_lifecycle_hooks.lambda_role_name
}
