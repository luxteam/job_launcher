import sys
import argparse
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir, os.path.pardir, os.path.pardir)))
import common.scripts.generate_baseline_default as generate_baseline_default
import common.scripts.generate_baseline_ct as generate_baseline_ct
import common.scripts.generate_baseline_ec as generate_baseline_ec
import core.config
try:
    from local_config import *
except ImportError:
    core.config.main_logger.critical("local config file not found. Default values will be used.")
    core.config.main_logger.critical("Correct report building isn't guaranteed")
    from core.defaults_local_config import *



def create_args_parser():
    args = argparse.ArgumentParser()
    args.add_argument('--results_root')
    args.add_argument('--baseline_root')
    if report_type == 'ct':
        args.add_argument('--case_suffix', required=False, default=core.config.CASE_REPORT_SUFFIX)
    return args


if __name__ == '__main__':
    args = create_args_parser()
    args = args.parse_args()

    args.results_root = os.path.abspath(args.results_root)
    args.baseline_root = os.path.abspath(args.baseline_root)
    
    if report_type == 'default':
        generate_baseline_default.main(args)
    elif report_type == 'ct':
        generate_baseline_ct.main(args)
    elif report_type == 'ec':
        generate_baseline_ec.main(args)
    




# import argparse
# import shutil
# import os
# import json
# import sys
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
# import core.config


# def main(args):
#     baseline_manifest_path = os.path.join(args.baseline_root, core.config.BASELINE_MANIFEST)

#     baseline_manifest = {}
#     report = []
#     if os.path.exists(baseline_manifest_path):              # if manifest already exists - update it
#         with open(baseline_manifest_path, 'r') as file:
#             baseline_manifest = json.loads(file.read())
#     if os.path.exists(args.baseline_root):
#         shutil.rmtree(args.baseline_root)

#     # find and process report_compare.json files
#     for path, dirs, files in os.walk(args.results_root):
#         for file in files:
#             if file == core.config.TEST_REPORT_NAME_COMPARED:
#                 # create destination folder in baseline location
#                 os.makedirs(os.path.join(args.baseline_root, os.path.relpath(path, args.results_root)))
#                 # copy json report with new names
#                 shutil.copyfile(os.path.join(path, file),
#                                 os.path.join(args.baseline_root, os.path.relpath(os.path.join(path, core.config.BASELINE_REPORT_NAME), args.results_root)))
#                 # copy html report
#                 if os.path.exists(os.path.join(path, core.config.TEST_REPORT_HTML_NAME)):
#                     shutil.copyfile(os.path.join(path, core.config.TEST_REPORT_HTML_NAME),
#                                     os.path.join(args.baseline_root, os.path.relpath(path, args.results_root), core.config.TEST_REPORT_HTML_NAME))

#                 with open(os.path.join(path, file), 'r') as json_report:
#                     report = json.loads(json_report.read())

#                 # copy files which described in json
#                 for test in report:
#                     # copy rendered images and thumbnails
#                     for img in core.config.POSSIBLE_JSON_IMG_RENDERED_KEYS_THUMBNAIL + core.config.POSSIBLE_JSON_IMG_RENDERED_KEYS:
#                         if img in test.keys():
#                             rendered_img_path = os.path.join(path, test[img])
#                             baseline_img_path = os.path.relpath(rendered_img_path, args.results_root)

#                             # add img to baseline manifest
#                             baseline_manifest.update({os.path.split(test[img])[-1]: baseline_img_path})
#                             # create folder in first step for current folder
#                             if not os.path.exists(os.path.join(args.baseline_root, os.path.split(baseline_img_path)[0])):
#                                 os.makedirs(os.path.join(args.baseline_root, os.path.split(baseline_img_path)[0]))

#                             try:
#                                 shutil.copyfile(rendered_img_path,
#                                                 os.path.join(args.baseline_root, baseline_img_path))
#                             except IOError as err:
#                                 core.config.main_logger.warning("Error baseline copy file: {}".format(str(err)))
#     try:
#         # save baseline manifest (using in compareByJSON.py)
#         with open(baseline_manifest_path, 'w') as file:
#             json.dump(baseline_manifest, file, indent=" ")

#         # TODO: check if session report exists and update it (is it need?)
#         # shutil.copyfile(os.path.join(args.results_root, core.config.SESSION_REPORT),
#         #                 os.path.join(os.path.abspath(args.baseline_root), core.config.BASELINE_SESSION_REPORT))
#         # TODO: copy html report
#         # shutil.copyfile(os.path.join(args.results_root, core.config.SESSION_REPORT_HTML),
#         #                 os.path.join(os.path.abspath(args.baseline_root), 'baseline_report.html'))
#         # shutil.copytree(os.path.join(args.results_root, 'report_resources'),
#         #                 os.path.join(os.path.abspath(args.baseline_root), 'report_resources'))
#     except Exception as err:
#         core.config.main_logger.error("Error while saving baseline manifest: {}".format(str(err)))
