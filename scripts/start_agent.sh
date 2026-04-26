#!/usr/bin/env bash

cd ../service
source .venv/bin/activate
python -m redteam_agent.api
