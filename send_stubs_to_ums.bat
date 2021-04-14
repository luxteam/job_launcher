set PATH=c:\python39\;c:\python39\scripts\;%PATH%
set PYTHONPATH=..\jobs_launcher\;%PYTHONPATH%

set SKIPPED_CASES_PATH=%1
set ERROR_CASES_PATH=%2
set RETRY_INFO_PATH=%3

python send_stubs_to_ums.py --path_to_skipped_cases %SKIPPED_CASES_PATH% --path_to_error_cases %ERROR_CASES_PATH% --path_to_retry_info %RETRY_INFO_PATH%