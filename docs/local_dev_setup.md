# Local deveopment setup

This document lists tools and some setup needed for local development


## Install

git

python 3.12+ < python 3.14 (3.14 has caused a few problems maybe because it is still new)

docker

vscode

terraform

neo4j desktop2

## Install venv

Many project have their own folder and requirements.txt file which will correspond to their own venv. The eugene_ws and graphrag live together in the src folder, but each require their own venv and requirements.txt

So I made two venv 

`venv_eugene_ws` and `venv_graphrag_ingest`. The other folders are microservices and not a monorepo and can the runtime can be managed individually.

## Add saved queries to neo4j desktop

My saved [queries](../eugene/saved_queries/neo4j_query_saved_cypher.csv)

## Building Docker Containers Locally

docker settings if building container locally. The docker default cloudflare url might not work behind the zscaler vpn, so you might need to change the registry mirror

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

## Git

Install [githook](../bin/pre-commit)



## Vscode

If using vscode, here is my python debugging and testrunner configurations in `.vscode`

launch.json
```json
{
    // Use IntelliSense to learn about possible attributes.
    // Hover to view descriptions of existing attributes.
    // For more information, visit: https://go.microsoft.com/fwlink/?linkid=830387
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python Debugger: Current File",
            "type": "debugpy",
            "request": "launch",
            "program": "${file}",
            "console": "integratedTerminal",
            "stopOnEntry": true,
            "justMyCode": false,
            "pythonArgs": [
                "-Xfrozen_modules=off",
                "-Xdev"
            ],
            "purpose": [
                "debug-test"
            ],
            "env": {
                "PYDEVD_DISABLE_FILE_VALIDATION": "1",
                "PYTEST_ADDOPTS": "--no-cov",
                "AWS_ACCESS_KEY_ID": "",
                "AWS_SECRET_ACCESS_KEY": "",
                "AWS_SESSION_TOKEN": ""
            }
        }
    ]
}
```

settings.json
```json
{
    "python.analysis.autoImportCompletions": true,
    "python.testing.pytestArgs": [
        "src",
        "-s"
    ],
    "python.testing.unittestEnabled": false,
    "python.testing.pytestEnabled": true,
    "python.envFile": "${workspaceFolder}/.env",
    "python.experiments.enabled": true,
    "python.experiments.optInto": [
        "pythonTestAdapter"
    ]
}
```