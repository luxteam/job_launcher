import ast
import os
import json
from core.config import *


# match gpu and OS labels in Jenkins and platform name which session_report.json contains
PLATFORM_CONVERTATIONS = {
	"Windows": {
		"os_name": "Windows 10(64bit)",
		"cards": {
			"AMD_RXVEGA": "Radeon RX Vega",
			"AMD_RX5700XT": "AMD Radeon RX 5700 XT",
			"AMD_RadeonVII": "AMD Radeon VII",
			"NVIDIA_GF1080TI": "GeForce GTX 1080 Ti",
			"AMD_WX7100": "AMD Radeon (TM) Pro WX 7100 Graphics",
			"AMD_WX9100": "Radeon (TM) Pro WX 9100",
			"NVIDIA_RTX2080TI": "GeForce RTX 2080 Ti"
		}
	},
	"Ubuntu18": {
		"os_name": "Ubuntu 18.04(64bit)",
		"cards": {
			"AMD_RadeonVII": "AMD Radeon VII",
			"NVIDIA_GTX980": "GeForce GTX 980"
		}
	},
	"OSX": {
		"os_name": "Darwin 10.14.6(64bit)",
		"cards": {
			"AMD_RXVEGA": "AMD Radeon RX Vega 56 (Metal)"
		}
	}
}

def main(lost_tests_results, tests_dir, output_dir, is_regression):
	lost_tests_data = {}
	lost_tests_results = ast.literal_eval(lost_tests_results)

	# check that session_reports is in each results directory
	results_directories = next(os.walk(os.path.abspath(output_dir)))[1]
	for results_directory in results_directories:
		for path, dirs, files in os.walk(os.path.abspath(os.path.join(output_dir, results_directory))):
			session_report_exist = False
			for file in files:
				if file.endswith(SESSION_REPORT):
					session_report_exist = True
					break
			if not session_report_exist:
				lost_tests_results.append(results_directory)


	if is_regression == 'true':
		with open(os.path.join(tests_dir, "jobs", "regression.json"), "r") as file:
			test_packages = json.load(file)
		for test_package_name in test_packages:
			lost_tests_count = len(test_packages[test_package_name].split(','))
			for lost_test_result in lost_tests_results:
				gpu_name = lost_test_result.split('-')[0]
				os_name = lost_test_result.split('-')[1]
				# join converted gpu name and os name
				joined_gpu_os_names = PLATFORM_CONVERTATIONS[os_name]["cards"][gpu_name] + "-" + PLATFORM_CONVERTATIONS[os_name]["os_name"]
				if joined_gpu_os_names not in lost_tests_data:
					lost_tests_data[joined_gpu_os_names] = {}
				lost_tests_data[joined_gpu_os_names][test_package_name] = lost_tests_count
	else:
		for lost_test_result in lost_tests_results:
			gpu_name = lost_test_result.split('-')[0]
			os_name = lost_test_result.split('-')[1]
			test_package_name = lost_test_result.split('-')[2]
			with open(os.path.join(tests_dir, "jobs", "Tests", test_package_name, TEST_CASES_JSON_NAME), "r") as file:
				data = json.load(file)
			# number of lost tests = number of tests in test package
			lost_tests_count = len(data)
			# join converted gpu name and os name
			joined_gpu_os_names = PLATFORM_CONVERTATIONS[os_name]["cards"][gpu_name] + "-" + PLATFORM_CONVERTATIONS[os_name]["os_name"]
			if joined_gpu_os_names not in lost_tests_data:
				lost_tests_data[joined_gpu_os_names] = {}
			lost_tests_data[joined_gpu_os_names][test_package_name] = lost_tests_count

	os.makedirs(output_dir, exist_ok=True)
	with open(os.path.join(output_dir, LOST_TESTS_JSON_NAME), "w") as file:
		json.dump(lost_tests_data, file, indent=4, sort_keys=True)
