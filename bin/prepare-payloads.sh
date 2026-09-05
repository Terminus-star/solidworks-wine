#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
source "$SCRIPT_DIR/common.sh"
if [[ "${1:-}" == '--help' ]]; then
    printf 'Usage: prepare-payloads.sh\nPrepare Spatial IOP and scheduler resources in the selected prefix.\n'
    exit 0
fi
prepare_wine_environment
require_prefix
prepare_spatial_iop_payload
stage_scheduler_resources
