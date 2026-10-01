locals {
  base_tags = {
    system = "eugene"
    data = "uspto"
    Environment = var.resource_prefix
  }

  dotenv = { for tuple in regexall("(.*)=(.*)", file(".env")) : tuple[0] => sensitive(tuple[1]) }

  uspto_secret_id = "eugene/dev/uspto/env"

  uspto_env = jsondecode(data.aws_secretsmanager_secret_version.uspto_env_secrets.secret_string)
}