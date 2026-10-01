#!/usr/bin/env bash

# look at terraform output for instance id
instance_id="${1:-}"
aws ssm start-session --target "${instance_id}"