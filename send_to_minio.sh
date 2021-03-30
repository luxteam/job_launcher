#!/bin/bash
FILES_PATH="$1"
PATTERN="$2"

/usr/local/bin/python3.9 send_to_minio.py --files_path $FILES_PATH --pattern $PATTERN