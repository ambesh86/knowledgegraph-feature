#!/usr/bin/env bash

uv sync
uv export --format requirements-txt > requirements.txt --no-hashes
uv pip sync ./requirements.txt
