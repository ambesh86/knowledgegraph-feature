#!/usr/bin/env bash

set -euxo pipefail

download_and_source_env() {
    # fetch latest .env file
    aws s3 cp s3://${S3_STAGING_BUCKET}/runtime/.env .

    # source all the variables
    [ ! -f .env ] || export $(grep -v '^#' .env | xargs)
}

download_huggingface_models() {
    # fetch models file
    # the env file should set to HF_OFFLINE to true and point to this CACHE dir
    cd $HOME/.cache/huggingface/hub
    aws s3 cp s3://${S3_STAGING_BUCKET}/build/minishlab.zip .
    unzip minishlab.zip && rm -rf minishlab.zip
    cd -
}

ls -alh

download_huggingface_models \
    &&  download_and_source_env \
    && uvicorn eugene_ws:app --app-dir src --host 0.0.0.0 --port 8000