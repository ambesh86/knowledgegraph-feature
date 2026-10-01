module "uspto" {
  source = "./uspto"

  account_type                     = var.account_type
  ams_managed                      = var.ams_managed
  ams_monitoring_policy            = var.ams_monitoring_policy
  ams_monitoring_policy_platform   = var.ams_monitoring_policy_platform
  apm                              = var.apm
  business_unit                  = var.business_unit
  cost_budget_amount               = var.cost_budget_amount
  cost_center                    = var.cost_center
  data_classification            = var.data_classification
  patch_schedule                   = var.patch_schedule
  resource_prefix                = var.resource_prefix
  technical_owner                = var.technical_owner
  workload_environment           = var.workload_environment
  workload_name                  = var.workload_name
  workload_owner                 = var.workload_owner
}

module "database" {
  source = "./database"

  account_type                     = var.account_type
  ams_managed                      = var.ams_managed
  ams_monitoring_policy            = var.ams_monitoring_policy
  ams_monitoring_policy_platform   = var.ams_monitoring_policy_platform
  apm                              = var.apm
  business_unit                  = var.business_unit
  cost_budget_amount               = var.cost_budget_amount
  cost_center                    = var.cost_center
  data_classification            = var.data_classification
  patch_schedule                   = var.patch_schedule
  resource_prefix                = var.resource_prefix
  technical_owner                = var.technical_owner
  workload_environment           = var.workload_environment
  workload_name                  = var.workload_name
  workload_owner                 = var.workload_owner
}

