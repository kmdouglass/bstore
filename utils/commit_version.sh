#!/bin/bash

CURRENT_VERSION="v0.1.0a-rev"
HASH="$(git log --pretty=format:'%h' -n 1)"
echo "__DataSTORM_Version__ = '$CURRENT_VERSION${HASH}'" > 'DataSTORM/config.py'
git add DataSTORM/config.py
git commit -m "Update git hash tracking."
