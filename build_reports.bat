set PATH=c:\python35\;c:\python35\scripts\;%PATH%
rem commit_message should be last arg because of eof in the end of commit message
python -c "import core.reportExporter; core.reportExporter.build_summary_reports('%1', major_title='%2', commit_sha='%3', branch_name='%4', node_retry_info='%~5', commit_message='%6')"