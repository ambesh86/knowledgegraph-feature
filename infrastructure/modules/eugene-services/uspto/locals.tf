locals {
  base_tags = {
    Environment = var.resource_prefix
  }

  dotenv = { for tuple in regexall("(.*)=(.*)", file("../../modules/eugene-services/.env")) : tuple[0] => sensitive(tuple[1]) }

}