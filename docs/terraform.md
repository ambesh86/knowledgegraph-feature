# Terraform

This document captures how terraform is used on the eugene project. Terraform scripts are used in two AWS environments; the `difflabs` and `AIA (ai ccelerator)`

Scripts:

* [difflabs tf](../difflabs/iac/) - run from local developer desktop
* [aia tf](../infrastructure/) - run from gitlab pipeline


# DIFFLABS TF

To use scripts to deploy to difflabs. 

* Paste credentials for the [aws account](./csl_aws.md)
* [build, tag and push docker](docker.md) changes
* Run terraform

First run `eugene-containers` setup - this is only needed once.

Note for all tf folders, modify the `difflabs.tfvars` as needed. The default values should work out of the box.

```
cd ./difflabs/iac/eugene-containers
./bin/init-difflabs.sh
./bin/plan-difflabs.sh
./bin/apply-difflabs.sh
```

Next deploy `eugene-services`

```
cd ./difflabs/iac/eugene-services
./bin/init-difflabs.sh
./bin/plan-difflabs.sh
./bin/apply-difflabs.sh
./bin/force-deployment.sh # (not always needed)
```

Note: The apply difflabs script might show an error about service not being idempotent. You can ignore that error, as it shows up every deployment. 

Ignore this error:

```
./bin/apply-difflabs.sh 
module.uspto.module.train.aws_ecs_service.training_service["subnet-07bd7b53c61cdd153"]: Creating...
module.uspto.module.mcp.aws_ecs_service.eugene_mcp_service["subnet-07bd7b53c61cdd153"]: Creating...
module.uspto.module.agent.aws_ecs_service.agent_web_service["subnet-07bd7b53c61cdd153"]: Creating...
module.uspto.module.search.aws_ecs_service.search_web_service["subnet-07bd7b53c61cdd153"]: Creating...
╷
│ Error: creating ECS Service (stage-eugene-agent-ws): operation error ECS: CreateService, https response error StatusCode: 400, RequestID: cc9d6a6c-77e6-4c71-b173-ac014afd4333, InvalidParameterException: Creation of service was not idempotent.
│ 
│   with module.uspto.module.agent.aws_ecs_service.agent_web_service["subnet-07bd7b53c61cdd153"],
│   on uspto/agent/ecs.tf line 69, in resource "aws_ecs_service" "agent_web_service":
│   69: resource "aws_ecs_service" "agent_web_service" {
│ 
╵
╷
│ Error: creating ECS Service (stage-eugene-mcp-ws): operation error ECS: CreateService, https response error StatusCode: 400, RequestID: d86bcf57-baca-4d01-9db8-e746365f094d, InvalidParameterException: Creation of service was not idempotent.
│ 
│   with module.uspto.module.mcp.aws_ecs_service.eugene_mcp_service["subnet-07bd7b53c61cdd153"],
│   on uspto/mcp/ecs.tf line 73, in resource "aws_ecs_service" "eugene_mcp_service":
│   73: resource "aws_ecs_service" "eugene_mcp_service" {
│ 
╵
╷
│ Error: creating ECS Service (stage-eugene-search-ws): operation error ECS: CreateService, https response error StatusCode: 400, RequestID: 7f31d0eb-e4ad-414e-b1ba-901886903cb6, InvalidParameterException: Creation of service was not idempotent.
│ 
│   with module.uspto.module.search.aws_ecs_service.search_web_service["subnet-07bd7b53c61cdd153"],
│   on uspto/search/ecs.tf line 86, in resource "aws_ecs_service" "search_web_service":
│   86: resource "aws_ecs_service" "search_web_service" {
│ 
╵
╷
│ Error: creating ECS Service (stage-eugene-training-service): operation error ECS: CreateService, https response error StatusCode: 400, RequestID: 8c5e085c-ebe0-4b8c-b405-72cd4b02bc94, InvalidParameterException: Creation of service was not idempotent.
│ 
│   with module.uspto.module.train.aws_ecs_service.training_service["subnet-07bd7b53c61cdd153"],
│   on uspto/train/ecs.tf line 65, in resource "aws_ecs_service" "training_service":
│   65: resource "aws_ecs_service" "training_service" {
│ 
```

Note: `eugene-database` and `eugene-loadbalancer` are not used as those resources were created manually out of band. However, the scripts should work if we need automation.

# AIA TF

To use the scripts to deploy to AIA, commit a change and merge the change into the `qa` branch. From there the pipeline will build and push docker images and deploy changes to ECS.

See [gitlab](./git.md)



