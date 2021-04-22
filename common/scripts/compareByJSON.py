import sys
import argparse
import os
import json
from shutil import copyfile
from PIL import Image
import hashlib
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


def md5(file_name):
    hash_md5 = hashlib.md5()
    with open(file_name, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def get_diff(current, previous):
    if current == previous:
        return 0.0
    try:
        return (current - previous) / previous * 100.0
    except ZeroDivisionError:
        return 0


def get_pixel_difference(work_dir, base_dir, img, tolerance, pix_diff_max):
    if img.get('testcase_timeout_exceeded', False):
        img['message'].append('Testcase timeout exceeded')
    elif img.get('group_timeout_exceeded', False):
        img['message'].append('Test group timeout exceeded')

    if 'render_color_path' in img.keys():
        path_to_baseline_json = os.path.join(
            base_dir, img['test_group'], img['test_case'] + core.config.CASE_REPORT_SUFFIX)
        if os.path.exists(path_to_baseline_json):
            with open(path_to_baseline_json) as f:
                baseline_json = json.load(f)
        else:
            img.update({'baseline_color_path': os.path.relpath(
                os.path.join(base_dir, 'baseline.png'), work_dir)})
            img['message'].append('Baseline not found')
            if img['test_status'] != core.config.TEST_CRASH_STATUS:
                img.update({'test_status': core.config.TEST_DIFF_STATUS})
            core.config.main_logger.error(
                "Baseline json not found by path: {}".format(path_to_baseline_json))
            return img

        # if baseline image not found - return
        baseline_img_path = os.path.join(
            base_dir, img['test_group'], baseline_json['render_color_path'])
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
        if os.path.exists(os.path.join(base_dir, img['test_group'], baseline_json.get('render_color_path', 'Null'))):
            img.update({'baseline_color_path': os.path.relpath(os.path.join(
                base_dir, img['test_group'], baseline_json['render_color_path']), work_dir)})
        else:
            core.config.main_logger.warning("Can't find {}".format(os.path.join(base_dir, img['test_group'], baseline_json['render_color_path'])))

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

            if report_type == 'ec':
                pix_difference = metrics.getDiffPixeles(tolerance=tolerance)
                img.update({'difference_color': pix_difference})
                if type(pix_difference) is str or pix_difference > pix_diff_max:
                    img['test_status'] = core.config.TEST_DIFF_STATUS
            else:
                # if 'Black image expected' in script_info - allow black img
                mark_failed_if_black = core.config.CASE_EXPECTS_BLACK not in img.get('script_info', '')
                pix_difference_2 = metrics.getPrediction(mark_failed_if_black=mark_failed_if_black)
                img.update({'difference_color_2': pix_difference_2})
                # if type(pix_difference) is str or pix_difference > float(pix_diff_max):
                if pix_difference_2 != 0 and img['test_status'] != core.config.TEST_CRASH_STATUS:
                    img['message'].append('Unacceptable pixel difference')
                    img['test_status'] = core.config.TEST_DIFF_STATUS
                elif pix_difference_2 == 2:
                    img['message'].append('Render is unexpected full black image.')
                    img['test_status'] = core.config.TEST_CRASH_STATUS

            for field in ['render_color_path', 'baseline_color_path']:
                image_path = os.path.join(base_dir, img['test_group'], img.get(field, 'None'))
                if image_path.endswith('.jpg') and os.path.exists(image_path):
                    try:
                        image = Image.open(image_path)
                        image.save(image_path, quality=75)
                    except Exception as e:
                        core.config.main_logger.warning('Failed to squeeze image. Exception: {}'.format(str(e)))

            if md5(render_img_path) == md5(baseline_img_path):
                for thumb in core.config.THUMBNAIL_PREFIXES + ['']:
                    baseline = os.path.join(base_dir, img['test_group'], 'Color', thumb + img.get('baseline_color_path', 'None'))
                    if os.path.exists(baseline):
                        os.remove(baseline)
                        img[thumb + 'baseline_color_path'] = img[thumb + 'render_color_path']
                if img.get('render_color_path', False):
                    img.update({'baseline_color_path': img['render_color_path']})

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

        if not 'groups_without_time_comparision' in globals():
            global groups_without_time_comparision
            groups_without_time_comparision = []

        if img['test_group'] not in groups_without_time_comparision:
            for threshold in time_diff_max:
                if baseline_time < float(threshold) and render_time - baseline_time > time_diff_max[threshold]:
                    img.update({'time_diff_status': core.config.TEST_DIFF_STATUS})
                    if img['test_status'] != core.config.TEST_CRASH_STATUS:
                        img['message'].append('Unacceptable time difference')
                        img['has_time_diff'] = True
                        break

        img.update({'difference_time': get_diff(render_time, baseline_time)})
    else:
        core.config.main_logger.error(
            '{} not exist'.format(path_to_baseline_json))
        img.update({'difference_time': -0.0})

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


def copy_stub(base_dir, destination_dir, stub_name):
    try:
        if not os.path.exists(os.path.join(base_dir, stub_name)):
            copyfile(os.path.join(destination_dir, stub_name),
                     os.path.join(base_dir, stub_name))
    except (OSError, FileNotFoundError) as err:
        core.config.main_logger.error(
            "Couldn't copy \"{}\" stub: {}".format(stub_name, str(err)))


def createArgParser():
    argparser = argparse.ArgumentParser()
    argparser.add_argument('--work_dir')
    argparser.add_argument('--base_dir')
    argparser.add_argument('--update_refs')
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

    stub_destination_dir = os.path.join(os.path.dirname(__file__), os.path.pardir, 'img')
    copy_stub(args.base_dir, stub_destination_dir, 'baseline.png')
    copy_stub(args.base_dir, stub_destination_dir, 'updating.png')

    # create report_compared.json before calculation to provide stability
    try:
        with open(render_json_path, 'r') as file:
            render_json = json.loads(file.read())
            for img in render_json:
                img.update({'difference_time': -0.0,
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
        img.update({'baseline_json_path': os.path.relpath(os.path.join(args.base_dir, img['test_group'], img['test_case'] + core.config.CASE_REPORT_SUFFIX), args.work_dir)})
        # if update baselines - skip comparision of images and set stub as a baseline image
        if 'Update' in args.update_refs:
            img.update({'baseline_color_path': os.path.relpath(
                os.path.join(args.base_dir, 'updating.png'), args.work_dir)})
        else:
            img.update(get_pixel_difference(args.work_dir, args.base_dir, img, args.pix_diff_tolerance,
                                            args.pix_diff_max))

        # check number of tries and add message if it's necessary
        if img['number_of_tries'] > 1:
            img['message'].append('Case was retried {} times'.format(img['number_of_tries'] - 1))

        img.update(get_rendertime_difference(
            args.base_dir, img, args.time_diff_max))

        if hasattr(args, 'vram_diff_max'):
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