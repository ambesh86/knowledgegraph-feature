#!/usr/bin/env bash

set -eou pipefail

python src/openai_eval.py --items on_topic
