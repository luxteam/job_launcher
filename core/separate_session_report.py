import os
import json
import copy
from .config import *
from .reportExporter import save_json_report


def separate_report(work_dir, engine_list):

    with open(os.path.join(work_dir, SESSION_REPORT), 'r') as file:
        session_report = json.loads(file.read())

    for engine in engine_list:
        temp_sep_report = copy.deepcopy(session_report)

        temp_sep_report_results = {x: session_report['results'][x] for x in session_report['results'].keys() if engine in x}

        temp_sep_report_summary = {x: 0 for x in session_report['summary'].keys()}

        temp_sep_report.update({'results': temp_sep_report_results})
        temp_sep_report['machine_info'].update({'os': session_report['machine_info']['os'] + " " + engine})

        for group in temp_sep_report_results:
            for config in temp_sep_report_results[group]:
                for key in temp_sep_report_summary.keys():
                    temp_sep_report_summary[key] += temp_sep_report_results[group][config][key]
        temp_sep_report.update({'summary': temp_sep_report_summary})

        save_json_report(temp_sep_report, work_dir, engine.lower() + '_' + SESSION_REPORT, True)
