#!/usr/bin/env bash

var_file="difflabs-lb.tfvars"
plan_file="difflabs-lb-tfplan.out"
terraform plan -var-file="${var_file}" -out "${plan_file}" 
