#!/usr/bin/env bash

set -euo pipefail

docker compose up -d
yarn codegen
yarn build
yarn subql-node-cosmos --db-schema app --force-clean