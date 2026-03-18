#!/usr/bin/env bash
set -euo pipefail

celery -A voting_system.config worker -l info
