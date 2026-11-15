#!/bin/bash
# Double-click to refresh every data source on jsbv.life. Details: docs/UPDATING.md
cd "$(dirname "$0")" || exit 1
python3 scripts/update.py "$@"
status=$?
echo
read -n 1 -s -r -p "Press any key to open GitHub Desktop (commit + push there), or just close this window."
echo
open -a "GitHub Desktop" . 2>/dev/null || echo "GitHub Desktop not found; commit and push however you usually do."
exit $status
