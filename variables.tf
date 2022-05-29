variable "name" {
  description = "The resource identify name"
  type        = string
  default     = "rolling-update"
}

variable "autoscaling_group_name" {
  description = "The name of the Auto Scaling group to which you want to assign the lifecycle hook"
  type        = string
}

variable "default_result" {
  description = "(optional) describe your variable"
  type = object({
    launching   = string
    terminating = string
  })
}

variable "heartbeat_timeout" {
  description = "lifecycle hook timeout in second"
  type = object({
    launching   = number
    terminating = number
  })
}

variable "notification_metadata" {
  description = "The additional information send from asg"
  type = object({
    launching   = string
    terminating = string
  })
  default = {
    launching   = ""
    terminating = ""
  }
}

variable "sns_topic_kms_key_id" {
  description = "ARN of the KMS key used for enabling SSE on the topic"
  type        = string
  default     = ""
}

variable "kms_key_arn" {
  description = "ARN of the KMS key used for decrypting slack webhook url"
  type        = string
  default     = ""
}

variable "cloudwatch_log_group_kms_key_id" {
  description = "The ARN of the KMS Key to use when encrypting log data for Lambda"
  type        = string
  default     = null
}

variable "reserved_concurrent_executions" {
  description = "The amount of reserved concurrent executions for this lambda function. A value of 0 disables lambda from being triggered and -1 removes any concurrency limitations"
  type        = number
  default     = -1
}

variable "lambda_handler" {
  description = "The lambda handler"
  type        = string
}

variable "lambda_role" {
  description = "IAM role attached to the Lambda Function.  If this is set then a role will not be created for you."
  type        = string
  default     = ""
}

variable "lambda_source_path" {
  description = "The lambda source path"
  type        = string
}

variable "lambda_runtime" {
  description = "The lambda runtime"
  type        = string
}

variable "lambda_timeout" {
  description = "The lambda timeout second"
  type        = number
  default     = 900
}

variable "lambda_environment_variables" {
  description = "The lambda environment variables"
  type        = map(string)
  default     = {}
}

variable "iam_role_boundary_policy_arn" {
  description = "The ARN of the policy that is used to set the permissions boundary for the role"
  type        = string
  default     = null
}

variable "iam_role_tags" {
  description = "Additional tags for the IAM role"
  type        = map(string)
  default     = {}
}

variable "lambda_function_vpc_subnet_ids" {
  description = "List of subnet ids when Lambda Function should run in the VPC. Usually private or intra subnets."
  type        = list(string)
  default     = null
}

variable "lambda_function_store_on_s3" {
  description = "Whether to store produced artifacts on S3 or locally."
  type        = bool
  default     = false
}

variable "lambda_function_s3_bucket" {
  description = "S3 bucket to store artifacts"
  type        = string
  default     = null
}

variable "lambda_function_vpc_security_group_ids" {
  description = "List of security group ids when Lambda Function should run in the VPC."
  type        = list(string)
  default     = null
}

variable "cloudwatch_log_group_retention_in_days" {
  description = "Specifies the number of days you want to retain log events in log group for Lambda."
  type        = number
  default     = 90
}

variable "extra_tags" {
  description = "The extra tag for resource"
  type        = map(string)
}