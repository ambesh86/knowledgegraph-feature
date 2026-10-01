bucket = "aia-scop-experiment-terraform-state" # the bucket is always the same for the same aws region
region       = "eu-central-1"
encrypt      = true  
# use_lockfile = true  #S3 native locking
dynamodb_table = "terraform-locks"
