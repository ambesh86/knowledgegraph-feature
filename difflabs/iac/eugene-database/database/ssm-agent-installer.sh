#!/usr/bin/env bash

# sudo mkdir /tmp/ssm
# cd /tmp/ssm
sudo yum install -y https://s3.amazonaws.com/session-manager-downloads/plugin/latest/linux_arm64/session-manager-plugin.rpm

sudo systemctl enable amazon-ssm-agent