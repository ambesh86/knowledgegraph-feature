locals {
  base_tags = {
    system = "eugene"
    Environment = var.resource_prefix
  }

  dotenv = { for tuple in regexall("(.*)=(.*)", file(".env")) : tuple[0] => sensitive(tuple[1]) }

  database_secret_id = "eugene/dev/database/env"

  # database_env = jsondecode(data.aws_secretsmanager_secret_version.database_env_secrets.secret_string)
}