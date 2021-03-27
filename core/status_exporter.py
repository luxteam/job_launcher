import os
import json
import argparse
from core.config import *


def main(work_dir='', multiple_reports='False'):
    args_parser = argparse.ArgumentParser()
    args_parser.add_argument('--work_dir')
    args_parser.add_argument('--multiple_reports')
    args = args_parser.parse_args()

    if work_dir:
        args.work_dir = work_dir
    if multiple_reports:
        args.multiple_reports = multiple_reports

    summary_report = {}
    results = {}
    max_name = 0
    total = {'total': 0, 'passed': 0, 'failed': 0, 'error': 0, 'skipped': 0, 'duration': 0, 'render_duration': 0}
    status_to_export = ""

    if args.multiple_reports == 'True':
        report_directories = next(os.walk(os.path.abspath(args.work_dir)))[1]
    else:
        report_directories = ['']

    for report_directory in report_directories:
        report_path = os.path.join(args.work_dir, report_directory, SUMMARY_REPORT)
        if os.path.exists(report_path):
            with open(report_path, 'r') as file:
                summary_report = json.load(file)

                if len(summary_report) == 0:
                    continue

                if not max_name:
                    max_name = max([len(x) for x in summary_report.keys()])
                    max_name = max(max_name, 12)

                for execution in summary_report:
                    if execution not in results:
                        results[execution] = {}
                        results[execution]['total'] = 0
                        results[execution]['passed'] = 0
                        results[execution]['failed'] = 0
                        results[execution]['error'] = 0
                        results[execution]['skipped'] = 0
                    results[execution]['total'] += summary_report[execution]['summary']['total']
                    results[execution]['passed'] += summary_report[execution]['summary']['passed']
                    results[execution]['failed'] += summary_report[execution]['summary']['failed']
                    results[execution]['error'] += summary_report[execution]['summary']['error']
                    results[execution]['skipped'] += summary_report[execution]['summary']['skipped']

    for execution in results:
        status_to_export += "_{: <{name_fill}}_ | *{}*/{}/`{}`/`{}`/{}\n".format(
            execution,
            results[execution]['total'],
            results[execution]['passed'],
            results[execution]['failed'],
            results[execution]['error'],
            results[execution]['skipped'],
            name_fill=max_name
        )

    status_to_export = "_{: <{name_fill}}_ | *total*/passed/`failed`/`error`/skipped\n".format("Test Machine", name_fill=max_name) + status_to_export
    # get summary results
    for execution in results:
        for key in total:
            if key in results[execution]:
                total[key] += results[execution][key]

    with open(os.path.join(args.work_dir, 'summary_status.json'), 'w') as file:
        json.dump(total, file, indent=' ')

    with open(os.path.join(args.work_dir, 'slack_status.json'), 'w') as file:
        json.dump(status_to_export, file, indent=' ')


if __name__ == '__main__':
    main()
