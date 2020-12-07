import os
import argparse
import json
import time
import traceback

from core.config import *
from ums_client import create_ums_client
from core.countLostTests import PLATFORM_CONVERTATIONS, LABELS_CONVERTATIONS


def generate_stubs(cases_names, status):
    cases = []
    try:
        for case_name in cases_names:
            cases.append({
                "name": case_name,
                "status": status,
                "metrics": {
                    "render_time": -0.0
                },
                "artefacts": {
                    "rendered_image": status
                },
            })
    except Exception as e:
        main_logger.error("Failed to generate stubs. Exception: {}".format(str(e)))
        main_logger.error("Traceback: {}".format(traceback.format_exc()))
    return cases


def prepare_ums_clients(gpu_os_name, suite_name, status, node_retry_info):
    ums_client_prod = None
    ums_client_dev = None
    env = {}
    try:
        host_name = "Unknown"
        gpu_name = gpu_os_name.split('-')[0]
        os_name = gpu_os_name.split('-')[1]
        gpu_label = LABELS_CONVERTATIONS[os_name]["cards"][gpu_name]
        os_label = LABELS_CONVERTATIONS[os_name]["os_name"]
        if status == "error":
            for retry_info in node_retry_info:
                try:
                    retry_gpu_name = PLATFORM_CONVERTATIONS[retry_info["osName"]]["cards"][retry_info["gpuName"]]
                    retry_os_name = PLATFORM_CONVERTATIONS[retry_info["osName"]]["os_name"]
                    if retry_gpu_name in gpu_os_name and retry_os_name in gpu_os_name:
                        for groups in retry_info["Tries"]:
                            package_or_default_execution = None
                            for group in groups.keys():
                                parsed_group_name = group.split('~')[0]
                                #all non splitTestsExecution and non regression builds (e.g. any build of core)
                                if "DefaultExecution" in group:
                                    package_or_default_execution = group
                                    break
                                elif parsed_group_name.endswith(".json") and suite_name not in group.split('~')[1]:
                                    with open(os.path.abspath(os.path.join("..", "jobs", parsed_group_name))) as f:
                                        if suite_name in json.load(f)["groups"]:
                                            package_or_default_execution = group
                                            break
                            if suite_name in groups.keys() or package_or_default_execution:
                                for test_tries in retry_info["Tries"]:
                                    if suite_name in test_tries:
                                        host_name = groups[suite_name][-1]["host"]
                                        break
                                if not host_name and package_or_default_execution:
                                    host_name = groups[package_or_default_execution][-1]["host"]
                except Exception as e:
                    main_logger.error("Failed to process retry info. ReasExceptionon: {}".format(str(e)))
                    main_logger.error("Traceback: {}".format(traceback.format_exc()))
        elif status == "skipped":
            host_name = "Skipped"

        env = {"host": host_name, "os": os_name, "gpu": gpu_name}

        env_label = "{}-{}".format(os_label, gpu_label)
        ums_client_prod = create_ums_client("PROD", env_label)
        ums_client_dev = create_ums_client("DEV", env_label)

        if ums_client_prod:
            ums_client_prod.define_environment(env)
        if ums_client_dev:
            ums_client_dev.define_environment(env)
    except Exception as e:
        main_logger.error("Failed to prepare UMS clients. Exception: {}".format(str(e)))
        main_logger.error("Traceback: {}".format(traceback.format_exc()))
    return ums_client_prod, ums_client_dev, env


def send_stubs(gpu_os_name, suite_name, cases_names, status, node_retry_info):

    ums_client_prod, ums_client_dev, env = prepare_ums_clients(gpu_os_name, suite_name, status, node_retry_info)

    cases = generate_stubs(cases_names, status)
    try:
        if ums_client_prod:
            ums_client_prod.get_suite_id_by_name(suite_name)
            send_try = 0
            while send_try < MAX_UMS_SEND_RETRIES:
                response_prod = ums_client_prod.send_test_suite(res=cases, env=env)
                main_logger.info('Test suite results sent to UMS PROD with code {} (try #{})'.format(response_prod.status_code, send_try))
                main_logger.info('Response from UMS PROD: \n{}'.format(response_prod.content))
                if response_prod and response_prod.status_code < 300:
                    response_data = json.loads(response_prod.content.decode("utf-8"))
                    if 'data' in response_data and 'test_suite_result_id' in response_data['data']:
                        test_suite_result_id_prod = response_data['data']['test_suite_result_id']
                    break
                send_try += 1
                time.sleep(UMS_SEND_RETRY_INTERVAL)
    except Exception as e:
        main_logger.error("Failed to send stubs to UMS PROD. Exception: {}".format(str(e)))
        main_logger.error("Traceback: {}".format(traceback.format_exc()))

    try:
        if ums_client_dev:
            ums_client_dev.get_suite_id_by_name(suite_name)
            send_try = 0
            while send_try < MAX_UMS_SEND_RETRIES:
                response_dev = ums_client_dev.send_test_suite(res=cases, env=env)
                main_logger.info('Test suite results sent to UMS DEV with code {} (try #{})'.format(response_dev.status_code, send_try))
                main_logger.info('Response from UMS DEV: \n{}'.format(response_dev.content))
                if response_dev and response_dev.status_code < 300:
                    response_data = json.loads(response_dev.content.decode("utf-8"))
                    if 'data' in response_data and 'test_suite_result_id' in response_data['data']:
                        test_suite_result_id_dev = response_data['data']['test_suite_result_id']
                    break
                send_try += 1
                time.sleep(UMS_SEND_RETRY_INTERVAL)
    except Exception as e:
        main_logger.error("Failed to send stubs to UMS DEV. Exception: {}".format(str(e)))
        main_logger.error("Traceback: {}".format(traceback.format_exc()))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--path_to_skipped_cases", required=True, type=str, metavar="<path>", help="path to json with skipped cases")
    parser.add_argument("--path_to_error_cases", required=True, type=str, metavar="<path>", help="path to json with error cases")
    parser.add_argument("--path_to_retry_info", required=True, type=str, metavar="<path>",help="path to info about retries")

    args = parser.parse_args()

    data_summary = []
    node_retry_info = []

    try:
        if os.path.exists(os.path.join(args.path_to_retry_info)):
            with open(os.path.join(args.path_to_retry_info), "r") as file:
                node_retry_info = json.load(file)            
    except Exception as e:
        main_logger.error("Failed to read retry info. Exception: {}".format(str(e)))
        main_logger.error("Traceback: {}".format(traceback.format_exc()))

    try:
        if args.path_to_skipped_cases:
            with open(args.path_to_skipped_cases, "r") as file:
                skipped_cases_data = json.load(file)
                data_summary.append({'status': 'skipped', 'data': skipped_cases_data})
    except Exception as e:
        main_logger.error("Failed to read list of skipped cases. Exception: {}".format(str(e)))
        main_logger.error("Traceback: {}".format(traceback.format_exc()))
    try:
        if args.path_to_error_cases:
            with open(args.path_to_error_cases, "r") as file:
                error_cases_data = json.load(file)
                data_summary.append({'status': 'error', 'data': error_cases_data})
    except Exception as e:
        main_logger.error("Failed to read list of error cases. Exception: {}".format(str(e)))
        main_logger.error("Traceback: {}".format(traceback.format_exc()))

    for data in data_summary:
        for gpu_os_name in data['data']:
            for suite_name in data['data'][gpu_os_name]:
                send_stubs(gpu_os_name, suite_name, data['data'][gpu_os_name][suite_name], data['status'], node_retry_info)
