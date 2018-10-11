import os
import jinja2
import json
import base64
import shutil
import datetime
import operator
from PIL import Image
from core.config import *
from core.auto_dict import AutoDict


def save_json_report(report, session_dir, file_name, replace_pathsep=False):
    with open(os.path.abspath(os.path.join(session_dir, file_name)), "w") as file:
        if replace_pathsep:
            s = json.dumps(report, indent=2, sort_keys=True)
            file.write(s.replace(os.path.sep, '/'))
        else:
            json.dump(report, file, indent=2, sort_keys=True)


def save_html_report(report, session_dir, file_name, replace_pathsep=False):
    with open(os.path.abspath(os.path.join(session_dir, file_name)), "w") as file:
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
                            main_logger.error('Error in base64 encoding: {}'.format(str(err)))

    return report


def env_override(value, key):
    return os.getenv(key, value)


def generate_thumbnails(session_dir):
    current_test_report = []
    # TODO: don't generate thumbnails if test failed ?
    main_logger.info("Start thumbnails creation")

    for path, dirs, files in os.walk(session_dir):
        for json_report in files:
            if json_report == TEST_REPORT_NAME_COMPARED:
                with open(os.path.join(path, json_report), 'r') as file:
                    current_test_report = json.loads(file.read())

                for test in current_test_report:
                    for img_key in POSSIBLE_JSON_IMG_KEYS:
                        if img_key in test.keys():
                            # create thumbnails
                            # TODO: check if thumb already exists in baseline folder
                            try:
                                cur_img_path = os.path.abspath(os.path.join(path, test[img_key]))
                                cur_img = Image.open(cur_img_path)
                                thumb64 = cur_img.resize((64, 64), Image.ANTIALIAS)
                                thumb256 = cur_img.resize((256, 256), Image.ANTIALIAS)

                                thumb64_path = os.path.abspath(os.path.join(path, test[img_key].replace(test['test_case'], 'thumb64_' + test['test_case'])))
                                thumb256_path = os.path.abspath(os.path.join(path, test[img_key].replace(test['test_case'], 'thumb256_' + test['test_case'])))

                                thumb64.save(thumb64_path)
                                thumb256.save(thumb256_path)
                            except Exception as err:
                                main_logger.error("Thumbnail didn't created: {}".format(str(err)))
                            else:
                                test.update({'thumb64_' + img_key: os.path.relpath(thumb64_path, path)})
                                test.update({'thumb256_' + img_key: os.path.relpath(thumb256_path, path)})

                with open(os.path.join(path, TEST_REPORT_NAME_COMPARED), 'w') as file:
                    json.dump(current_test_report, file, indent=" ")
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
                main_logger.error("Expected 'report_compare.json' not found: {}".format(str(err)))
                report['results'][result][item].update({'render_results': {}})
                report['results'][result][item].update({'render_duration': -0.0})
            else:
                render_duration = 0.0
                try:
                    for jtem in current_test_report:
                        for img in POSSIBLE_JSON_IMG_KEYS + POSSIBLE_JSON_IMG_KEYS_THUMBNAIL:
                            if img in jtem.keys():
                                # update paths
                                cur_img_path = os.path.abspath(os.path.join(session_dir, report['results'][result][item]['result_path'], jtem[img]))

                                jtem.update({img: os.path.relpath(cur_img_path, session_dir)})

                        render_duration += jtem['render_time']
                        if jtem['test_status'] == 'undefined':
                            report['results'][result][item]['total'] += 1
                        else:
                            report['results'][result][item][jtem['test_status']] += 1

                        # TODO: set machine_info once only
                        try:
                            report['machine_info'].update({'render_device': jtem['render_device']})
                            report['machine_info'].update({'tool': jtem['tool']})
                            report['machine_info'].update({'render_version': jtem['render_version']})
                            report['machine_info'].update({'core_version': jtem['core_version']})
                        except Exception as err:
                            main_logger.warning(str(err))

                    report['results'][result][item]['total'] += report['results'][result][item]['passed'] + \
                                                               report['results'][result][item]['failed'] + \
                                                               report['results'][result][item]['skipped'] + \
                                                               report['results'][result][item]['error']
                    # unite launcher report and render report
                except Exception as err:
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

    save_json_report(report, session_dir, SESSION_REPORT, replace_pathsep=True)

    return report


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
                    basename = temp_report['machine_info']['render_device'] + ' ' + temp_report['machine_info']['os']

                    # update relative paths
                    try:
                        for test_package in temp_report['results']:
                            for test_conf in temp_report['results'][test_package]:
                                temp_report['results'][test_package][test_conf].update({'machine_info': temp_report['machine_info']})

                                if common_info:
                                    for key in common_info:
                                        if not temp_report['machine_info'][key] in common_info[key]:
                                            common_info[key].append(temp_report['machine_info'][key])
                                else:
                                    common_info.update(
                                        {'reporting_date': [temp_report['machine_info']['reporting_date']],
                                         'render_version': [temp_report['machine_info']['render_version']],
                                         'core_version': [temp_report['machine_info']['core_version']]
                                         })

                                for jtem in temp_report['results'][test_package][test_conf]['render_results']:
                                    for img in POSSIBLE_JSON_IMG_KEYS + POSSIBLE_JSON_IMG_KEYS_THUMBNAIL:
                                        if img in jtem.keys():
                                            jtem.update({img: os.path.relpath(os.path.join(work_dir, basepath, jtem[img]), work_dir)})
                                temp_report['results'][test_package][test_conf].update(
                                    {'result_path': os.path.relpath(os.path.join(work_dir, basepath, temp_report['results'][test_package][test_conf]['result_path']), work_dir)}
                                )
                    except Exception as err:
                        main_logger.error(str(err))

                    if basename in summary_report.keys():
                        summary_report[basename]['results'].update(temp_report['results'])
                        for key in temp_report['summary'].keys():
                            summary_report[basename]['summary'][key] += temp_report['summary'][key]
                    else:
                        summary_report[basename] = {}
                        summary_report[basename].update({'results': temp_report['results']})
                        summary_report[basename].update({'summary': temp_report['summary']})

    for key in common_info:
        common_info[key] = ', '.join(common_info[key])

    return summary_report, common_info


