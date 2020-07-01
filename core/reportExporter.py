import os
import subprocess
import jinja2
import json
import base64
from shutil import rmtree, copytree
from codecs import open
import datetime
import operator
from PIL import Image
import core.config as config
from core.config import *
from core.auto_dict import AutoDict
import copy
import sys
import traceback
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir, os.path.pardir)))

try:
    from local_config import *
except ImportError:
    main_logger.critical("local config file not found. Default values will be used.")
    main_logger.critical("Correct report building isn't guaranteed")
    from core.defaults_local_config import *


def save_json_report(report, session_dir, file_name, replace_pathsep=False):
    with open(os.path.abspath(os.path.join(session_dir, file_name)), "w", encoding='utf8') as file:
        if replace_pathsep:
            s = json.dumps(report, indent=4, sort_keys=True)
            file.write(s.replace(os.path.sep, '/'))
        else:
            json.dump(report, file, indent=4, sort_keys=True)


def save_html_report(report, session_dir, file_name, replace_pathsep=False):
    with open(os.path.abspath(os.path.join(session_dir, file_name)), "w", encoding='utf8') as file:
        if replace_pathsep:
            file.write(report.replace(os.path.sep, '/'))
        else:
            file.write(report)


def make_base64_img(session_dir, report):
    os.mkdir(os.path.join(session_dir, 'tmp'))

    for test_package in report['results']:
        for test_conf in report['results'][test_package]:
            for test_execution in report['results'][test_package][test_conf]['render_results']:

                for img in POSSIBLE_JSON_IMG_KEYS:
                    if img in test_execution:
                        try:
                            if not os.path.exists(os.path.abspath(test_execution[img])):
                                test_execution[img] = os.path.join(session_dir, test_execution[img])

                            cur_img = Image.open(os.path.abspath(test_execution[img]))
                            tmp_img = cur_img.resize((64, 64), Image.ANTIALIAS)
                            tmp_img.save(os.path.join(session_dir, 'tmp', 'img.jpg'))

                            with open(os.path.join(session_dir, 'tmp', 'img.jpg'), 'rb') as file:
                                code = base64.b64encode(file.read())

                            src = "data:image/jpeg;base64," + str(code)[2:-1]
                            test_execution.update({img: src})
                        except Exception as err:
                            traceback.print_exc()
                            main_logger.error('Error in base64 encoding: {}'.format(str(err)))

    return report


def env_override(value, key):
    return os.getenv(key, value)


def get_jobs_launcher_version(value):
    return subprocess.check_output("git describe --tags --always", shell=True).decode("utf-8")


def generate_thumbnails(session_dir):
    current_test_report = []
    main_logger.info("Start thumbnails creation")

    for path, dirs, files in os.walk(session_dir):
        for json_report in files:
            if json_report == TEST_REPORT_NAME_COMPARED:
                with open(os.path.join(path, json_report), 'r') as file:
                    current_test_report = json.loads(file.read())

                for test in current_test_report:
                    for img_key in POSSIBLE_JSON_IMG_KEYS:
                        if img_key in test.keys():
                            try:
                                cur_img_path = os.path.abspath(os.path.join(path, test[img_key]))
                                thumb64_path = os.path.abspath(
                                    os.path.join(path, test[img_key].replace(test['test_case'],
                                                                             'thumb64_' + test['test_case'])))
                                thumb256_path = os.path.abspath(
                                    os.path.join(path, test[img_key].replace(test['test_case'],
                                                                             'thumb256_' + test['test_case'])))

                                if os.path.exists(thumb64_path) and os.path.exists(thumb256_path):
                                    continue

                                cur_img = Image.open(cur_img_path)
                                thumb64 = cur_img.resize((64, int(64 * cur_img.size[1] / cur_img.size[0])),
                                                         Image.ANTIALIAS)
                                thumb256 = cur_img.resize((256, int(256 * cur_img.size[1] / cur_img.size[0])),
                                                          Image.ANTIALIAS)

                                thumb64.save(thumb64_path)
                                thumb256.save(thumb256_path)
                            except Exception as err:
                                print("Thumbnail didn't created: json_report - {}, test - {}, img_key - {}".format(json_report, test, img_key))
                                main_logger.error("Thumbnail didn't created: {}".format(str(err)))
                            else:
                                test.update({'thumb64_' + img_key: os.path.relpath(thumb64_path, path)})
                                test.update({'thumb256_' + img_key: os.path.relpath(thumb256_path, path)})

                with open(os.path.join(path, TEST_REPORT_NAME_COMPARED), 'w') as file:
                    json.dump(current_test_report, file, indent=4)
                    main_logger.info("Thumbnails created for: {}".format(os.path.join(path, TEST_REPORT_NAME_COMPARED)))


