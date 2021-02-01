# Launching Instance
resource "aws_autoscaling_lifecycle_hook" "lifecycle_launching" {
  name                    = "${var.name}-launching"
  autoscaling_group_name  = var.autoscaling_group_name
  default_result          = var.default_result["launching"]
  heartbeat_timeout       = var.heartbeat_timeout["launching"]
  lifecycle_transition    = "autoscaling:EC2_INSTANCE_LAUNCHING"
  notification_metadata   = var.notification_metadata["launching"]
  notification_target_arn = aws_sns_topic.lifecycle.arn
  role_arn                = aws_iam_role.lifecycle.arn
}

# Terminating Instance
resource "aws_autoscaling_lifecycle_hook" "lifecycle_terminating" {
  name                    = "${var.name}-terminating"
  autoscaling_group_name  = var.autoscaling_group_name
  default_result          = var.default_result["terminating"]
  heartbeat_timeout       = var.heartbeat_timeout["terminating"]
  lifecycle_transition    = "autoscaling:EC2_INSTANCE_TERMINATING"
  notification_metadata   = var.notification_metadata["terminating"]
  notification_target_arn = aws_sns_topic.lifecycle.arn
  role_arn                = aws_iam_role.lifecycle.arn
}