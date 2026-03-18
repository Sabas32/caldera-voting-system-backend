#!/usr/bin/env bash
set -euo pipefail

celery -A voting_system.config beat -l info
