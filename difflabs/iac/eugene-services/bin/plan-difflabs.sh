#!/usr/bin/env bash

var_file="difflabs.tfvars"
plan_file="difflabs-tfplan.out"
terraform plan -var-file="${var_file}" -out "${plan_file}" 
