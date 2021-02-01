data "aws_iam_policy_document" "lifecycle_profile" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["autoscaling.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lifecycle" {
  name               = "${var.name}-asg"
  assume_role_policy = data.aws_iam_policy_document.lifecycle_profile.json
}

data "aws_iam_policy_document" "lifecycle" {
  statement {
    effect    = "Allow"
    actions   = ["sns:Publish", "autoscaling:CompleteLifecycleAction"]
    resources = [aws_sns_topic.lifecycle.arn]
  }
}

resource "aws_iam_role_policy" "lifecycle" {
  name   = "${var.name}-asg"
  role   = aws_iam_role.lifecycle.id
  policy = data.aws_iam_policy_document.lifecycle.json
}