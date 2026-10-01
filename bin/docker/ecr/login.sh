#!/usr/bin/env bash

set -eou pipefail
set -x

source ./env.sh

aws ecr get-login-password --region "${aws_region}" | docker login --username AWS --password-stdin "${aws_acct}.dkr.ecr.${aws_region}.amazonaws.com"
