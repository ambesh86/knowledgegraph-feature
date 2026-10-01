#!/usr/bin/env bash

set -euxo pipefail


sudo yum install -y https://s3.amazonaws.com/session-manager-downloads/plugin/latest/linux_64bit/session-manager-plugin.rpm

sudo systemctl enable amazon-ssm-agent
