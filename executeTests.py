import argparse
import datetime
import os
import shutil
import json
import uuid
import traceback
import subprocess
import time

import core.reportExporter
import core.system_info
from core.auto_dict import AutoDict
from core.config import *
try:
    from local_config import *
except ImportError:
    main_logger.critical("local config file not found. Default values will be used.")
    main_logger.critical("Correct report building isn't guaranteed")
    from core.defaults_local_config import *


import jobs_launcher.jobs_parser
import jobs_launcher.job_launcher

from ums_client import create_ums_client, str2bool
from image_service_client import ISClient
from minio_client import create_mc_client


SCRIPTS = os.path.dirname(os.path.realpath(__file__))


def parse_cmd_variables(tests_root, cmd_variables):
    # if TestsFilter doesn't exist or is empty - set it 'full'
    if 'TestsFilter' not in cmd_variables.keys() or not cmd_variables['TestsFilter']:
        cmd_variables.update({'TestsFilter': 'full'})

    return cmd_variables


def send_machine_info(ums_client, machine_info, args):
    print('Tests filter: ' + str(args.test_filter))
    for group in args.test_filter:
        delete_chars = ' ,[]"'
        group = group.translate(str.maketrans("", "", delete_chars))
        ums_client.get_suite_id_by_name(group)
        # send machine info to ums
        env = {"gpu": core.system_info.get_gpu(), **machine_info}
        env.pop('os')
        env.update({'hostname': env.pop('host'), 'cpu_count': int(env['cpu_count'])})
        ums_client.define_environment(env)


