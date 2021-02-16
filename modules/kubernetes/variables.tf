variable "autoscaling_group_name" {
  description = "The name of the Auto Scaling group to which you want to assign the lifecycle hook"
  type        = string
}

variable "cluster_name" {
  description = "The K8s cluster identify name"
  type        = string
}

variable "default_result" {
  description = "(optional) describe your variable"
  type        = object({
    launching   = string
    terminating = string
  })
  default     = {
    launching   = "CONTINUE"
    terminating = "CONTINUE"
  }
}

variable "extra_tags" {
  description = "The extra tag for resource"
  type        = map(string)
  default     = {}
}

variable "heartbeat_timeout" {
  description = "lifecycle hook timeout in second"
  type        = object({
    launching   = number
    terminating = number 
  })
  default    = {
    launching   = 550
    terminating = 850
  } 
}

variable "kubeconfig_s3_bucket" {
    description = "The kubeconfig s3 bucket name"
    type        = string
}

variable "kubeconfig_s3_object" {
    description = "The kubeconfig s3 object name"
    type        = string
}

variable "kubernetes_node_role" {
    description = "The kubernetes node role name, e.g. node-role.kubernetes.io/master"
    type        = string
}

variable "lambda_handler" {
    description = "The lifecycle hooks lambda handler"
    type        = string
    default     = "handler.lambda_handler"
}

variable "lambda_function_vpc_subnet_ids" {
    description = "The Lambda vpc subnet ids"
    type        = list(string)
    default     = []
}

variable "lambda_runtime" {
    description = "The lifecycle hooks runtime"
    type        = string
    default     = "python3.7"
}

variable "name" {
  description = "The resource identify name"
  type        = string
}




