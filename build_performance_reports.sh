#!/bin/bash
python3.9 -c "import core.reportExporter; core.reportExporter.build_performance_reports('$1', major_title='$2', commit_sha='$3', branch_name='$4', commit_message='$5', build_number='$6')"
