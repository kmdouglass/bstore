#!/bin/bash

# Updates the first line of config with the version number
# Run this after a commit where the commit ID should be updated.
CURRENT_VERSION="v0.1.0b-"
HASH="$(git log --pretty=format:'%h' -n 1)"
sed -i "1s/.*/__bstore_Version__ = \'$CURRENT_VERSION${HASH}\'/" bstore/config.py
git add bstore/config.py
git commit -m "Update git hash tracking."
