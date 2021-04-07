set PATH=c:\python39\;c:\python39\scripts\;%PATH%
set PYTHONPATH=..\jobs_launcher\;%PYTHONPATH%

set GPU=%1
set OS=%2
set ENGINE=%3
set TESTS_PATH=%4

python core\\isGroupSkipped.py --gpu %GPU% --os %OS% --engine %ENGINE% --tests_path %TESTS_PATH%