def build_session_report(report, session_dir):
    total = {'total': 0, 'passed': 0, 'failed': 0, 'error': 0, 'skipped': 0, 'duration': 0, 'render_duration': 0}

    generate_thumbnails(session_dir)

    current_test_report = {}
    for result in report['results']:
        for item in report['results'][result]:
            try:
                # get report_compare.json by one tests group
                with open(os.path.join(session_dir, report['results'][result][item]['result_path'], TEST_REPORT_NAME_COMPARED), 'r') as file:
                    current_test_report = json.loads(file.read())
            except Exception as err:
                print("Excepted 'report_compare.json' not found for {} {}".format(result, item))
                main_logger.error("Expected 'report_compare.json' not found: {}".format(str(err)))
                report['results'][result][item].update({'render_results': {}})
                report['results'][result][item].update({'render_duration': -0.0})
            else:
                render_duration = 0.0
                try:
                    for jtem in current_test_report:
                        for group_report_file in REPORT_FILES:
                            if group_report_file in jtem.keys():
                                # update paths
                                cur_img_path = os.path.abspath(os.path.join(session_dir, report['results'][result][item]['result_path'], jtem[group_report_file]))

                                jtem.update({group_report_file: os.path.relpath(cur_img_path, session_dir)})

                        render_duration += jtem['render_time']
                        if jtem['test_status'] == 'undefined':
                            report['results'][result][item]['total'] += 1
                        else:
                            report['results'][result][item][jtem['test_status']] += 1

                    try:
                        report['machine_info'].update({'render_device': jtem['render_device']})
                        report['machine_info'].update({'tool': jtem['tool']})
                        if report_type != 'ec':
                            report['machine_info'].update({'render_version': jtem['render_version']})
                        else:
                            report['machine_info'].update({'minor_version': jtem['minor_version']})
                        report['machine_info'].update({'core_version': jtem['core_version']})
                    except Exception as err:
                        print("Exception while updating machine_info in session_report")
                        main_logger.warning(str(err))

                    report['results'][result][item]['total'] += report['results'][result][item]['passed'] + \
                                                               report['results'][result][item]['failed'] + \
                                                               report['results'][result][item]['skipped'] + \
                                                               report['results'][result][item]['error']
                    # unite launcher report and render report
                except Exception as err:
                    traceback.print_exc()
                    main_logger.error('Exception while update render report {}'.format(str(err)))
                    render_duration = -0.0

                if current_test_report:
                    report['results'][result][item].update({'render_results': current_test_report})

                report['results'][result][item].update({'render_duration': render_duration})

    # get summary results
    for result in report['results']:
        for item in report['results'][result]:
            for key in total:
                total[key] += report['results'][result][item][key]
    report.update({'summary': total})
    report['machine_info'].update({'reporting_date': datetime.date.today().strftime('%m/%d/%Y')})

    save_json_report(report, session_dir, SESSION_REPORT)

    return report


