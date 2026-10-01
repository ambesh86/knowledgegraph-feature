output "instance_id" {
  value = aws_instance.ui.id
}

output "private_ip" {
  value = aws_instance.ui.private_ip
}

output "public_ip" {
  value       = var.associate_public_ip ? aws_eip.ui[0].public_ip : null
  description = "Stable public IP if associate_public_ip=true."
}

output "ui_url_public" {
  value = var.associate_public_ip ? (var.expose_on_port_80
    ? "http://${aws_eip.ui[0].public_ip}/"
  : "http://${aws_eip.ui[0].public_ip}:${var.ui_port}/") : null
  description = "URL for browser access (public path)."
}

output "ui_url_private" {
  value = (var.expose_on_port_80
    ? "http://${aws_instance.ui.private_ip}/"
    : "http://${aws_instance.ui.private_ip}:${var.ui_port}/"
  )
  description = "URL reachable from inside the VPC (via VPN)."
}

output "ui_url_https" {
  value       = var.enable_tls ? "https://${var.domain_name}/" : null
  description = "Public HTTPS URL (only when enable_tls = true)."
}

output "public_alb_dns_name" {
  value       = var.enable_tls ? aws_lb.public[0].dns_name : null
  description = "Public ALB hostname (only when enable_tls = true)."
}

output "ssm_start_session_cmd" {
  value       = "aws ssm start-session --target ${aws_instance.ui.id} --region ${var.aws_region}"
  description = "Run this to shell into the EC2 without SSH."
}

output "tail_bootstrap_log_cmd" {
  value       = "aws ssm start-session --target ${aws_instance.ui.id} --region ${var.aws_region} --document-name AWS-StartInteractiveCommand --parameters command='sudo tail -f /var/log/eugene-ui-bootstrap.log'"
  description = "Live-tail the user-data bootstrap log."
}
