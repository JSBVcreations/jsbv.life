#!/bin/bash
# Install (or remove, with --remove) the launchd agent that runs scripts/update.py by itself:
# daily at 6:00 and whenever something lands in "jsbv data/inbox". It never commits or pushes.
#   bash scripts/launchd/install.sh            install / refresh
#   bash scripts/launchd/install.sh --remove   uninstall
# The agent's python3 needs Full Disk Access once (System Settings > Privacy & Security > Full Disk Access),
# because ~/Documents and the Photos library are protected. Log: ~/Library/Logs/jsbv-update.log
set -e
LABEL=life.jsbv.update
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
DATA="${JSBV_DATA:-$HOME/Documents/00-Database/jsbv data}"
PY="$(command -v python3)"
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
if [ "$1" = "--remove" ]; then rm -f "$PLIST"; echo "removed $LABEL"; exit 0; fi
mkdir -p "$DATA/inbox" "$HOME/Library/LaunchAgents"
esc() { printf '%s' "$1" | sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g'; }
cat > "$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key><array><string>$(esc "$PY")</string><string>$(esc "$REPO/scripts/update.py")</string><string>--notify</string></array>
  <key>WorkingDirectory</key><string>$(esc "$REPO")</string>
  <key>EnvironmentVariables</key><dict><key>JSBV_DATA</key><string>$(esc "$DATA")</string></dict>
  <key>StartCalendarInterval</key><dict><key>Hour</key><integer>6</integer><key>Minute</key><integer>0</integer></dict>
  <key>WatchPaths</key><array><string>$(esc "$DATA/inbox")</string></array>
  <key>ThrottleInterval</key><integer>120</integer>
  <key>StandardOutPath</key><string>$(esc "$HOME/Library/Logs/jsbv-update.log")</string>
  <key>StandardErrorPath</key><string>$(esc "$HOME/Library/Logs/jsbv-update.log")</string>
</dict></plist>
PL
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "installed $LABEL: daily 6:00 + on new files in $DATA/inbox (python: $PY)"
echo "If the log shows 'Operation not permitted', give $PY Full Disk Access."