def generate_empty_render_result(summary_report, lost_test_package, gpu_os_case, gpu_name, os_name, lost_tests_count):
    summary_report[gpu_os_case]['results'][lost_test_package] = {}
    # add empty conf
    summary_report[gpu_os_case]['results'][lost_test_package][""] = {}
    # specify data
    summary_report[gpu_os_case]['results'][lost_test_package][""]['duration'] = 0.0
    summary_report[gpu_os_case]['results'][lost_test_package][""]['error'] = lost_tests_count
    summary_report[gpu_os_case]['results'][lost_test_package][""]['failed'] = 0
    summary_report[gpu_os_case]['results'][lost_test_package][""]['machine_info'] = ""
    summary_report[gpu_os_case]['results'][lost_test_package][""]['passed'] = 0
    summary_report[gpu_os_case]['results'][lost_test_package][""]['render_duration'] = -0.0
    summary_report[gpu_os_case]['results'][lost_test_package][""]['render_results'] = []
    summary_report[gpu_os_case]['results'][lost_test_package][""]['result_path'] = ""
    summary_report[gpu_os_case]['results'][lost_test_package][""]['skipped'] = 0
    summary_report[gpu_os_case]['results'][lost_test_package][""]['total'] = lost_tests_count

    summary_report[gpu_os_case]['results'][lost_test_package][""]['recovered_info'] = {}
    summary_report[gpu_os_case]['results'][lost_test_package][""]['recovered_info']['os'] = os_name
    summary_report[gpu_os_case]['results'][lost_test_package][""]['recovered_info']['render_device'] = gpu_name

    summary_report[gpu_os_case]['summary']['error'] += lost_tests_count
    summary_report[gpu_os_case]['summary']['total'] += lost_tests_count


def build_summary_report(work_dir):
    summary_report = {}
    common_info = {}
    for path, dirs, files in os.walk(os.path.abspath(work_dir)):
        for file in files:
            # build summary report
            if file.endswith(SESSION_REPORT):
                basepath = os.path.relpath(path, work_dir)
                with open(os.path.join(path, file), 'r') as report_file:
                    temp_report = json.loads(report_file.read())
                    try:
                        basename = temp_report['machine_info']['render_device'] + ' ' + temp_report['machine_info']['os']
                    except KeyError:
                        continue

                    # update relative paths
                    try:
                        for test_package in temp_report['results']:
                            for test_conf in temp_report['results'][test_package]:
                                temp_report['results'][test_package][test_conf].update(
                                    {'machine_info': temp_report['machine_info']})

                                if common_info:
                                    for key in common_info:
                                        if not temp_report['machine_info'][key] in common_info[key]:
                                            common_info[key].append(temp_report['machine_info'][key])
                                else:
                                    common_info.update({'reporting_date': [temp_report['machine_info']['reporting_date']]})
                                    
                                    if report_type != 'ec':
                                        common_info.update({'render_version': [temp_report['machine_info']['render_version']]})
                                    else:
                                        common_info.update({'minor_version': [temp_report['machine_info']['minor_version']]})
                                    common_info.update({'core_version': [temp_report['machine_info']['core_version']]})

                                for jtem in temp_report['results'][test_package][test_conf]['render_results']:
                                    for group_report_file in REPORT_FILES:
                                        if group_report_file in jtem.keys():
                                            jtem.update({group_report_file: os.path.relpath(os.path.join(work_dir, basepath, jtem[group_report_file]), work_dir)})
                                temp_report['results'][test_package][test_conf].update(
                                    {'result_path': os.path.relpath(
                                        os.path.join(work_dir, basepath, temp_report['results'][test_package][test_conf]['result_path']),
                                        work_dir)}
                                )
                    except Exception as err:
                        traceback.print_exc()
                        main_logger.error("Processing of {} has produced error: {}".format(basepath.split(os.path.sep)[-1], str(err)))

                    if basename in summary_report.keys():
                        summary_report[basename]['results'].update(temp_report['results'])
                        for key in temp_report['summary'].keys():
                            summary_report[basename]['summary'][key] += temp_report['summary'][key]
                    else:
                        summary_report[basename] = {}
                        summary_report[basename].update({'results': temp_report['results']})
                        summary_report[basename].update({'summary': temp_report['summary']})

    for key in common_info:
        common_info[key] = ' '.join(common_info[key])

    if os.path.exists(os.path.join(work_dir, LOST_TESTS_JSON_NAME)): 
        with open(os.path.join(work_dir, LOST_TESTS_JSON_NAME), "r") as file:
            lost_tests_count = json.load(file)
        for lost_test_result in lost_tests_count:
            test_case_found = False
            gpu_name = lost_test_result.split('-')[0]
            os_name = lost_test_result.split('-')[1]
            for gpu_os_case in summary_report:
                if gpu_name.lower() in gpu_os_case.lower() and os_name.lower() in gpu_os_case.lower():
                    for lost_test_package in lost_tests_count[lost_test_result]:
                        generate_empty_render_result(summary_report, lost_test_package, gpu_os_case, gpu_name, os_name, lost_tests_count[lost_test_result][lost_test_package])
                    test_case_found = True
                    break
            # if all data for GPU + OS was lost (it can be regression.json execution)
            if not test_case_found:
                gpu_os_case = lost_test_result.replace('-', ' ')
                summary_report[gpu_os_case] = {}
                summary_report[gpu_os_case]['results'] = {}
                summary_report[gpu_os_case]['summary'] = {}
                summary_report[gpu_os_case]['summary']['duration'] = 0.0
                summary_report[gpu_os_case]['summary']['error'] = 0
                summary_report[gpu_os_case]['summary']['failed'] = 0
                summary_report[gpu_os_case]['summary']['passed'] = 0
                summary_report[gpu_os_case]['summary']['render_duration'] = -0.0
                summary_report[gpu_os_case]['summary']['skipped'] = 0
                summary_report[gpu_os_case]['summary']['total'] = 0
                for lost_test_package in lost_tests_count[lost_test_result]:
                    generate_empty_render_result(summary_report, lost_test_package, gpu_os_case, gpu_name, os_name, lost_tests_count[lost_test_result][lost_test_package])

    return summary_report, common_info


