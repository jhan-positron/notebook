#!/bin/bash
# GIT_SEQUENCE_EDITOR: turn the pick of commit b03a9c4ab5 into a reword.
sed -i 's/^pick b03a9c4ab5 /reword b03a9c4ab5 /' "$1"
