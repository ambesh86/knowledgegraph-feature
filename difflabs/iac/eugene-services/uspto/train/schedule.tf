resource "aws_cloudwatch_event_rule" "train_rule_1" {
 name                = "${var.resource_prefix}-eugene-train-rule-1"
 description         = "patent search trainer rule, will project and train graph embeddings for patent and other searches"
 schedule_expression = "rate(2 hours)"


  tags = merge(var.base_tags, {
    Name = "${var.resource_prefix}-eugene-train-rule-1"
    workloadName = var.workload_name
  })
}

resource "aws_cloudwatch_event_target" "train_event_ecs_target" {
 arn      = var.ecs_uspto_cluster_arn
 rule     = aws_cloudwatch_event_rule.train_rule_1.name
 role_arn = var.uspto_ecs_task_role_arn

 for_each = toset([for s in data.aws_subnet.uspto_subnets : s.id])
 ecs_target {
   task_count          = 1
   task_definition_arn = aws_ecs_task_definition.training_task.arn
   network_configuration {
     subnets         = toset([one([each.value])])
     security_groups = [aws_security_group.eugene_train_allow_sg.id]
   }
   launch_type = "FARGATE"
 }

}