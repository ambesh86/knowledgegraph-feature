# Project folders

This document captures information about the EUGENE project folder structure.



* [agents](../agents/) - has several subfolders for agentic and MCP projects
* [api-canaries](../api-canaries/) - contains a single project used to monitor the `eugene_ws` webservice
* [bin](../bin) - simple bash scripts used during local development or maintenance 
* [containers](../containers/) - docker image definitions for the `AIA` environment
* [difflabs](../difflabs/) - docker images and terraform scripts used for the `difflabs` environment
* [docs](../docs) - documentation, mostly for handover
* [eugene](../eugene/) - base folder used for installing and setting up the eugene database. Also contains one off cypher scripts.
* [infrastructure](../infrastructure/) - infrastructure as code terraform files used to deploy to the `AIA` environment. Called in the gitlab pipeline
* [output](../output/) - used during local scripts runs to store output and checkpoints. Sometimes the data backedup in the `difflabs` [s3](https://us-east-1.console.aws.amazon.com/s3/buckets/knowledge-graph-external-data?region=us-east-1) to avoid reprocessing
* [resources](../resources/) - stores input for local scripts, or test data
* [src](../src/) - `eugene_ws` and `graphrag` code.



All source code files are inspired by [domain driven design and hexagonal architecture](https://vaadin.com/blog/ddd-part-3-domain-driven-design-and-the-hexagonal-architecture) concepts.

You will see the following python source code folder structure

```
<domain> - some specific domain like pubmed
    model - models
    provider - services
    conf - dependency injection
    mapper - convert models to different formats or models
    load - load models from disk, sometimes checkpoint files
    writer - output or checkpoint models in different formats
    router - enpoint and fastapi routers
infra - base folder to hold non pure domain but classes to interact with infrastructure like llms or databases 
    db - hold database adapters; per hexagonal architecture
```