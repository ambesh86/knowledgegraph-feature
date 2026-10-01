#!/usr/bin/env bash

var_file="difflabs-db.tfvars"
plan_file="difflabs-db-tfplan.out"
terraform plan -var-file="${var_file}" -out "${plan_file}" 
