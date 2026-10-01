#!/usr/bin/env bash

set -eou pipefail
set -x

aws_acct=010928221940
aws_region=eu-central-1

aws ecr get-login-password --region "${aws_region}" | docker login --username AWS --password-stdin "${aws_acct}.dkr.ecr.${aws_region}.amazonaws.com"
