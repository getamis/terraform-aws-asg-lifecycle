terraform {
  required_version = ">= 0.13.1"
}

module "k8s_lifecycle_hook" {
  source = "../modules/kubernetes"

  name                           = "test-master"
  cluster_name                   = "test"
  autoscaling_group_name         = "test-master"
  kubeconfig_s3_bucket           = "test-master"
  kubeconfig_s3_object           = "test-master/kubeconfig"
  kubernetes_node_role           = "master"
  lambda_function_vpc_subnet_ids = ["subnet-12345678"]

  extra_tags = {
    "Name"                              = "test-master"
    "kubernetes.io/cluster/test-master" = "owned"
  }
  
}