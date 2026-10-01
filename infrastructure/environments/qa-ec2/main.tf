module "eugene_database" {
  source = "../../modules/eugene-ec2"

  aws_region=var.aws_region
  aws_availability_zone = var.aws_availability_zone
  subnet = var.subnet
  vpc_id=var.vpc_id

  workload_name=var.workload_name
  resource_prefix=var.resource_prefix
  instance_type = "r7i.xlarge"

  ec2_instance_role_arn = var.ec2_instance_role_arn
  ec2_instance_role_name = var.ec2_instance_role_name
}
