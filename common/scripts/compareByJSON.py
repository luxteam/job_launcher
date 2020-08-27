import sys
import argparse
import os
import json
from shutil import copyfile
from CompareMetrics import CompareMetrics
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
import core.config
import core.performance_counter as perf_count

try:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(
        __file__), os.path.pardir, os.path.pardir, os.path.pardir)))
    from local_config import *
except ImportError:
    core.config.main_logger.critical(
        "local config file not found. Default values will be used.")
    core.config.main_logger.critical(
        "Correct report building isn't guaranteed")
    from core.defaults_local_config import *


def get_diff(current, previous):
    if current == previous:
        return 0.0
    try:
        return (current - previous) / previous * 100.0
    except ZeroDivisionError:
        return 0


def get_pixel_difference(work_dir, base_dir, img, tolerance, pix_diff_max):
    if 'render_color_path' in img.keys():
        path_to_baseline_json = os.path.join(
            base_dir, img['test_group'], img['test_case'] + core.config.CASE_REPORT_SUFFIX)
        if os.path.exists(path_to_baseline_json):
            with open(path_to_baseline_json) as f:
                baseline_json = json.load(f)
        else:
            core.config.main_logger.error(
                'Error while read {}'.format(path_to_baseline_json))
            return img
        baseline_img_path = os.path.join(
            base_dir, img['test_group'], baseline_json['render_color_path'])
        if img.get('testcase_timeout_exceeded', False):
            img['message'].append('Testcase timeout exceeded')
        elif img.get('group_timeout_exceeded', False):
            img['message'].append('Test group timeout exceeded')
        # if baseline image not found - return
        if not os.path.exists(baseline_img_path):
            core.config.main_logger.warning(
                "Baseline image not found by path: {}".format(baseline_img_path))
            img.update({'baseline_color_path': os.path.relpath(
                os.path.join(base_dir, 'baseline.png'), work_dir)})
            img['message'].append('Baseline not found')
            if img['test_status'] != core.config.TEST_CRASH_STATUS:
                img.update({'test_status': core.config.TEST_DIFF_STATUS})
            return img

        # else add baseline images paths to json
        img.update({'baseline_color_path': os.path.relpath(
            baseline_img_path, work_dir)})
        for thumb in core.config.THUMBNAIL_PREFIXES:
            if thumb + 'render_color_path' and os.path.exists(os.path.join(base_dir, img['test_group'], baseline_json.get(thumb + 'render_color_path', None))):
                img.update({thumb + 'baseline_color_path': os.path.relpath(os.path.join(
                    base_dir, img['test_group'], baseline_json[thumb + 'render_color_path']), work_dir)})
            else:
                core.main_logger.warning("Can't find {}".format(os.path.join(base_dir, img['test_group'], thumb + baseline_json['render_color_path'])))

        # for crushed and non-executed cases only set baseline img src
        if img['test_status'] != core.config.TEST_SUCCESS_STATUS:
            return img

        render_img_path = os.path.join(work_dir, img['render_color_path'])
        if not os.path.exists(render_img_path):
            core.config.main_logger.error(
                "Rendered image not found by path: {}".format(render_img_path))
            for possible_extension in core.config.POSSIBLE_BASELINE_EXTENSIONS:
                if os.path.exists(os.path.join(work_dir, "Color", core.config.TEST_CRASH_STATUS + "." + possible_extension)):
                    img['render_color_path'] = os.path.join(
                        "Color", core.config.TEST_CRASH_STATUS + "." + possible_extension)
                    break
            img['message'].append('Rendered image not found')
            img['test_status'] = core.config.TEST_CRASH_STATUS
            return img

        if core.config.DONT_COMPARE not in img.get('script_info', ''):
            metrics = None
            try:
                metrics = CompareMetrics(render_img_path, baseline_img_path)
            except (FileNotFoundError, OSError) as err:
                core.config.main_logger.error(
                    "Error during metrics calculation: {}".format(str(err)))
                return img

            # pix_difference = metrics.getDiffPixeles(tolerance=tolerance)
            # img.update({'difference_color': pix_difference})
            pix_difference_2 = metrics.getPrediction()
            img.update({'difference_color_2': pix_difference_2})
            # if type(pix_difference) is str or pix_difference > float(pix_diff_max):
            if pix_difference_2 != 0 and img['test_status'] != core.config.TEST_CRASH_STATUS:
                img['message'].append('Unacceptable pixel difference')
                img['test_status'] = core.config.TEST_DIFF_STATUS

    return img


