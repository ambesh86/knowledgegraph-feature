#!/usr/bin/env bash

set -ou pipefail

mlflow ui --backend-store-uri sqlite:///mlflow.db --port 5000
