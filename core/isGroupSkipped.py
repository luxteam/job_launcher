import argparse
import os
import json
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from countLostTests import PLATFORM_CONVERTATIONS
from jobs.Scripts.utils import is_case_skipped


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--gpu', required=True)
    parser.add_argument('--os', required=True)
    parser.add_argument('--engine', required=False)
    parser.add_argument('--tests_path', required=True)

    args = parser.parse_args()

    with open(args.tests_path) as file:
        cases = json.load(file)

    recovered_gpu_name= PLATFORM_CONVERTATIONS[args.os]["cards"][args.gpu]
    recovered_os_name = PLATFORM_CONVERTATIONS[args.os]["os_name"][recovered_gpu_name] if isinstance(args.os, dict) else PLATFORM_CONVERTATIONS[args.os]["os_name"]
    render_platform = {recovered_os_name, recovered_gpu_name}

    skipped_cases_num = 0
    total_cases_num = len(cases)

    for case in cases:
        if args.engine:	
            case_skipped = is_case_skipped(case, render_platform, args.engine)
        else:
            case_skipped = is_case_skipped(case, render_platform)
        if case_skipped:
            skipped_cases_num += 1
    print(skipped_cases_num == total_cases_num)
