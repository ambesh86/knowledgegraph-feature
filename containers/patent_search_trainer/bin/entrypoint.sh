#!/usr/bin/env bash

set -euxo pipefail

download_and_source_env () {
    # fetch latest .env file
    aws s3 cp s3://${S3_STAGING_BUCKET}/runtime/.env .

    # source all the variables
    [ ! -f .env ] || export $(grep -v '^#' .env | xargs)
}

download_and_source_env \
    && python src/train_for_search.py --dimension-size 768 \
    && exit 0