set PATH=c:\python39\;c:\python39\scripts\;%PATH%

set FILES_PATH=%1
set PATTERN=%2
set DEST_DIR=%3
set DEST_DIR_OPTION=

if defined DEST_DIR set DEST_DIR_OPTION=--dest_dir %DEST_DIR%

python send_to_minio.py --files_path %FILES_PATH% --pattern %PATTERN% %DEST_DIR_OPTION%