#!/usr/bin/env bash

var_file="difflabs-db.tfvars"
terraform init -var-file="${var_file}"