def build_performance_report(summary_report):

    performance_report = AutoDict()
    performance_report_detail = AutoDict()
    hardware = {}
    summary_info_for_report = {}

    for key in summary_report:
        platform = summary_report[key]
        group = next(iter(platform['results']))
        conf = list(platform['results'][group].keys())[0]

        if platform['results'][group][conf]['machine_info'] == "":
            # if machine info is empty it's blank data for lost test cases
            continue

        hw = platform['results'][group][conf]['machine_info']['render_device']
        if hw not in hardware:
            hardware[hw] = platform['summary']['render_duration']

        temp_report = platform['results'][group][conf]
        tool = temp_report['machine_info']['tool']

        results = platform.pop('results', None)
        info = temp_report
        for test_package in results:
            for test_config in results[test_package]:
                results[test_package][test_config].pop('render_results', None)

        performance_report[tool].update({hw: info})

        for test_package in results:
            for test_config in results[test_package]:
                performance_report_detail[tool][test_package][test_config].update(
                    {hw: results[test_package][test_config]})

        tmp = sorted(hardware.items(), key=operator.itemgetter(1))
        summary_info_for_report[tool] = tmp
    hardware = sorted(hardware.items(), key=operator.itemgetter(1))
    return performance_report, hardware, performance_report_detail, summary_info_for_report


def build_compare_report(summary_report):
    compare_report = AutoDict()
    hardware = []
    for platform in summary_report.keys():
        for test_package in summary_report[platform]['results']:
            for test_config in summary_report[platform]['results'][test_package]:
                temp_report = summary_report[platform]['results'][test_package][test_config]

                if temp_report['machine_info'] == "":
                    # if machine info is empty it's blank data for lost test cases
                    continue

                # force add gpu from baseline
                hw = temp_report['machine_info']['render_device']
                hw_bsln = temp_report['machine_info']['render_device'] + " [Baseline]"

                if hw not in hardware:
                    hardware.append(hw)
                    hardware.append(hw_bsln)

                # collect images links
                for item in temp_report['render_results']:
                    # if test is processing first time
                    if not compare_report[item['test_case']]:
                        compare_report[item['test_case']] = {}

                    try:
                        for img_key in POSSIBLE_JSON_IMG_RENDERED_KEYS + POSSIBLE_JSON_IMG_RENDERED_KEYS_THUMBNAIL:
                            if img_key in item.keys():
                                compare_report[item['test_case']].update({hw: item[img_key]})
                        for img_key in POSSIBLE_JSON_IMG_BASELINE_KEYS + POSSIBLE_JSON_IMG_BASELINE_KEYS_THUMBNAIL:
                            if img_key in item.keys():
                                compare_report[item['test_case']].update({hw_bsln: item[img_key]})
                    except KeyError as err:
                        print("Missed testcase detected: platform - {}, test_package - {}, test_config - {}, item - {}".format(platform, test_package, test_config, item))
                        main_logger.error("Missed testcase detected {}".format(str(err)))

    return compare_report, hardware


