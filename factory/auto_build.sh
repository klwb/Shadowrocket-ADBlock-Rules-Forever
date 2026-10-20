#!/bin/bash
set -euo pipefail

Path=./factory
cd $Path

if [[ "${1:-}" == "--from-local-sources" ]]; then
  shift
else
  python3 ad.py
  python3 gfwlist.py
  python3 passwall_like.py
fi
python3 build_confs.py "$@"
