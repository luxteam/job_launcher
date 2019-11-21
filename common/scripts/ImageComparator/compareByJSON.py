import os
import argparse
import json
import CompareMetrics
import sys
import shutil
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir, os.path.pardir, os.path.pardir)))
import core.config


def createArgParser():
    argparser = argparse.ArgumentParser()
    argparser.add_argument('--work_dir', required=True)
    argparser.add_argument('--base_dir', required=True)
    argparser.add_argument('--pix_diff_tolerance', required=False, default=core.config.PIX_DIFF_TOLERANCE)
    argparser.add_argument('--pix_diff_max', required=False, default=core.config.PIX_DIFF_MAX)
    argparser.add_argument('--time_diff_max', required=False, default=core.config.TIME_DIFF_MAX)
    argparser.add_argument('--vram_diff_max', required=False, default=core.config.VRAM_DIFF_MAX)

    return argparser


def get_diff(current, base):
    if current == base:
        return 0.0
    try:
        return (current - base) / base * 100.0
    except ZeroDivisionError:
        return 0


def check_pixel_difference(work_dir, base_dir, img, baseline_item, tolerance, pix_diff_max):

    for key in core.config.POSSIBLE_JSON_IMG_RENDERED_KEYS:
        if key in img.keys():
            render_img_path = os.path.join(work_dir, img[key])

            try:
                baseline_img_path = os.path.join(base_dir, baseline_item[key])
            except KeyError as err:
                core.config.main_logger.error("No such file in baseline: {}".format(str(err)))
                continue

            metrics = None
            try:
                metrics = CompareMetrics.CompareMetrics(render_img_path, baseline_img_path)
            except (FileNotFoundError, OSError) as err:
                core.config.main_logger.error("Error file open: ".format(str(err)))
                return img
            # BUG: loop for all possible keys, but only one compare result
            pix_difference = metrics.getDiffPixeles(tolerance=tolerance)
            img.update({'difference_color': pix_difference})
            if type(pix_difference) is str or pix_difference > pix_diff_max:
                img['test_status'] = core.config.TEST_DIFF_STATUS
            img.update({'baseline_color_path': os.path.relpath(os.path.join(base_dir, baseline_item[key]), work_dir)})

    return img


# RFE: unite check_rendertime_difference() & check_vram_difference()
def check_rendertime_difference(img, baseline_item, time_diff_max):
    try:
        img.update({'baseline_render_time': baseline_item['render_time']})
    except KeyError:
        core.config.main_logger.error("Baseline render time not defined")
    else:
        img.update({'difference_time': get_diff(img['render_time'], baseline_item['render_time'])})
        # TODO: compare diff with time_diff_max
    return img


def check_vram_difference(img, baseline_item, vram_diff_max):

    try:
        img.update({'baseline_gpu_memory_usage': baseline_item['gpu_memory_usage']})
    except KeyError:
        core.config.main_logger.error()
    else:
        img.update({'difference_vram': get_diff(img['gpu_memory_usage'], baseline_item['gpu_memory_usage'])})
        # TODO: compare diff with vram_diff_max
    return img


def check_ram_difference(img, baseline_item, ram_diff_max):

    try:
        img.update({'baseline_system_memory_usage': baseline_item['system_memory_usage']})
    except KeyError:
        core.config.main_logger.error()
    else:
        img.update({'difference_ram': get_diff(img['system_memory_usage'], baseline_item['system_memory_usage'])})
        # TODO: compare diff with ram_diff_max
    return img


def main():
    args = createArgParser().parse_args()

    render_json_path = os.path.join(args.work_dir, core.config.TEST_REPORT_NAME)
    baseline_json_path = os.path.join(args.base_dir, core.config.BASELINE_REPORT_NAME)

    if not os.path.exists(render_json_path):
        core.config.main_logger.error("Render report doesn't exists")
        return 1

    if not os.path.exists(baseline_json_path):
        core.config.main_logger.warning("Baseline or manifest not found by path: {}".format(args.base_dir))
        shutil.copyfile(render_json_path, os.path.join(args.work_dir, core.config.TEST_REPORT_NAME_COMPARED))
        return 1

    with open(render_json_path, 'r') as file:
        render_json = json.loads(file.read())

    with open(baseline_json_path, 'r') as file:
        baseline_json = json.loads(file.read())

    for img in render_json:
        baseline_item = [x for x in baseline_json if x['test_case'] == img['test_case']]
        if len(baseline_item) == 1:
            check_pixel_difference(args.work_dir, args.base_dir, img, baseline_item[0], args.pix_diff_tolerance, args.pix_diff_max)
            check_rendertime_difference(img, baseline_item[0], args.time_diff_max)
            check_vram_difference(img, baseline_item[0], args.vram_diff_max)
            check_ram_difference(img, baseline_item[0], args.vram_diff_max)
            try:
                img.update({"baseline_render_device": baseline_item[0]['render_device']})
            except KeyError:
                core.config.main_logger.error("Can't get baseline render device")
        else:
            core.config.main_logger.error("Found invalid count of test_cases in baseline json")
            continue

    with open(os.path.join(args.work_dir, core.config.TEST_REPORT_NAME_COMPARED), 'w') as file:
        json.dump(render_json, file, indent=4)

    return 0


if __name__ == '__main__':
    exit(main())