def build_local_reports(work_dir, summary_report, common_info, jinja_env):
    work_dir = os.path.abspath(work_dir)

    template = jinja_env.get_template('local_template_{}.html'.format(report_type))
    report_dir = ""

    try:
        for execution in summary_report:
            for test in summary_report[execution]['results']:
                for config in summary_report[execution]['results'][test]:
                    report_dir = summary_report[execution]['results'][test][config]['result_path']

                    render_report = []

                    if os.path.exists(os.path.join(work_dir, report_dir, TEST_REPORT_NAME_COMPARED)):
                        with open(os.path.join(work_dir, report_dir, TEST_REPORT_NAME_COMPARED), 'r') as file:
                            render_report = json.loads(file.read())
                            keys_for_upd = ['tool', 'render_device', 'testing_start', 'test_group']
                            for key_upd in keys_for_upd:
                                if key_upd in render_report[0].keys():
                                    common_info.update({key_upd: render_report[0][key_upd]})
                    else:
                    	# test case was lost
                    	continue

                    # for core baseline_render_time initialize via compareByJson script
                    if report_type != 'ec':
                        baseline_report_path = os.path.abspath(os.path.join(work_dir, execution, 'Baseline', test, BASELINE_REPORT_NAME))
                        baseline_report = []

                        if os.path.exists(baseline_report_path):
                            with open(baseline_report_path, 'r') as file:
                                baseline_report = json.loads(file.read())
                                for render_item in render_report:
                                    try:
                                        baseline_item = list(filter(lambda item: item['test_case'] == render_item['test_case'], baseline_report))[0]
                                        render_item.update({'baseline_render_time': baseline_item['render_time']})
                                    except IndexError:
                                        pass

                    # choose right plugin version based on building report type
                    if report_type != 'ec':
                        version_in_title = common_info['render_version']
                    else:
                        version_in_title = common_info['core_version']
                    html = template.render(title="{} {} plugin version: {}".format(common_info['tool'], test, version_in_title),
                                           common_info=common_info,
                                           render_report=render_report,
                                           pre_path=os.path.relpath(work_dir, os.path.join(work_dir, report_dir)))
                    save_html_report(html, os.path.join(work_dir, report_dir), 'report.html', replace_pathsep=True)
    except Exception as err:
        traceback.print_exc()
        main_logger.error(str(err))