def get_rendertime_difference(base_dir, img, time_diff_max):
    render_time = img['render_time']
    path_to_baseline_json = os.path.join(
        base_dir, img['test_group'], img['test_case'] + core.config.CASE_REPORT_SUFFIX)
    if os.path.exists(path_to_baseline_json):
        with open(path_to_baseline_json) as f:
            baseline_json = json.load(f)
        try:
            baseline_time = baseline_json['render_time']
        except IndexError:
            baseline_time = -0.0

        time_diff = render_time - baseline_time

        for threshold in time_diff_max:
            if baseline_time < float(threshold) and time_diff > time_diff_max[threshold]:
                img.update({'time_diff_status': core.config.TEST_DIFF_STATUS})
                if img['test_status'] != core.config.TEST_CRASH_STATUS:
                    img['message'].append('Unacceptable time difference')
                    img.update({'test_status': core.config.TEST_DIFF_STATUS})

        img.update({'difference_time': time_diff})
        img.update({'baseline_render_time': baseline_time})
    else:
        core.config.main_logger.error(
            'Error while read {}'.format(path_to_baseline_json))
        img.update({'difference_time': -0.0})
        img.update({'baseline_render_time': -0.0})

    return img


def check_vram_difference(img, baseline_item, vram_diff_max):
    try:
        img.update(
            {'baseline_gpu_memory_usage': baseline_item['gpu_memory_usage']})
    except KeyError:
        core.config.main_logger.error()
    else:
        img.update({'difference_vram': get_diff(
            img['gpu_memory_usage'], baseline_item['gpu_memory_usage'])})
        # TODO: compare diff with vram_diff_max
    return img


def check_ram_difference(img, baseline_item, ram_diff_max):
    try:
        img.update(
            {'baseline_system_memory_usage': baseline_item['system_memory_usage']})
    except KeyError:
        core.config.main_logger.error()
    else:
        img.update({'difference_ram': get_diff(
            img['system_memory_usage'], baseline_item['system_memory_usage'])})
        # TODO: compare diff with ram_diff_max
    return img


def createArgParser():
    argparser = argparse.ArgumentParser()
    argparser.add_argument('--work_dir')
    argparser.add_argument('--base_dir')
    argparser.add_argument('--case_suffix', default='')
    argparser.add_argument(
        '--pix_diff_tolerance', required=False, default=core.config.PIX_DIFF_TOLERANCE)
    if report_type == 'ec':
        argparser.add_argument(
            '--pix_diff_max', required=False, default=core.config.PIX_DIFF_MAX_EC)
    else:
        argparser.add_argument(
            '--pix_diff_max', required=False, default=core.config.PIX_DIFF_MAX)
    argparser.add_argument('--time_diff_max', required=False,
                           default=core.config.TIME_DIFF_TOLERANCE)
    if report_type == 'ec':
        argparser.add_argument(
            '--vram_diff_max', required=False, default=core.config.VRAM_DIFF_MAX)
    return argparser


