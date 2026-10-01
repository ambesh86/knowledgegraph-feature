data "aws_secretsmanager_secret_version" "uspto_env_secrets" {
  secret_id     = local.uspto_secret_id
}