def main():

    # create UMS client
    ums_client_prod = None
    ums_client_dev = None
    use_ums = None
    mc_prod = None
    mc_dev = None
    try:
        main_logger.info("Try to get environment variable UMS_USE")
        use_ums = str2bool(os.getenv('UMS_USE'))
    except Exception as e:
        main_logger.error('Exception when getenv UMS USE: {}'.format(str(e)))
    if use_ums:
        main_logger.info("Try to create Production UMS client")
        ums_client_prod = create_ums_client("PROD")
        main_logger.info("Try to create Develop UMS client")
        ums_client_dev = create_ums_client("DEV")
    else:
        main_logger.info("UMS_USE set as false")

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
            file_name = args.file_filter.split('~')[0]
            with open(os.path.join(args.tests_root, file_name), 'r') as file:
                file_content = json.load(file)
                # exclude some tests from non-splitted tests package
                if not file_content['split']:
                    # save path to tests package
                    args.cmd_variables['TestCases'] = os.path.abspath(os.path.join(args.tests_root, file_name))
                    excluded_tests = args.file_filter.split('~')[1].split(',')
                    args.test_filter.extend([x for x in file_content['groups'].keys() if x not in excluded_tests])
        except Exception as e:
            main_logger.error(str(e))

    print('Working folder  : ' + work_path)
    print('Tests folder    : ' + tests_path)

    main_logger.info('Working folder: {}'.format(work_path))
    main_logger.info('Tests folder: {}'.format(tests_path))

    machine_info = core.system_info.get_machine_info()
    for mi in machine_info.keys():
        print('{0: <16}: {1}'.format(mi, machine_info[mi]))


    # send machine info to ums
    if ums_client_prod:
        send_machine_info(ums_client_prod, machine_info, args)
    if ums_client_dev:
        send_machine_info(ums_client_dev, machine_info, args)

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
        
        if ums_client_prod or ums_client_dev:
            # TODO: Monitoring start
            interval = 5
            main_logger.info('Started monitoring: {}'.format(found_job[0]))
            monitor = subprocess.Popen([
                "python",
                os.path.join("..", "jobs_launcher", "progress_monitor.py"),
                "--interval",
                str(interval),
                "--session_dir",
                session_dir,
                "--suite_name",
                found_job[0]
            ])

        print("Processing {}  {}/{}".format(found_job[0], found_jobs.index(found_job)+1, len(found_jobs)))
        main_logger.info("Processing {}  {}/{}".format(found_job[0], found_jobs.index(found_job)+1, len(found_jobs)))
        report['results'][found_job[0]][' '.join(found_job[1])] = {
            'result_path': '', 'total': 0, 'passed': 0, 'failed': 0, 'error': 0, 'skipped': 0, 'duration': 0, 'synchronization_duration': 0
        }
        temp_path = os.path.abspath(found_job[4][0].format(SessionDir=session_dir))

        for i in range(len(found_job[3])):
            if (args.execute_stages and str(i + 1) in args.execute_stages) or not args.execute_stages:
                print("  Executing job {}/{}".format(i+1, len(found_job[3])))
                main_logger.info("  Executing job {}/{}".format(i+1, len(found_job[3])))
                job_launcher_report = jobs_launcher.job_launcher.launch_job(found_job[3][i].format(SessionDir=session_dir), found_job[6][i])
                report['results'][found_job[0]][' '.join(found_job[1])]['duration'] += job_launcher_report['report']['duration']
            report['results'][found_job[0]][' '.join(found_job[1])]['result_path'] = os.path.relpath(temp_path, session_dir)

            if (i == 0) and (ums_client_prod or ums_client_dev):
                if job_launcher_report['rc'] != -10:
                    try:
                        monitor.wait()
                    except Exception as e:
                        main_logger.error(str(e))
                # job was terminated due to timeout - kill monitor
                else:
                    try:
                        monitor.terminate()
                        time.sleep(5)
                        monitor.kill()
                    except Exception as e:
                        main_logger.error(str(e))
        main_logger.newline()

    # json_report = json.dumps(report, indent = 4)
    # print(json_report)

    print("Saving session report")
    core.reportExporter.build_session_report(report, session_dir)
    main_logger.info('Saved session report\n\n')

    if ums_client_prod or ums_client_dev:
        main_logger.info("Try to send results to UMS")

        if ums_client_prod:
            main_logger.info("Try to create Production MINIO client")
            mc_prod = create_mc_client(ums_client_prod.job_id)
        if ums_client_dev:
            main_logger.info("Try to create Develop MINIO client")
            mc_dev = create_mc_client(ums_client_dev.job_id)

        try:
            main_logger.info('Start preparing results')
            cases = []
            suites = []

            with open(os.path.join(session_dir, SESSION_REPORT)) as file:
                data = json.loads(file.read())
                suites = data["results"]

            for suite_name, suite_result in suites.items():
                events_data = []
                summary_sync_time = 0
                try:
                    events_data_path = os.path.join(session_dir, suite_name + "_performance_ums.json")
                    if os.path.exists(events_data_path):
                        with open(events_data_path, 'r') as json_file:
                            events_data = json.load(json_file)
                except Exception as e:
                    main_logger.error("Can't read performance data: {}".format(str(e)))
                    main_logger.error("Traceback: {}".format(traceback.format_exc()))
                res = []
                cases = suite_result[""]["render_results"]
                if ums_client_prod:
                    ums_client_prod.get_suite_id_by_name(suite_name)
                if ums_client_dev:
                    ums_client_dev.get_suite_id_by_name(suite_name)
                for case in cases:
                    try:
                        summary_sync_time += case.get('sync_time', 0)

                        if 'rendered_image_is_id' in case:
                            rendered_image = str(case['rendered_image_is_id'])
                        else:
                            rendered_image = 'error'

                        if 'error_screen_is_id' in case:
                            error_screen = str(case['error_screen_is_id'])
                        else:
                            error_screen = ''

                        case_info = {}
                        for key in case:
                            if key in UMS_POSSIBLE_INFO_FIELD:
                                case_info[key] = case[key]
                                    
                        res.append({
                            'name': case['test_case'],
                            'status': case['test_status'],
                            'metrics': {
                                'render_time': case['render_time']
                            },
                            "artefacts": {
                                "rendered_image": rendered_image,
                                "error_screen": error_screen
                            },
                            "info": case_info
                        })
                        
                        path_to_test_case_log = os.path.join(session_dir, suite_name, 'render_tool_logs', case["test_case"] + ".log")
                        if os.path.exists(path_to_test_case_log):
                            if ums_client_prod and mc_prod:
                                mc_prod.upload_file(path_to_test_case_log, "PROD",ums_client_prod.build_id,
                                    ums_client_prod.suite_id, ums_client_prod.env_label, case["test_case"])
                            if ums_client_dev and mc_dev:
                                mc_dev.upload_file(path_to_test_case_log, "DEV", ums_client_dev.build_id,
                                    ums_client_dev.suite_id, ums_client_dev.env_label, case["test_case"])
                    except Exception as e1:
                        if 'test_case' in case:
                            main_logger.error("UMS failed to prepare results for case {}. Error: {}".format(case['test_case'], str(e1)))
                        main_logger.error("Traceback: {}".format(traceback.format_exc()))
                #TODO: send logs for each test cases
                
                # logs from suite dir
                test_suite_artefacts = {"renderTool.log", "render_log.txt", "test_cases.json"}
                for artefact in test_suite_artefacts:
                    path_to_test_suite_render_log = os.path.join(session_dir, suite_name, artefact)
                    if os.path.exists(path_to_test_suite_render_log):
                        if ums_client_prod and mc_prod:
                            mc_prod.upload_file(path_to_test_suite_render_log, "PROD",
                                ums_client_prod.build_id, ums_client_prod.suite_id, ums_client_prod.env_label)
                        if ums_client_dev and mc_dev:
                            mc_dev.upload_file(path_to_test_suite_render_log, "DEV",
                                ums_client_dev.build_id, ums_client_dev.suite_id, ums_client_dev.env_label)

                if ums_client_prod:
                    ums_client_prod.get_suite_id_by_name(suite_name)
                if ums_client_dev:
                    ums_client_dev.get_suite_id_by_name(suite_name)
                # send machine info to ums
                env = {"gpu": core.system_info.get_gpu(), **core.system_info.get_machine_info()}
                env.pop('os')
                env.update({'hostname': env.pop('host'), 'cpu_count': int(env['cpu_count'])})
                main_logger.info("Generated results:\n{}".format(json.dumps(res, indent=2)))
                main_logger.info("Environment: {}".format(env))

                # calculate time of 'Refactor logs' step
                if events_data:
                    try:
                        sum_steps = 0
                        for event_data in events_data:
                            sum_steps += event_data['time']
                        session_report_path = os.path.join(session_dir, "session_report.json")
                        if os.path.exists(session_report_path):
                            with open(session_report_path, 'r') as json_file:
                                data = json.load(json_file)
                                duration = data['results'][suite_name]['']['duration']
                                render_duration = data['results'][suite_name]['']['render_duration']
                                events_data.append({'name': 'Refactor logs', 'time': duration - sum_steps - render_duration - summary_sync_time})
                    except Exception as e:
                        main_logger.error("Can't calculate time of 'Refactor logs' step: {}".format(str(e)))
                        main_logger.error("Traceback: {}".format(traceback.format_exc()))
                # collect performance data
                performance_data = {'setup_time': events_data, 'sync_time': summary_sync_time}
                main_logger.info("Generated performance data:\n{}".format(json.dumps(performance_data, indent=2)))

                test_suite_result_id_prod = None
                test_suite_result_id_dev = None
                send_try = 0
                if ums_client_prod and ums_client_prod.suite_id:
                    while send_try < MAX_UMS_SEND_RETRIES:
                        response_prod = ums_client_prod.send_test_suite(res=res, env=env)
                        main_logger.info('Test suite results sent to UMS PROD with code {} (try #{})'.format(response_prod.status_code, send_try))
                        main_logger.info('Response from UMS PROD: \n{}'.format(response_prod.content))
                        if response_prod and response_prod.status_code < 300:
                            response_data = json.loads(response_prod.content.decode("utf-8"))
                            if 'data' in response_data and 'test_suite_result_id' in response_data['data']:
                                test_suite_result_id_prod = response_data['data']['test_suite_result_id']
                            break
                        send_try += 1
                        time.sleep(UMS_SEND_RETRY_INTERVAL)
                else:
                    main_logger.info('Result for test suite {} won\'t be send on UMS PROD due to empty suite_id'.format(suite_name))

                if test_suite_result_id_prod:
                    send_try = 0
                    while send_try < MAX_UMS_SEND_RETRIES:
                        response_prod = ums_client_prod.send_test_suite_performance(data=performance_data, test_suite_result_id=test_suite_result_id_prod)
                        main_logger.info('Test suite performance sent for {} to UMS PROD with code {} (try #{})'.format(test_suite_result_id_prod, response_prod.status_code, send_try))
                        main_logger.info('Response from UMS PROD: \n{}'.format(response_prod.content))
                        if response_prod and response_prod.status_code < 300:
                            break
                        send_try += 1
                        time.sleep(UMS_SEND_RETRY_INTERVAL)
                else:
                    main_logger.info("UMS client did not set. Result won't be sent to UMS PROD")

                send_try = 0
                if ums_client_dev and ums_client_dev.suite_id:
                    while send_try < MAX_UMS_SEND_RETRIES:
                        response_dev = ums_client_dev.send_test_suite(res=res, env=env)
                        main_logger.info('Test suite results sent to UMS DEV with code {} (try #{})'.format(response_dev.status_code, send_try))
                        main_logger.info('Response from UMS DEV: \n{}'.format(response_dev.content))
                        if response_dev and response_dev.status_code < 300:
                            response_data = json.loads(response_dev.content.decode("utf-8"))
                            if 'data' in response_data and 'test_suite_result_id' in response_data['data']:
                                test_suite_result_id_dev = response_data['data']['test_suite_result_id']
                            break
                        send_try += 1
                        time.sleep(UMS_SEND_RETRY_INTERVAL)
                else:
                    main_logger.info('Result for test suite {} won\'t be send on UMS DEV due to empty suite_id'.format(suite_name))

                if test_suite_result_id_dev:
                    send_try = 0
                    while send_try < MAX_UMS_SEND_RETRIES:
                        response_dev = ums_client_dev.send_test_suite_performance(data=performance_data, test_suite_result_id=test_suite_result_id_dev)
                        main_logger.info('Test suite performance sent for {} to UMS DEV with code {} (try #{})'.format(test_suite_result_id_dev, response_dev.status_code, send_try))
                        main_logger.info('Response from UMS DEV: \n{}'.format(response_dev.content))
                        if response_dev and response_dev.status_code < 300:
                            break
                        send_try += 1
                        time.sleep(UMS_SEND_RETRY_INTERVAL)
                else:
                    main_logger.info("UMS client did not set. Result won't be sent to UMS DEV")

            shutil.copyfile('launcher.engine.log', os.path.join(session_dir, 'launcher.engine.log'))

            test_suite_artefacts = ("launcher.engine.log", "found_jobs.json")

            for artefact in test_suite_artefacts:
                path_to_test_suite_render_log = os.path.join(session_dir, artefact)
                # send logs to suites dirs
                for suite in suites:
                    if ums_client_prod and mc_prod:
                        ums_client_prod.get_suite_id_by_name(suite_name)
                        mc_prod.upload_file(path_to_test_suite_render_log, "PROD",
                            ums_client_prod.build_id, ums_client_prod.suite_id, ums_client_prod.env_label)
                    if ums_client_dev and mc_dev:
                        ums_client_dev.get_suite_id_by_name(suite_name)
                        mc_dev.upload_file(path_to_test_suite_render_log, "DEV",
                            ums_client_dev.build_id, ums_client_dev.suite_id, ums_client_dev.env_label)


        except Exception as e:
            main_logger.error("UMS Failed in preparing test cases results and sending")
            main_logger.error("Traceback: {}".format(traceback.format_exc()))
            shutil.copyfile('launcher.engine.log', os.path.join(session_dir, 'launcher.engine.log'))
    else:
        main_logger.info("UMS client did not set. Result won't be sent to UMS")
        shutil.copyfile('launcher.engine.log', os.path.join(session_dir, 'launcher.engine.log'))


if __name__ == "__main__":
    if not main():
        exit(0)
