import os
import argparse
import json
import CompareMetrics


def createArgParser():
    argparser = argparse.ArgumentParser()
    argparser.add_argument('--stage_report')
    argparser.add_argument('--work_dir')
    argparser.add_argument('--base_dir')
    argparser.add_argument('--report_name')
    argparser.add_argument('--result_name')

    return argparser


def compareFoldersWalk(jsonReport, workFolder, baseFolder, root_dir):
    for img in jsonReport:
        file1 = os.path.abspath(os.path.join(workFolder, img['file_name']))
        file2 = os.path.abspath(os.path.join(baseFolder, img['file_name']))

        try:
            metrics = CompareMetrics.CompareMetrics(file1, file2)
            key_diff = ('difference_' + os.path.basename(workFolder)).lower()
            key_src = ('baseline_' + os.path.basename(workFolder) + '_path').lower()
            # key_diff = ('difference_' + suffix + '_' + os.path.basename(workFolder)).lower()
            # key_src = ('path_' + suffix + '_' + os.path.basename(workFolder)).lower()

            diff = {key_diff: metrics.getDiffPixeles()}
            src = {key_src: os.path.relpath(file2, root_dir)}
        except:
            # print("Diff tool can't find path")
            pass
        else:
            img.update(diff)
            img.update(src)


    return jsonReport


def main(args):
    stage_report = [{'status': 'INIT'}, {'log': ['compareByJSON.py started;']}]

    jsonReport = ""
    try:
        with open(os.path.abspath(os.path.join(args.work_dir, args.report_name)), 'r') as file:
            jsonReport = file.read()
    except OSError:
        stage_report[1]['log'].append('Report not found;')
        stage_report[0]['status'] = 'FAILED'
        return stage_report

    try:
        jsonReport = json.loads(jsonReport)
    except json.JSONDecodeError:
        stage_report[1]['log'].append('Error in json report; Try to fix it;')
        s = list(jsonReport)
        if s[-1] == ',':
            del s[-1]
        s.append(']')
        try:
            jsonReport = json.loads("".join(s))
        except json.JSONDecodeError:
            stage_report[1]['log'].append('Error was not fixed;')
            stage_report[0]['status'] = 'FAILED'
            return stage_report
    else:
        stage_report[1]['log'].append('Error was fixed;')

    if os.path.exists(os.path.abspath(args.base_dir)):
        for path, dirs, files in os.walk(args.base_dir):
            for dir in dirs:
                if dir == 'Opacity' or dir == 'Color' or dir == 'images':
                    if os.path.basename(path) == os.path.basename(args.work_dir):
                    # stage_report[1]['log'].append('Comparison: ' + os.path.join(path, dir))
                        jsonReport = compareFoldersWalk(jsonReport, os.path.join(args.work_dir, dir), os.path.join(path, dir), args.work_dir)
    else:
        stage_report[1]['log'].append('Baseline dose not exist;')

    stage_report[0]['status'] = 'OK'

    with open(os.path.join(args.work_dir, args.result_name), 'w') as file:
        json.dump(jsonReport, file, indent=" ", sort_keys=True)

    return stage_report


if __name__ == '__main__':
    args = createArgParser().parse_args()
    stage_report = main(args)

    with open(os.path.join(args.work_dir, args.stage_report), 'w') as file:
        json.dump(stage_report, file, indent=' ')