# commit_message should be last arg because of eof in the end of commit message
def build_summary_reports(work_dir, major_title, commit_sha='undefined', branch_name='undefined', node_retry_info='', commit_message='undefined'):
    if os.path.exists(os.path.join(work_dir, 'report_resources')):
        rmtree(os.path.join(work_dir, 'report_resources'), True)

    try:
        copytree(os.path.join(os.path.split(__file__)[0], REPORT_RESOURCES_PATH),
                 os.path.join(work_dir, 'report_resources'))
    except Exception as err:
        main_logger.error("Failed to copy report resources: {}".format(str(err)))

    env = jinja2.Environment(
        loader=jinja2.PackageLoader('core.reportExporter', 'templates'),
        autoescape=True
    )
    # check that original_render variable exists
    if not 'original_render' in globals():
        global original_render
        original_render = ''
    env.globals.update({'original_render': original_render,
                        'report_type': report_type,
                        'pre_path': '.',
                        'config': config})
    env.filters['env_override'] = env_override
    env.filters['get_jobs_launcher_version'] = get_jobs_launcher_version

    common_info = {}
    summary_report = None

    if node_retry_info:
        node_retry_info = json.loads(bytes(node_retry_info, "utf-8").decode("unicode_escape"))

    main_logger.info("Saving summary report...")

    try:
        summary_template = env.get_template('summary_template.html')
        detailed_summary_template = env.get_template('detailed_summary_template_{}.html'.format(report_type))

        summary_report, common_info = build_summary_report(work_dir)

        add_retry_info(summary_report, node_retry_info)

        common_info.update({'commit_sha': commit_sha})
        common_info.update({'branch_name': branch_name})
        common_info.update({'commit_message': commit_message})
        save_json_report(summary_report, work_dir, SUMMARY_REPORT)
        summary_html = summary_template.render(title=major_title + " Summary",
                                               report=summary_report,
                                               pageID="summaryA",
                                               PIX_DIFF_MAX=PIX_DIFF_MAX,
                                               common_info=common_info,
                                               node_retry_info=node_retry_info)
        save_html_report(summary_html, work_dir, SUMMARY_REPORT_HTML, replace_pathsep=True)

        for execution in summary_report.keys():
            detailed_summary_html = detailed_summary_template.render(title=major_title + " " + execution,
                                                                     report=summary_report,
                                                                     pageID="summaryA",
                                                                     PIX_DIFF_MAX=PIX_DIFF_MAX,
                                                                     common_info=common_info,
                                                                     i=execution)
            save_html_report(detailed_summary_html, work_dir, execution + "_detailed.html", replace_pathsep=True)
    except Exception as err:
        traceback.print_exc()
        main_logger.error(summary_html) #FIXME: referenced before assignment
        save_html_report("Error while building summary report: {}".format(str(err)), work_dir, SUMMARY_REPORT_HTML,
                         replace_pathsep=True)

    main_logger.info("Saving performance report...")
    try:
        copy_summary_report = copy.deepcopy(summary_report)
        performance_template = env.get_template('performance_template.html')

        performance_report, hardware, performance_report_detail, summary_info_for_report = build_performance_report(copy_summary_report)

        save_json_report(performance_report, work_dir, PERFORMANCE_REPORT)
        save_json_report(performance_report_detail, work_dir, 'performance_report_detailed.json')
        performance_html = performance_template.render(title=major_title + " Performance",
                                                       performance_report=performance_report,
                                                       hardware=hardware,
                                                       performance_report_detail=performance_report_detail,
                                                       pageID="performanceA",
                                                       common_info=common_info,
                                                       test_info=summary_info_for_report)
        save_html_report(performance_html, work_dir, PERFORMANCE_REPORT_HTML, replace_pathsep=True)
    except Exception as err:
        traceback.print_exc()
        main_logger.error(performance_html)
        save_html_report(performance_html, work_dir, PERFORMANCE_REPORT_HTML, replace_pathsep=True)

    main_logger.info("Saving compare report...")
    try:
        compare_template = env.get_template('compare_template.html')
        copy_summary_report = copy.deepcopy(summary_report)

        compare_report, hardware = build_compare_report(copy_summary_report)

        save_json_report(compare_report, work_dir, COMPARE_REPORT)
        compare_html = compare_template.render(title=major_title + " Compare",
                                               hardware=hardware,
                                               compare_report=compare_report,
                                               pageID="compareA",
                                               common_info=common_info)
        save_html_report(compare_html, work_dir, COMPARE_REPORT_HTML, replace_pathsep=True)
    except Exception as err:
        traceback.print_exc()
        main_logger.error(compare_html)
        save_html_report(compare_html, work_dir, "compare_report.html", replace_pathsep=True)

    build_local_reports(work_dir, summary_report, common_info, env)


def add_retry_info(summary_report, retry_info):
    try:
        for config in summary_report:
            for test_package in summary_report[config]['results']:
                node = summary_report[config]['results'][test_package]['']['machine_info']['host']
                for retry in retry_info:
                    for tester in retry['Testers']:
                        if str(node).upper() in tester:
                            for group in retry['Tries']:
                                if test_package in group.keys() or [g for g in group.keys() if g.endswith('.json')]:
                                    retries_list = []

                                    for retry in retry['Tries']:
                                        for group in retry.keys():
                                            if group.endswith('.json'):
                                                groupOrJson = retry[str(
                                                    next(iter(retry['Tries'][0].keys())))]
                                            else:
                                                groupOrJson = retry.get(
                                                    test_package, [])
                                        for retry in groupOrJson:
                                            retries_list.append(retry)

                                    summary_report[config]['results'][test_package]['']['machine_info']['retries'] = retries_list
    except Exception as e:
        main_logger.error(
            'Error "{}" while adding retry info'.format(str(e)))
