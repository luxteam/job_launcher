import os
import argparse
import json
import datetime


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", required=True, type=str, metavar="<path>", help="path to summary_report.json")
    parser.add_argument("--results_path", required=False, type=str, metavar="<path>", help="allows to save results to use them as weights for unite test suites")

    args = parser.parse_args()

    if os.path.exists(args.path):
        with open(args.path, "r") as file:
            summary_report = json.load(file)   
    else:
        print("Could not find summary_report.json by specified path")
        exit(-1)

    test_suites_info = {}
    platforms_count = 0

    sum_summary_duration = 0
    min_summary_duration = -1
    max_summary_duration = -1

    for platform_name, platform_content in summary_report.items():
        platforms_count += 1

        platform_duration = platform_content["summary"]["duration"]

        sum_summary_duration += platform_duration

        if min_summary_duration > platform_duration or min_summary_duration == -1:
            min_summary_duration = platform_duration

        if max_summary_duration < platform_duration or max_summary_duration == -1:
            max_summary_duration = platform_duration

        for suite_name, suite_content in platform_content["results"].items():

            if suite_name not in test_suites_info:
                test_suites_info[suite_name] = {}
                test_suites_info[suite_name]["summary"] = 0
                test_suites_info[suite_name]["min"] = -1
                test_suites_info[suite_name]["max"] = -1

            suite_duration = suite_content[""]["duration"]

            test_suites_info[suite_name]["summary"] += suite_duration

            if test_suites_info[suite_name]["min"] > suite_duration or test_suites_info[suite_name]["min"] == -1:
                test_suites_info[suite_name]["min"] = suite_duration

            if test_suites_info[suite_name]["max"] < suite_duration or test_suites_info[suite_name]["max"] == -1:
                test_suites_info[suite_name]["max"] = suite_duration

    print("Averange time for each test suite:")

    for test_suite, value in test_suites_info.items():
        print("{name} -> {avrg} (min: {min}, max: {max})".format(name=test_suite, 
            avrg=str(datetime.timedelta(seconds=round(value["summary"] / platforms_count))), 
            min=str(datetime.timedelta(seconds=round(value["min"]))), 
            max=str(datetime.timedelta(seconds=round(value["max"])))))

    print("\nAverange all suites execution time: {avrg} (one suite average: {one})".format(
        avrg=str(datetime.timedelta(seconds=round(sum_summary_duration / platforms_count))),
        one=str(datetime.timedelta(seconds=round(sum_summary_duration / len(test_suites_info) / platforms_count)))))

    print("Min all suites execution time: {min} (one suite average: {one})".format(
        min=str(datetime.timedelta(seconds=round(min_summary_duration))),
        one=str(datetime.timedelta(seconds=round(min_summary_duration / len(test_suites_info))))))

    print("Max all suites execution time: {max} (one suite average: {one})".format(
        max=str(datetime.timedelta(seconds=round(max_summary_duration))),
        one=str(datetime.timedelta(seconds=round(max_summary_duration / len(test_suites_info))))))

    if args.results_path:
        results = {}
        results["weights"] = []
        test_suites_info_copy = test_suites_info.copy()
        for i in range (len(test_suites_info_copy)):
            max_test_suite = None
            max_value = -1
            for test_suite, value in test_suites_info_copy.items():
                if value["max"] > max_value:
                    max_test_suite = test_suite
                    max_value = value["max"]
            results["weights"].append({"suite_name": max_test_suite, "value": round(max_value)})
            test_suites_info_copy.pop(max_test_suite)

        with open(args.results_path, "w") as file:
            summary_report = json.dump(results, file, indent=4)   
