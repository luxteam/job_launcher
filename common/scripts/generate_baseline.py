import argparse
import shutil
import os
import json
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
import core.config


def create_args_parser():
    args = argparse.ArgumentParser()
    args.add_argument('--results_root')
    args.add_argument('--baseline_root')
    return args


def main():
    args = create_args_parser()
    args = args.parse_args()

    args.results_root = os.path.abspath(args.results_root)
    args.baseline_root = os.path.abspath(args.baseline_root)

    if os.path.exists(args.baseline_root):
        shutil.rmtree(args.baseline_root)

    # find and process report_compare.json files
    for path, dirs, files in os.walk(args.results_root):
        for file in files:
            # if file == core.config.TEST_REPORT_NAME_COMPARED:

            if file.endswith(core.config.CASE_REPORT_SUFFIX):
                # create destination folder in baseline location
                if not os.path.exists(os.path.join(args.baseline_root, os.path.relpath(path, args.results_root))):
                    os.makedirs(os.path.join(args.baseline_root, os.path.relpath(path, args.results_root)))
                # copy json report with new names
                shutil.copyfile(os.path.join(path, file),
                                os.path.join(args.baseline_root, os.path.relpath(os.path.join(path, file), args.results_root)))

                with open(os.path.join(path, file), 'r') as json_report:
                    report = json.loads(json_report.read())

                # copy files which described in json
                for test in report:
                    # copy rendered images and thumbnails
                    for img in core.config.POSSIBLE_JSON_IMG_RENDERED_KEYS_THUMBNAIL + core.config.POSSIBLE_JSON_IMG_RENDERED_KEYS:
                        if img in test.keys():
                            rendered_img_path = os.path.join(path, test[img])
                            baseline_img_path = os.path.relpath(rendered_img_path, args.results_root)

                            # create folder in first step for current folder
                            if not os.path.exists(os.path.join(args.baseline_root, os.path.split(baseline_img_path)[0])):
                                os.makedirs(os.path.join(args.baseline_root, os.path.split(baseline_img_path)[0]))

                            try:
                                shutil.copyfile(rendered_img_path,
                                                os.path.join(args.baseline_root, baseline_img_path))
                            except IOError as err:
                                core.config.main_logger.warning("Error baseline copy file: {}".format(str(err)))


if __name__ == '__main__':
    main()
