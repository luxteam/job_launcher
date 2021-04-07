#!/bin/bash
SKIPPED_CASES_PATH="$1"
ERROR_CASES_PATH="$2"
RETRY_INFO_PATH="$3"

python3.9 send_stubs_to_ums.py --path_to_skipped_cases $SKIPPED_CASES_PATH --path_to_error_cases $ERROR_CASES_PATH --path_to_retry_info $RETRY_INFO_PATH
