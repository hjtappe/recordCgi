#!/bin/bash

# Sample script which will be called with the mp3 file
# as an argument, which can be used to copy the MP3 file or do other actions
# after a successful file transcoding

# exit on unknown variables
set -u

# preset some variables.
THISDIR="$(dirname $0)"
RET=0
COPY_FILE=${1:-}

if [ -z "$COPY_FILE" ]; then
	echo >&2 "First argument must be the file to handle."
	exit 1
fi
if [ ! -r "$COPY_FILE" ]; then
	echo >&2 "First argument must be a readable file."
	exit 1
fi

#################################
TARGET_DIR="$THISDIR/public-records"

# keep the last 3 old records and their descriptions, removing the rest.
find "${TARGET_DIR}/" -maxdepth 1 -mindepth 1 -type f -mtime +31 -name "${FILE_BASE}*" -exec rm -v {} \;

# Copy the files to the target directory.
cp -v "${COPY_FILE}" "${TARGET_DIR}/"
RET=$?
# Be sure, data is on the disk
sync
#################################

exit $RET
