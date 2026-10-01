resource "aws_cloudwatch_metric_alarm" "successful_health_endpoint_alarm" {
  alarm_name                = "${var.resource_prefix}-eugene-successful-health-endpoint-alarm"
  comparison_operator       = "LessThanThreshold"
  evaluation_periods        = 1
  namespace                 = "${local.metrics_namespace}"
  metric_name               = "${local.successful_metric_name}"
  dimensions = {
    EndpointName  = "Health Endpoint"
    Environment   = "STAGING"
    SystemName    = "DIFFLABS"
  }
  period                    = 300
  statistic                 = "Sum"
  threshold                 = 1
  alarm_description         = "This metric monitors successful canaries against the API"
  insufficient_data_actions = []
  datapoints_to_alarm       = 1
  treat_missing_data        = "breaching"

  tags = merge(var.base_tags, {
    Name = "${var.resource_prefix}-eugene-successful-health-endpoint-alarm"
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

resource "aws_cloudwatch_metric_alarm" "unsuccessful_health_endpoint_alarm" {
  alarm_name                = "${var.resource_prefix}-eugene-unsuccessful-health-endpoint-alarm"
  comparison_operator       = "GreaterThanOrEqualToThreshold"
  evaluation_periods        = 1
  namespace                 = "${local.metrics_namespace}"
  metric_name               = "${local.unsuccessful_metric_name}"
  dimensions = {
    EndpointName  = "Health Endpoint"
    Environment   = "STAGING"
    SystemName    = "DIFFLABS"
  }
  period                    = 300
  statistic                 = "Sum"
  threshold                 = 1
  alarm_description         = "This metric monitors unsuccessful canaries against the API"
  insufficient_data_actions = []
  datapoints_to_alarm       = 1
  treat_missing_data        = "notBreaching"

  tags = merge(var.base_tags, {
    Name = "${var.resource_prefix}-eugene-unsuccessful-health-endpoint-alarm"
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

resource "aws_cloudwatch_metric_alarm" "successful_label_count_alarm" {
  alarm_name                = "${var.resource_prefix}-eugene-successful-label-count-endpoint-alarm"
  comparison_operator       = "LessThanThreshold"
  evaluation_periods        = 1
  namespace                 = "${local.metrics_namespace}"
  metric_name               = "${local.successful_metric_name}"
  dimensions = {
    EndpointName  = "Label Count Endpoint"
    Environment   = "STAGING"
    SystemName    = "DIFFLABS"
  }
  period                    = 300
  statistic                 = "Sum"
  threshold                 = 1
  alarm_description         = "This metric monitors successful canaries against the API"
  insufficient_data_actions = []
  datapoints_to_alarm       = 1
  treat_missing_data        = "breaching"

  tags = merge(var.base_tags, {
    Name = "${var.resource_prefix}-eugene-successful-label-count-endpoint-alarm"
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

resource "aws_cloudwatch_metric_alarm" "unsuccessful_label_count_endpoint_alarm" {
  alarm_name                = "${var.resource_prefix}-eugene-unsuccessful-label-count-endpoint-alarm"
  comparison_operator       = "GreaterThanOrEqualToThreshold"
  evaluation_periods        = 1
  namespace                 = "${local.metrics_namespace}"
  metric_name               = "${local.unsuccessful_metric_name}"
  dimensions = {
    EndpointName  = "Label Count Endpoint"
    Environment   = "STAGING"
    SystemName    = "DIFFLABS"
  }
  period                    = 300
  statistic                 = "Sum"
  threshold                 = 1
  alarm_description         = "This metric monitors unsuccessful canaries against the API"
  insufficient_data_actions = []
  datapoints_to_alarm       = 1
  treat_missing_data        = "notBreaching"

  tags = merge(var.base_tags, {
    Name = "${var.resource_prefix}-eugene-unsuccessful-label-count-endpoint-alarm"
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

resource "aws_cloudwatch_metric_alarm" "successful_stats_alarm" {
  alarm_name                = "${var.resource_prefix}-eugene-successful-stats-endpoint-alarm"
  comparison_operator       = "LessThanThreshold"
  evaluation_periods        = 1
  namespace                 = "${local.metrics_namespace}"
  metric_name               = "${local.successful_metric_name}"
  dimensions = {
    EndpointName  = "Stats Endpoint"
    Environment   = "STAGING"
    SystemName    = "DIFFLABS"
  }
  period                    = 300
  statistic                 = "Sum"
  threshold                 = 1
  alarm_description         = "This metric monitors successful canaries against the API"
  insufficient_data_actions = []
  datapoints_to_alarm       = 1
  treat_missing_data        = "breaching"

  tags = merge(var.base_tags, {
    Name = "${var.resource_prefix}-eugene-successful-stats-endpoint-alarm"
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

resource "aws_cloudwatch_metric_alarm" "unsuccessful_stats_endpoint_alarm" {
  alarm_name                = "${var.resource_prefix}-eugene-unsuccessful-stats-endpoint-alarm"
  comparison_operator       = "GreaterThanOrEqualToThreshold"
  evaluation_periods        = 1
  namespace                 = "${local.metrics_namespace}"
  metric_name               = "${local.unsuccessful_metric_name}"
  dimensions = {
    EndpointName  = "Stats Endpoint"
    Environment   = "STAGING"
    SystemName    = "DIFFLABS"
  }
  period                    = 300
  statistic                 = "Sum"
  threshold                 = 1
  alarm_description         = "This metric monitors unsuccessful canaries against the API"
  insufficient_data_actions = []
  datapoints_to_alarm       = 1
  treat_missing_data        = "notBreaching"

  tags = merge(var.base_tags, {
    Name = "${var.resource_prefix}-eugene-unsuccessful-stats-endpoint-alarm"
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

resource "aws_cloudwatch_metric_alarm" "successful_node_find_alarm" {
  alarm_name                = "${var.resource_prefix}-eugene-successful-node-find-endpoint-alarm"
  comparison_operator       = "LessThanThreshold"
  evaluation_periods        = 1
  namespace                 = "${local.metrics_namespace}"
  metric_name               = "${local.successful_metric_name}"
  dimensions = {
    EndpointName  = "Node Find Endpoint"
    Environment   = "STAGING"
    SystemName    = "DIFFLABS"
  }
  period                    = 300
  statistic                 = "Sum"
  threshold                 = 1
  alarm_description         = "This metric monitors successful canaries against the API"
  insufficient_data_actions = []
  datapoints_to_alarm       = 1
  treat_missing_data        = "breaching"

  tags = merge(var.base_tags, {
    Name = "${var.resource_prefix}-eugene-successful-node-find-endpoint-alarm"
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

resource "aws_cloudwatch_metric_alarm" "unsuccessful_node_find_endpoint_alarm" {
  alarm_name                = "${var.resource_prefix}-eugene-unsuccessful-node-find-endpoint-alarm"
  comparison_operator       = "GreaterThanOrEqualToThreshold"
  evaluation_periods        = 1
  namespace                 = "${local.metrics_namespace}"
  metric_name               = "${local.unsuccessful_metric_name}"
  dimensions = {
    EndpointName  = "Node Find Endpoint"
    Environment   = "STAGING"
    SystemName    = "DIFFLABS"
  }
  period                    = 300
  statistic                 = "Sum"
  threshold                 = 1
  alarm_description         = "This metric monitors unsuccessful canaries against the API"
  insufficient_data_actions = []
  datapoints_to_alarm       = 1
  treat_missing_data        = "notBreaching"

  tags = merge(var.base_tags, {
    Name = "${var.resource_prefix}-eugene-unsuccessful-node-find-endpoint-alarm"
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

resource "aws_cloudwatch_metric_alarm" "successful_node_details_alarm" {
  alarm_name                = "${var.resource_prefix}-eugene-successful-node-details-endpoint-alarm"
  comparison_operator       = "LessThanThreshold"
  evaluation_periods        = 1
  namespace                 = "${local.metrics_namespace}"
  metric_name               = "${local.successful_metric_name}"
  dimensions = {
    EndpointName  = "Node Details Endpoint"
    Environment   = "STAGING"
    SystemName    = "DIFFLABS"
  }
  period                    = 300
  statistic                 = "Sum"
  threshold                 = 1
  alarm_description         = "This metric monitors successful canaries against the API"
  insufficient_data_actions = []
  datapoints_to_alarm       = 1
  treat_missing_data        = "breaching"

  tags = merge(var.base_tags, {
    Name = "${var.resource_prefix}-eugene-successful-node-details-endpoint-alarm"
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

resource "aws_cloudwatch_metric_alarm" "unsuccessful_node_details_endpoint_alarm" {
  alarm_name                = "${var.resource_prefix}-eugene-unsuccessful-node-details-endpoint-alarm"
  comparison_operator       = "GreaterThanOrEqualToThreshold"
  evaluation_periods        = 1
  namespace                 = "${local.metrics_namespace}"
  metric_name               = "${local.unsuccessful_metric_name}"
  dimensions = {
    EndpointName  = "Node Details Endpoint"
    Environment   = "STAGING"
    SystemName    = "DIFFLABS"
  }
  period                    = 300
  statistic                 = "Sum"
  threshold                 = 1
  alarm_description         = "This metric monitors unsuccessful canaries against the API"
  insufficient_data_actions = []
  datapoints_to_alarm       = 1
  treat_missing_data        = "notBreaching"

  tags = merge(var.base_tags, {
    Name = "${var.resource_prefix}-eugene-unsuccessful-node-details-endpoint-alarm"
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