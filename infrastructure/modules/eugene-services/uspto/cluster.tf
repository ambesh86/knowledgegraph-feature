resource "aws_ecs_cluster" "uspto_cluster" {
  name = "${var.resource_prefix}-${var.ecs_uspto_cluster_name}"

  tags = merge(local.base_tags, {
    Name = "${var.resource_prefix}-${var.ecs_uspto_cluster_name}"
    workloadName = var.workload_name
  })
}
