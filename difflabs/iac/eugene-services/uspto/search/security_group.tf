resource "aws_security_group" "eugene_search_container_sg" {
  name        = "${var.resource_prefix}-eugene_search_container_sg"
  description = "Allow inbound traffic and all outbound traffic to the search container"
  vpc_id      = data.aws_vpc.uspto_vpc.id

  tags = merge(var.base_tags, {
    Name = "${var.resource_prefix}-eugene_search_container_sg"
    accountType                   = var.account_type
    amsManaged                    = var.ams_managed
    amsMonitoringPolicy           = var.ams_monitoring_policy
    amsMonitoringPolicyPlatform   = var.ams_monitoring_policy_platform
    APM                           = var.apm
    businessUnit                  = var.business_unit
    costBudgetAmount              = var.cost_budget_amount
    costCenter                    = var.cost_center
    dataClassification            = var.data_classification
    patchSchedule                 = var.patch_schedule
    technicalOwner                = var.technical_owner
    workloadEnvironment           = var.workload_environment
    workloadName                  = var.workload_name
    workloadOwner                 = var.workload_owner
  })
}

resource "aws_vpc_security_group_ingress_rule" "eugene_search_container_allow_http_rule" {
  security_group_id = aws_security_group.eugene_search_container_sg.id
  cidr_ipv4         = data.aws_vpc.uspto_vpc.cidr_block
  from_port         = 8000
  to_port           = 8000
  ip_protocol       = "tcp"
}

resource "aws_vpc_security_group_egress_rule" "eugene_search_container_allow_egress_rule" {
  security_group_id = aws_security_group.eugene_search_container_sg.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1" 
}
