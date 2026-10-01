# Docker

This document contains information about using docker for the eugene project

Docker is used both in the `difflabs` and `ai accelerator` environments. The builds are slightly different based on what network access was available.


# Setup Locally

Install docker

The docker default cloudflare url might not work behind the zscaler vpn, so you might need to change the registry mirror

```json
{
  "builder": {
    "gc": {
      "defaultKeepStorage": "20GB",
      "enabled": true
    }
  },
  "debug": true,
  "experimental": false,
  "mtu": 1450,
  "registry-mirrors": [
    "https://mirror.gcr.io"
  ]
}
```

# Login

My build flow for difflabs is to [login to AWS](./csl_aws.md). Get the cli access tokens and paste them in a terminal. 


Then docker login to ECR. Scripts are in [bin/docker/ecr](../bin/docker/ecr/)


# Build And Push
```
cd bin/docker
./login.sh
cd ../..

./bin/docker/build.sh
./bin/docker/tag.sh
./bin/docker/push.sh
```

These build, tag, and push scripts will stage docker images to difflabs for running in that account.

Note to run the `push.sh` will require you to setup the ECR repo using terraform at least one time. See installing from terraform docs.


# Modify Images

To modify the build or docker images visit either

* [difflabs images](../difflabs/containers/)
* [aia images](../containers/)


Images were split across the environments because network access and thus the builds are slightly different. Differences include package repo access and secrets management. This is not ideal and is technical debt


# FAQ 

Use the prune.sh and clean-volumes to clean up running or orpaned images. Sometimes the disk will fill up and this is needed.