def build_performance_report(work_dir):

    performance_report = AutoDict()
    performance_report_detail = AutoDict()
    hardware = {}
    summary_info_for_report = {}
    for path, dirs, files in os.walk(os.path.abspath(work_dir)):
        for file in files:
            if file.endswith(SESSION_REPORT):
                with open(os.path.join(path, file), 'r') as report_file:
                    temp_report = json.loads(report_file.read())

                hw = temp_report['machine_info']['render_device']
                if hw not in hardware:
                    hardware[hw] = temp_report['summary']['render_duration']
                tool = temp_report['machine_info']['tool']

                results = temp_report.pop('results', None)
                info = temp_report
                for test_package in results:
                    for test_config in results[test_package]:
                        results[test_package][test_config].pop('render_results', None)

                performance_report[tool].update({hw: info})

                for test_package in results:
                    for test_config in results[test_package]:
                        performance_report_detail[tool][test_package][test_config].update({hw: results[test_package][test_config]})

                tmp = sorted(hardware.items(), key=operator.itemgetter(1))
                summary_info_for_report[tool] = tmp
    hardware = sorted(hardware.items(), key=operator.itemgetter(1))
    return performance_report, hardware, performance_report_detail, summary_info_for_report


def build_compare_report(work_dir):
    compare_report = AutoDict()
    hardware = []
    for path, dirs, files in os.walk(os.path.abspath(work_dir)):
        for file in files:
            if file == SESSION_REPORT:
                with open(os.path.join(path, file), 'r') as report_file:
                    temp_report = json.loads(report_file.read())

                # force add gpu from baseline
                hw = temp_report['machine_info']['render_device']
                hw_bsln = temp_report['machine_info']['render_device'] + "[Baseline"
                hardware.append(hw)
                hardware.append(hw_bsln)

                # collect images links
                for test_package in temp_report['results']:
                    for test_config in temp_report['results'][test_package]:
                        for item in temp_report['results'][test_package][test_config]['render_results']:
                            # if test is processing first time
                            if not compare_report[item['test_case']]:
                                compare_report[item['test_case']] = {}
                            try:
                                compare_report[item['test_case']].update({hw: os.path.relpath(os.path.join(path, item['thumb256_render_color_path']), work_dir)})
                                compare_report[item['test_case']].update({hw_bsln: os.path.relpath(os.path.join(path, item['thumb256_baseline_color_path']), work_dir)})
                            except KeyError as err:
                                # TODO: fix
                                try:
                                    compare_report[item['test_case']].update({hw: os.path.relpath(os.path.join(path, item['render_color_path']), work_dir)})
                                    compare_report[item['test_case']].update({hw_bsln: os.path.relpath(os.path.join(path, item['baseline_color_path']), work_dir)})
                                except:
                                    pass

    return compare_report, hardware


