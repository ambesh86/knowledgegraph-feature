resource "aws_security_group" "allow_outbound" {
  name        = "${var.resource_prefix}-allow-outbound-ingest"
  description = "Allow all outbound traffic"
  vpc_id      = data.aws_vpc.uspto_vpc.id

  tags = {
    Name = "${var.resource_prefix}-allow-outbound-ingest"
    Service = "uspto"
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
  }
}

resource "aws_vpc_security_group_egress_rule" "allow_all_traffic_ipv4" {
  security_group_id = aws_security_group.allow_outbound.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1" # semantically equivalent to all ports
}
