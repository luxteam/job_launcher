import argparse
import shutil
import os
import json


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

    report = []
    for path, dirs, files in os.walk(args.results_root):
        for file in files:
            if file == 'report_compare.json':

                with open(os.path.join(path, file), 'r') as json_report:
                    report = json.loads(json_report.read())

                for test in report:
                    # baseline_name = '.'.join([test['tool'], test['render_device'], test['render_version']])
                    for img in ['render_color_path', 'render_opacity_path']:
                        try:
                            rendered_img_path = os.path.join(path, test[img])
                            baseline_img_path = os.path.relpath(rendered_img_path, args.results_root)

                            # if not os.path.exists(os.path.join(args.baseline_root, baseline_name, os.path.split(baseline_img_path)[0])):
                            try:
                                os.makedirs(os.path.join(args.baseline_root, os.path.split(baseline_img_path)[0]))
                                # os.makedirs(os.path.join(args.baseline_root, baseline_name, os.path.split(baseline_img_path)[0]))
                            except Exception as err:
                                # print(str(err))
                                pass

                            try:
                                shutil.copyfile(rendered_img_path, os.path.join(args.baseline_root, baseline_img_path))
                                # shutil.copyfile(rendered_img_path, os.path.join(args.baseline_root, baseline_name, baseline_img_path))
                            except Exception as err:
                                # print(str(err))
                                pass
                        except:
                            pass
                # shutil.copyfile(os.path.join(path, file), os.path.join(args.baseline_root, baseline_name,
                shutil.copyfile(os.path.join(path, file),
                                os.path.join(args.baseline_root, os.path.relpath(os.path.join(path, file),args.results_root))
                                )
            elif file == 'result.html':
                try:
                    os.makedirs(os.path.join(args.baseline_root, os.path.relpath(path, args.results_root)))
                except Exception as err:
                    # print(str(err))
                    pass
                # print(os.path.join(args.baseline_root, os.path.relpath(path, args.results_root), file))
                shutil.copyfile(os.path.join(path,file),
                                os.path.join(args.baseline_root, os.path.relpath(path, args.results_root), file)
                                )

    try:
        report = 'session_report.html'
        shutil.copyfile(os.path.join(args.results_root, report),
            os.path.join(os.path.abspath(args.baseline_root), report)
                        )
    except Exception as err:
        print(str(err))
        # pass


if __name__ == '__main__':
    main()