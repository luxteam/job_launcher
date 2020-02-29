import argparse
import datetime
import os
import shutil
import json
import uuid

import core.reportExporter
import core.system_info
from core.auto_dict import AutoDict
from core.config import *

import jobs_launcher.jobs_parser
import jobs_launcher.job_launcher

SCRIPTS = os.path.dirname(os.path.realpath(__file__))


def parse_cmd_variables(tests_root, cmd_variables):
    # if TestsFilter doesn't exist or is empty - set it 'full'
    if 'TestsFilter' not in cmd_variables.keys() or not cmd_variables['TestsFilter']:
        cmd_variables.update({'TestsFilter': 'full'})

    return cmd_variables


def main():

    level = 0
    delim = ' '*level

    parser = argparse.ArgumentParser()
    parser.add_argument('--tests_root', required=True, metavar="<dir>", help="tests root dir")
    parser.add_argument('--work_root', required=True, metavar="<dir>", help="tests root dir")
    parser.add_argument('--work_dir', required=False, metavar="<dir>", help="tests root dir")
    parser.add_argument('--cmd_variables', required=False, nargs="*")
    parser.add_argument('--test_filter', required=False, nargs="*", default=[])
    parser.add_argument('--package_filter', required=False, nargs="*", default=[])
    parser.add_argument('--file_filter', required=False)
    parser.add_argument('--execute_stages', required=False, nargs="*", default=[])

    args = parser.parse_args()

    main_logger.info('Started with args: {}'.format(args))

    if args.cmd_variables:
        args.cmd_variables = {
            args.cmd_variables[i]: args.cmd_variables[i+1] for i in range(0, len(args.cmd_variables), 2)
        }
        args.cmd_variables = parse_cmd_variables(args.tests_root, args.cmd_variables)
    else:
        args.cmd_variables = {}

    args.cmd_variables['TestCases'] = None

    args.tests_root = os.path.abspath(args.tests_root)

    main_logger.info('Args parsed to: {}'.format(args))

    tests_path = os.path.abspath(args.tests_root)
    work_path = os.path.abspath(args.work_root)

    if not args.work_dir:
        args.work_dir = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    work_path = os.path.join(work_path, args.work_dir)

    if not os.path.exists(work_path):
        try:
            os.makedirs(work_path)
        except OSError as e:
            main_logger.error(str(e))

    # session_dir = os.path.join(work_path, machine_info.get("host"))
    session_dir = work_path

    if '' in args.test_filter:
        args.test_filter = []

    if '' in args.package_filter:
        args.package_filter = []

    # extend test_filter by values in file_filter
    if args.file_filter and args.file_filter != 'none':
        try:
            with open(os.path.join(args.tests_root, args.file_filter), 'r') as file:
                if args.file_filter.endswith('json'):
                    args.cmd_variables['TestCases'] = args.file_filter
                    args.test_filter.extend([x for x in json.loads(file.read()).keys()])
                else:
                    args.test_filter.extend(file.read().splitlines())
        except Exception as e:
            main_logger.error(str(e))

    print('Working folder  : ' + work_path)
    print('Tests folder    : ' + tests_path)

    main_logger.info('Working folder: {}'.format(work_path))
    main_logger.info('Tests folder: {}'.format(tests_path))

    machine_info = core.system_info.get_machine_info()
    for mi in machine_info.keys():
        print('{0: <16}: {1}'.format(mi, machine_info[mi]))

    found_jobs = []
    report = AutoDict()
    report['failed_tests'] = []
    report['machine_info'] = machine_info
    report['guid'] = uuid.uuid1().__str__()

    try:
        if os.path.isdir(session_dir):
            shutil.rmtree(session_dir)
        os.makedirs(session_dir)
    except OSError as e:
        print(delim + str(e))
        main_logger.error(str(e))

    jobs_launcher.jobs_parser.parse_folder(level, tests_path, '', session_dir, found_jobs, args.cmd_variables,
                                           test_filter=args.test_filter, package_filter=args.package_filter)
    core.reportExporter.save_json_report(found_jobs, session_dir, 'found_jobs.json')

    for found_job in found_jobs:
        main_logger.info('Started job: {}'.format(found_job[0]))

        print("Processing {}  {}/{}".format(found_job[0], found_jobs.index(found_job)+1, len(found_jobs)))
        report['results'][found_job[0]][' '.join(found_job[1])] = {
            'result_path': '', 'total': 0, 'passed': 0, 'failed': 0, 'error': 0, 'skipped': 0, 'duration': 0
        }
        temp_path = os.path.abspath(found_job[4][0].format(SessionDir=session_dir))

        for i in range(len(found_job[3])):
            if (args.execute_stages and str(i + 1) in args.execute_stages) or not args.execute_stages:
                print("  Executing job {}/{}".format(i+1, len(found_job[3])))
                report['results'][found_job[0]][' '.join(found_job[1])]['duration'] += \
                    jobs_launcher.job_launcher.launch_job(found_job[3][i].format(SessionDir=session_dir), found_job[6][i])['duration']
            report['results'][found_job[0]][' '.join(found_job[1])]['result_path'] = os.path.relpath(temp_path, session_dir)

    # json_report = json.dumps(report, indent = 4)
    # print(json_report)

    print("Saving session report")
    core.reportExporter.build_session_report(report, session_dir)
    main_logger.info('Saved session report\n\n')
    shutil.copyfile('launcher.engine.log', os.path.join(session_dir, 'launcher.engine.log'))


if __name__ == "__main__":
    if not main():
        exit(0)
