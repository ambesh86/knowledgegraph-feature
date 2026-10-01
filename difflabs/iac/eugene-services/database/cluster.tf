resource "aws_ecs_cluster" "database_cluster" {
  name = "${var.resource_prefix}-${var.ecs_database_cluster_name}"

  tags = merge(local.base_tags, {
    Name = "${var.resource_prefix}-${var.ecs_database_cluster_name}"
    workloadName = var.workload_name
  })
}
