import os
import json
import time
import argparse
import hashlib

from image_service_client import ISClient
from ums_client import create_ums_client
from minio_client import create_mc_client
from core.config import *
import traceback

res = []
transferred_test_cases = []

main_logger.info("UMS progress monitor is running")

test_cases_sent = False
is_client = None
ums_client_prod = create_ums_client("PROD")
ums_client_dev = create_ums_client("DEV")
minio_client_prod = None
minio_client_dev = None
if ums_client_prod:
    minio_client_prod = create_mc_client(ums_client_prod.job_id)
if ums_client_dev:
    minio_client_dev = create_mc_client(ums_client_dev.job_id)
try:
    is_client = ISClient(
        url=os.getenv("IS_URL"),
        login=os.getenv("IS_LOGIN"),
        password=os.getenv("IS_PASSWORD")
    )
    main_logger.info("UMS progress monitor Image Service client created for url: {}".format(is_client.url))
except Exception as e:
    main_logger.error("UMS progress monitor can't create Image Service client for url: {}. Error: {}".format(os.getenv("IS_URL"), str(e)))


def render_color_full_path(session_dir, suite_name, render_color_path):
    return os.path.realpath(os.path.join(session_dir, suite_name, render_color_path))


def get_cases_existence_info_by_hashes(session_dir, suite_name, test_cases):
    cases_hashes_info = {}
    cases_hashes = {}
    try:
        for case in test_cases:
            try:
                with open(os.path.join(session_dir, suite_name, case + '_RPR.json')) as case_file:
                    case_file_data = json.load(case_file)[0]
                    with open(render_color_full_path(session_dir, suite_name, case_file_data['render_color_path']), 'rb') as img:
                        bytes_data = img.read()
                        cases_hashes[case] = hashlib.md5(bytes_data).hexdigest()
            except Exception as e1:
                main_logger.error("Failed to process case {} while hash check. Excetpion: {}".format(case, e1))
                main_logger.error("Traceback: {}".format(traceback.format_exc()))

        hash_info_from_is = is_client.get_existence_info_by_hash(
            [case_hash for case, case_hash in cases_hashes.items() if case_hash]
        )
        if hash_info_from_is:
            cases_hashes_info = {
                case: hash_info_from_is[case_hash]
                for case, case_hash in cases_hashes.items() if case_hash in hash_info_from_is
            }
        main_logger.info("Hashes of existing images were received from Image Service")
    except Exception as e:
        main_logger.error("Failed to get hashed from Image Service. Excetpion: {}".format(e))
        main_logger.error("Traceback: {}".format(traceback.format_exc()))
    return cases_hashes_info