def main(args):
    perf_count.event_record(args.work_dir, 'Compare', True)
    render_json_path = os.path.join(
        args.work_dir, core.config.TEST_REPORT_NAME)

    if not os.path.exists(render_json_path):
        core.config.main_logger.error("Render report doesn't exists")
        perf_count.event_record(args.work_dir, 'Compare', False)
        return

    if not os.path.exists(args.base_dir):
        core.config.main_logger.error(
            "Baseline folder doesn't exist. It will be created with baseline stub img.")
        os.makedirs(args.base_dir)

    try:
        if not os.path.exists(os.path.join(args.base_dir, 'baseline.png')):
            copyfile(os.path.join(os.path.dirname(__file__), os.path.pardir, 'img', 'baseline.png'),
                     os.path.join(args.base_dir, 'baseline.png'))
    except (OSError, FileNotFoundError) as err:
        core.config.main_logger.error(
            "Couldn't copy baseline stub: {}".format(str(err)))

    # create report_compared.json before calculation to provide stability
    try:
        with open(render_json_path, 'r') as file:
            render_json = json.loads(file.read())
            for img in render_json:
                img.update({'baseline_render_time': -0.0,
                            'difference_time': -0.0,
                            'baseline_color_path': os.path.relpath(os.path.join(args.base_dir, 'baseline.png'), args.work_dir)})
    except (FileNotFoundError, OSError) as err:
        core.config.main_logger.error(
            "Can't read report.json: {}".format(str(err)))
    except json.JSONDecodeError as e:
        core.config.main_logger.error("Broken report: {}".format(str(e)))
    else:
        with open(os.path.join(args.work_dir, core.config.TEST_REPORT_NAME_COMPARED), 'w') as file:
            json.dump(render_json, file, indent=4)

    if not os.path.exists(args.base_dir):
        core.config.main_logger.warning(
            "Baseline directory not found by path: {}".format(args.base_dir))
        for img in render_json:
            if img['test_status'] != core.config.TEST_CRASH_STATUS:
                img.update({'test_status': core.config.TEST_DIFF_STATUS})
        with open(os.path.join(args.work_dir, core.config.TEST_REPORT_NAME_COMPARED), 'w') as file:
            json.dump(render_json, file, indent=4)
        perf_count.event_record(args.work_dir, 'Compare', False)
        exit(1)

    try:
        with open(render_json_path, 'r') as file:
            render_json = json.loads(file.read())

    except (FileNotFoundError, OSError, json.JSONDecodeError) as err:
        core.config.main_logger.error(
            "Can't get input data: {}".format(str(err)))

    core.config.main_logger.info("Began metrics calculation")
    for img in render_json:
        img.update(get_pixel_difference(args.work_dir, args.base_dir, img, args.pix_diff_tolerance,
                                        args.pix_diff_max))
        img.update(get_rendertime_difference(
            args.base_dir, img, args.time_diff_max))

        if args.vram_diff_max:
            path_to_baseline_json = os.path.join(
                args.base_dir, img['test_group'], img['test_case'] + core.config.CASE_REPORT_SUFFIX)
            if os.path.exists(path_to_baseline_json):
                with open(path_to_baseline_json) as f:
                    baseline_item = json.load(f)
                    check_vram_difference(img, baseline_item, args.vram_diff_max)
                    check_ram_difference(img, baseline_item, args.vram_diff_max)

        if args.case_suffix:
            or_baseline_json_path = os.path.join(
                args.base_dir, img['test_case'] + args.case_suffix)
            if not os.path.exists(or_baseline_json_path):
                core.config.main_logger.error(
                    "Test case {} original render report not found".format(img['test_case']))
            else:
                with open(or_baseline_json_path, 'r') as file:
                    original_json = json.loads(file.read())
                if len(original_json) <= 0:
                    core.config.main_logger.error(
                        "{} case OR json is empty".format(img['test_case']))
                else:
                    for key in ['original_color_path', 'original_render_log']:
                        try:
                            original_path = original_json[0][key]
                            img.update({key: os.path.relpath(os.path.join(args.base_dir, original_path),
                                                             args.work_dir)})
                        except KeyError:
                            core.config.main_logger.error(
                                "{} case OR json is incomplete".format(img['test_case']))

                        try:
                            original_render_time = original_json[0]['render_time']
                            img.update(
                                {'or_render_time': original_render_time})
                            img.update({'difference_time_or': get_diff(
                                img['render_time'], original_render_time)})
                        except KeyError:
                            core.config.main_logger.error(
                                "{} case OR json is incomplete".format(img['test_case']))

    with open(os.path.join(args.work_dir, core.config.TEST_REPORT_NAME_COMPARED), 'w') as file:
        json.dump(render_json, file, indent=4)

    perf_count.event_record(args.work_dir, 'Compare', False)


if __name__ == '__main__':
    args = createArgParser().parse_args()
    main(args)