def build_local_reports(work_dir, summary_report, common_info):
    work_dir = os.path.abspath(work_dir)

    env = jinja2.Environment(
        loader=jinja2.PackageLoader('core.reportExporter', 'templates'),
        autoescape=True
    )
    template = env.get_template('local_template.html')
    report_dir = ""

    for execution in summary_report:
        for test in summary_report[execution]['results']:
            for config in summary_report[execution]['results'][test]:
                report_dir = summary_report[execution]['results'][test][config]['result_path']

                # TODO: refactor it
                baseline_report_path = os.path.abspath(os.path.join(work_dir, execution, 'Baseline', test, BASELINE_REPORT_NAME))
                baseline_report = []
                render_report = []

                if os.path.exists(os.path.join(work_dir, report_dir, TEST_REPORT_NAME_COMPARED)):
                    with open(os.path.join(work_dir, report_dir, TEST_REPORT_NAME_COMPARED), 'r') as file:
                        render_report = json.loads(file.read())
                        common_info.update({'tool': render_report[0]['tool']})
                        common_info.update({'render_device': render_report[0]['render_device']})
                        common_info.update({'testing_start': render_report[0]['date_time']})
                        common_info.update({'test_group': render_report[0]['test_group']})

                if os.path.exists(baseline_report_path):
                    with open(baseline_report_path, 'r') as file:
                        baseline_report = json.loads(file.read())
                        for render_item in render_report:
                            try:
                                baseline_item = list(filter(lambda item: item['test_case'] == render_item['test_case'], baseline_report))[0]
                                render_item.update({'baseline_render_time': baseline_item['render_time']})
                            except IndexError:
                                pass

                try:
                    html = template.render(title=test,
                                           common_info=common_info,
                                           render_report=render_report,
                                           pre_path=os.path.relpath(work_dir, os.path.join(work_dir, report_dir)))
                    save_html_report(html, os.path.join(work_dir, report_dir), 'report.html', replace_pathsep=True)
                except Exception as err:
                    print(str(err))
                    main_logger.error(str(err))


def build_summary_reports(work_dir, major_title, commit_sha='undefiend', branch_name='undefined', commit_message='undefined'):

    try:
        shutil.copytree(os.path.join(os.path.split(__file__)[0], REPORT_RESOURCES_PATH),
                        os.path.join(work_dir, 'report_resources'))
    except Exception as err:
        main_logger.error("Failed to copy report resources: {}".format(str(err)))

    env = jinja2.Environment(
        loader=jinja2.PackageLoader('core.reportExporter', 'templates'),
        autoescape=True
    )
    env.filters['env_override'] = env_override

    common_info = {}
    summary_report = None

    try:
        summary_template = env.get_template('summary_template.html')
        detailed_summary_template = env.get_template('detailed_summary_template.html')

        summary_report, common_info = build_summary_report(work_dir)
        common_info.update({'commit_sha': commit_sha})
        common_info.update({'branch_name': branch_name})
        common_info.update({'commit_message': commit_message})
        save_json_report(summary_report, work_dir, SUMMARY_REPORT, replace_pathsep=True)
        summary_html = summary_template.render(title=major_title + " Summary",
                                               report=summary_report,
                                               pageID="summaryA",
                                               PIX_DIFF_MAX=PIX_DIFF_MAX,
                                               common_info=common_info)

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
        summary_html = "Error while building summary report: {}".format(str(err))
        main_logger.error(summary_html)
        save_html_report("Error while building summary report: {}".format(str(err)), work_dir, SUMMARY_REPORT_HTML,
                         replace_pathsep=True)

    try:
        performance_template = env.get_template('performance_template.html')
        performance_report, hardware, performance_report_detail, summary_info_for_report = build_performance_report(work_dir)
        save_json_report(performance_report, work_dir, PERFORMANCE_REPORT, replace_pathsep=True)
        save_json_report(performance_report_detail, work_dir, 'perf.json', replace_pathsep=True)
        performance_html = performance_template.render(title=major_title + " Performance",
                                                       performance_report=performance_report,
                                                       hardware=hardware,
                                                       performance_report_detail=performance_report_detail,
                                                       pageID="performanceA",
                                                       common_info=common_info, test_info=summary_info_for_report)
        save_html_report(performance_html, work_dir, PERFORMANCE_REPORT_HTML, replace_pathsep=True)
    except Exception as err:
        performance_html = "Error while building performance report: {}".format(str(err))
        main_logger.error(performance_html)
        save_html_report(performance_html, work_dir, PERFORMANCE_REPORT_HTML, replace_pathsep=True)

    try:
        compare_template = env.get_template('compare_template.html')
        compare_report, hardware = build_compare_report(work_dir)
        save_json_report(compare_report, work_dir, COMPARE_REPORT, True)
        compare_html = compare_template.render(title=major_title + " Compare",
                                               hardware=hardware,
                                               compare_report=compare_report,
                                               pageID="compareA",
                                               common_info=common_info)
        save_html_report(compare_html, work_dir, COMPARE_REPORT_HTML, replace_pathsep=True)
    except Exception as err:
        compare_html = "Error while building compare report: {}".format(str(err))
        main_logger.error(compare_html)
        save_html_report(compare_html, work_dir, "compare_report.html", replace_pathsep=True)

    build_local_reports(work_dir, summary_report, common_info)
