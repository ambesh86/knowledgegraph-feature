# GIT source control

This document captures information about the source control used by EUGENE.


Eugene uses a CSL hosted gitlab server


Latest source code is in [SCOP Experiments](https://gitlab.com/cslagile/business/ai-accelerator-usecases/scop-experimentation/-/tree/qa/.gitlab/ci?ref_type=heads)

Deprecated source code is in [DIFFLABS Experiments](https://gitlab.com/cslagile/business/diffusion-labs/fuze-experiments)

The SCOP Experiments git repo uses the following branches. These branches correspond to the AIA naming and pipeline convention


* main - not really used as we do not have a prod system
* qa - this is the main development branch. It has a trigger to deploy to the AIA environment
* feature branch names - these are cleaned on every merge, but some might be around and are not used


# Gitlab Pipeline

To use the scripts to deploy to AIA, commit a change and merge the change into the `qa` branch. From there the pipeline will build and push docker images and deploy changes to ECS.

See the [pipeline builds](https://gitlab.com/cslagile/business/ai-accelerator-usecases/scop-experimentation/-/pipelines) and [pipeline triggers](https://gitlab.com/cslagile/business/ai-accelerator-usecases/scop-experimentation/-/ci/editor?branch_name=main) and [pipeline definition](../.gitlab/ci/) or [committed pipeline definition](https://gitlab.com/cslagile/business/ai-accelerator-usecases/scop-experimentation/-/tree/qa/.gitlab/ci?ref_type=heads)


[Git commit hook](../bin/pre-commit) used during development, it is incomplete for some of the folders
