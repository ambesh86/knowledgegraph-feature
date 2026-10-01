# Difflabs directory

This difflabs directory holds infrastructure as code, `docker` and `terraform` files for the diffusions labs AWS account and VPC.

These files do not run in the gitlab pipeline. The gitlab pipeline account does not have access to the diffusion labs VPC.


# FAQ

Q. Why not use the same files as the AIA deployment?

A. These files are similar to the AIA deployment. The differences revolve around reaching out to an AIA AWS S3 bucket and expectations around whitelisting of images, libraries, and HuggingFace models.