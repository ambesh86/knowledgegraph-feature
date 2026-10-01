#!/usr/bin/env bash

var_file="scop-db.tfvars"
plan_file="scop-db-tfplan.out"
terraform plan -var-file="${var_file}" -out "${plan_file}" 
