#!/usr/bin/env bash
set -e
echo "================================================================================"
echo "                   Starting SI Scout Local Dashboard                            "
echo "================================================================================"
python3 ui/app.py || python ui/app.py
