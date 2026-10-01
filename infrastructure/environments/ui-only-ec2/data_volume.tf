# =============================================================================
# Persistent data volume for Atlas Postgres.
#
# Why this exists: `user_data_replace_on_change = true` means any change to the
# image tag, an env var, or the proxy settings REPLACES the instance. The Docker
# named volume `atlas-pg-data` lives on the instance root disk, so replacement
# silently destroys every user account and every conversation in the product.
#
# That is a data-loss bug waiting on the next routine deploy, and it cannot be
# fixed by being careful — the whole point of the deploy path is that it
# replaces the box. So Postgres data moves to its own EBS volume, which is a
# separate resource with its own lifecycle and is re-attached to whatever
# instance currently exists.
#
# `prevent_destroy` is deliberate: a `terraform destroy` of this environment
# should fail loudly rather than take the user database with it. Remove the
# block consciously if you really mean to delete it.
# =============================================================================

resource "aws_ebs_volume" "atlas_data" {
  count             = var.persist_atlas_data ? 1 : 0
  availability_zone = data.aws_subnet.target.availability_zone
  size              = var.atlas_data_volume_gb
  type              = "gp3"
  encrypted         = true

  tags = { Name = "${var.name_prefix}-atlas-data" }

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_volume_attachment" "atlas_data" {
  count       = var.persist_atlas_data ? 1 : 0
  device_name = "/dev/sdf" # Nitro renames this; user-data discovers it by size
  volume_id   = aws_ebs_volume.atlas_data[0].id
  instance_id = aws_instance.ui.id

  # On replacement the volume must detach from the dying instance before it can
  # attach to the new one. Without this the apply deadlocks.
  stop_instance_before_detaching = true
}

data "aws_subnet" "target" {
  id = var.subnet_id
}
