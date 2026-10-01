module "database" {
  source = "./database"

  aws_region = var.aws_region
  aws_availability_zone = var.aws_availability_zone
  subnet = var.subnet
  vpc_id = var.vpc_id

  resource_prefix = var.resource_prefix
  workload_name = var.workload_name

  ec2_instance_role_arn = var.ec2_instance_role_arn
  ec2_instance_role_name = var.ec2_instance_role_name

  instance_type = var.instance_type
}
