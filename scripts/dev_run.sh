#!/usr/bin/env bash
# Run the api or worker locally against the dev database (.secrets/dev.env).
cd "$(dirname "$0")/.."
. .secrets/dev.env
exec .venv/Scripts/mf "$@"
