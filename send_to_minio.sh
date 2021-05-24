#!/bin/bash
FILES_PATH="$1"
PATTERN="$2"
DEST_DIR="$3"

if [ -z "$DEST_DIR" ] 
then
        DEST_DIR_OPTION=""
else
        DEST_DIR_OPTION="--dest_dir $DEST_DIR"
fi

python3.9 send_to_minio.py --files_path $FILES_PATH --pattern $PATTERN $DEST_DIR_OPTION