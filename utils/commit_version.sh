#!/bin/bash

# Commits changes to the Git repo, then updates the first line 
# of config with the version number and commit.
git commit
CURRENT_VERSION="v1.1.0-"
HASH="$(git log --pretty=format:'%h' -n 1)"
sed -i "1s/.*/__bstore_Version__ = \'$CURRENT_VERSION${HASH}\'/" bstore/config.py
git add bstore/config.py
git commit --amend -m "Update version number in config.py."
