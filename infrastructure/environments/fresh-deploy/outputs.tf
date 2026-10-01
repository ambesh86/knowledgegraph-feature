output "alb_dns_name" {
  description = "ALB hostname — point your DNS / clients at this."
  value       = aws_lb.main.dns_name
}

output "alb_zone_id" {
  description = "ALB hosted zone ID (for ALIAS records)."
  value       = aws_lb.main.zone_id
}

output "service_urls" {
  description = "What each service responds to via the ALB."
  value = {
    chat_ui_next     = var.alb_certificate_arn == "" ? "http://${aws_lb.main.dns_name}/"          : "https://${aws_lb.main.dns_name}/"
    chat_ui_legacy   = var.alb_certificate_arn == "" ? "http://${aws_lb.main.dns_name}/ui/"       : "https://${aws_lb.main.dns_name}/ui/"
    agent_api        = var.alb_certificate_arn == "" ? "http://${aws_lb.main.dns_name}/agent/api/": "https://${aws_lb.main.dns_name}/agent/api/"
    core_api         = var.alb_certificate_arn == "" ? "http://${aws_lb.main.dns_name}/api/"      : "https://${aws_lb.main.dns_name}/api/"
    mcp              = var.alb_certificate_arn == "" ? "http://${aws_lb.main.dns_name}/mcp/"      : "https://${aws_lb.main.dns_name}/mcp/"
  }
}

output "neo4j_private_ip" {
  description = "Neo4j Bolt endpoint (port 7687) — reachable only from inside the VPC."
  value       = aws_instance.neo4j.private_ip
}

output "ecs_cluster" {
  value = aws_ecs_cluster.main.name
}

output "ssm_parameter_paths" {
  description = "Where each secret lives in SSM Parameter Store."
  value = {
    openai_api_key       = aws_ssm_parameter.openai_key.name
    eugene_client_secret = aws_ssm_parameter.eugene_client_secret.name
    neo4j_password       = aws_ssm_parameter.neo4j_password.name
  }
}
