set PATH=c:\python35\;c:\python35\scripts\;%PATH%
set REPORTS_DIR=%1
set BRANCH_NAME=%2
python -c "import core.reportExporter; core.reportExporter.build_summary_reports('%REPORTS_DIR%' '%BRANCH_NAME%')"