def send_finished_cases(session_dir, suite_name):
    global test_cases_sent
    if os.path.exists(os.path.join(session_dir, suite_name, 'test_cases.json')):
        test_cases_path = os.path.join(session_dir, suite_name, 'test_cases.json')
        with open(test_cases_path) as test_cases_file:
            global transferred_test_cases
            test_cases = json.load(test_cases_file)
        # Blender, Maya, Core and Viewer has different case name
        if 'case' in test_cases[0]:
            name_key = 'case'
        elif 'name' in test_cases[0]:
            name_key = 'name'
        else:
            name_key = 'scene'
    else:
        # case of Max
        test_cases_path = os.path.join(session_dir, suite_name, 'test_cases.json')
        with open(test_cases_path) as test_cases_file:
            global transferred_test_cases
            test_cases = json.load(test_cases_file)['cases']
        name_key = 'name'
    new_test_cases = {}
    for test_case in test_cases:
        if test_case['status'] in ('skipped', 'error', 'failed', 'done', 'passed') and not test_case[name_key] in transferred_test_cases:
            # check that file with case info already exists
            if os.path.exists(os.path.join(session_dir, suite_name, test_case[name_key] + '_RPR.json')):
                new_test_cases[test_case[name_key]] = test_case['status']
                if 'aovs' in test_case:
                    for aov in test_case['aovs']:
                        new_test_cases[test_case[name_key] + aov['aov']] = aov['status']
            else:
                main_logger.warning("File with case info for case {} doesn't exist. Make sure that it is expected".format(test_case[name_key]))

    if new_test_cases:
        new_cases_existence_hashes_info = get_cases_existence_info_by_hashes(session_dir, suite_name, new_test_cases) if is_client else {}
        print('Got hashes info from image service:\n{}'.format(json.dumps(new_cases_existence_hashes_info, indent=2)))

    if not test_cases_sent:
        if ums_client_prod and minio_client_prod:
            ums_client_prod.get_suite_id_by_name(suite_name)
            minio_client_prod.upload_file(test_cases_path, "PROD", ums_client_prod.build_id, ums_client_prod.suite_id or "", ums_client_prod.env_label)
        if ums_client_dev and minio_client_dev:
            ums_client_dev.get_suite_id_by_name(suite_name)
            minio_client_dev.upload_file(test_cases_path, "DEV", ums_client_dev.build_id, ums_client_dev.suite_id or "", ums_client_dev.env_label)

        test_cases_sent = True

    for test_case in new_test_cases:
        try:
            print('Sending artefacts & images for: {}'.format(test_case))
            case_file_path = os.path.join(session_dir, suite_name, test_case + '_RPR.json')
            with open(case_file_path) as case_file:
                case_file_data = json.load(case_file)[0]

                if test_case in new_cases_existence_hashes_info and \
                        new_cases_existence_hashes_info[test_case] and \
                        'id' in new_cases_existence_hashes_info[test_case]:
                    image_id = new_cases_existence_hashes_info[test_case]['id']
                    print('Use id found by hash for case: {} id: {}'.format(test_case, image_id))
                else:
                    image_id = is_client.send_image(render_color_full_path(session_dir, suite_name, case_file_data[
                        'render_color_path'])) if is_client else -1
                    print('Upload new image for case: {} and get image id: {}'.format(test_case, image_id))

                # upload error screen if it exists
                if 'error_screen_path' in case_file_data and case_file_data['error_screen_path']:
                    error_screen_id = is_client.send_image(render_color_full_path(session_dir, suite_name, case_file_data[
                        'error_screen_path'])) if is_client else -1
                    print('Upload error screen for case: {} and get image id: {}'.format(test_case, error_screen_id))
                    case_file_data['error_screen_is_id'] = error_screen_id

                case_file_data['rendered_image_is_id'] = image_id

            with open(case_file_path, 'w') as case_file:
                json.dump([case_file_data], case_file, indent=4, sort_keys=True)

            transferred_test_cases.append(test_case)

        except Exception as e:
            main_logger.error("UMS progress monitor failed iteration of test case {} send.".format(test_case))
            main_logger.error("Traceback: {}".format(traceback.format_exc()))

    diff = len(test_cases) - len(transferred_test_cases)
    print('Monitor is waiting {} cases'.format(diff))
    if diff <= 0:
        return True

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--interval', required=False, default=5, type=int, help="time interval")
    parser.add_argument('--session_dir', required=True, type=str, help='session dir')
    parser.add_argument('--suite_name', required=True, type=str, help='suite name')

    args = parser.parse_args()

    check = 1
    fails_in_succession = 0
    while True:
        try:
            time.sleep(args.interval)
            print('Check number {}'.format(check))
            check += 1
            result = send_finished_cases(args.session_dir, args.suite_name)
            fails_in_succession = 0
            if result:
                main_logger.info("UMS progress monitor send all expected results.")
                break
        except Exception as e:
            fails_in_succession += 1
            main_logger.error("UMS progress monitor failed look up for new cases iteration. Sleep for {} seconds".format(args.interval))
            main_logger.error("Traceback: {}".format(traceback.format_exc()))
        if MAX_UMS_SEND_RETRIES == fails_in_succession:
            break
