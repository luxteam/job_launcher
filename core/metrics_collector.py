import os
import json
import re
import traceback
from glob import glob
from collections import OrderedDict
from core.config import main_logger, TRACKED_METRICS_LOCATION_NAME, TRACKED_METRICS_JSON_NAME


class MetricsCollector:
    def __init__(self, tracked_metrics_config):
        # configuration of tracked metrics (see defaults_local_config for details)
        self.tracked_metrics_config = tracked_metrics_config
        # values of tracked metrics
        self.tracked_metrics_data = {}
        # list of all metrics which are tracked
        self.found_metrics = {}
        # grouped lists of metrics (how they should be grouped on charts)
        self.groupped_metrics = {}
        # general info about build (e.g. core version, commit sha)
        self.general_info = {}

    def collect_metrics_test_case(self, platform, test_package, item):
        try:
            tracked_metrics_config = self.tracked_metrics_config
            tracked_metrics_data = self.tracked_metrics_data
            found_metrics = self.found_metrics
            groupped_metrics = self.groupped_metrics
            for tracked_metric in tracked_metrics_config:
                if tracked_metric in item:
                    test_case = item['test_case']
                    # add necessary platform in tracked_metrics_data if it's required
                    if platform not in tracked_metrics_data:
                        tracked_metrics_data[platform] = {}
                        tracked_metrics_data[platform]['groups'] = {}
                    groups = tracked_metrics_data[platform]['groups']
                    # add necessary test group in tracked_metrics_data if it's required
                    if test_package not in groups:
                        groups[test_package] = {}
                        groups[test_package]['metrics'] = {}
                    # add necessary test case in tracked_metrics_data if it's required
                    if test_case not in groups[test_package]['metrics']:
                        groups[test_package]['metrics'][test_case] = {}
                    # change metric name if it depends on value of some other field
                    if 'separation_field' in tracked_metrics_config[tracked_metric]:
                        separation_field = tracked_metrics_config[tracked_metric]['separation_field']
                        # get value of separation_field for currect test case
                        groups[test_package]['metrics'][test_case][separation_field] = item[separation_field]
                        if 'metric_name' in tracked_metrics_config[tracked_metric]:
                            # get base name of metric from config
                            tracked_metric_name = '{}_{}'.format(tracked_metrics_config[tracked_metric]['metric_name'], item[separation_field])
                        else:
                            tracked_metric_name = '{}_{}'.format(tracked_metric, item[separation_field])
                        displaying_name = '{} ({})'.format(tracked_metrics_config[tracked_metric]['displaying_name'], item[separation_field])
                    else:
                        if 'metric_name' in tracked_metrics_config[tracked_metric]:
                            tracked_metric_name = tracked_metrics_config[tracked_metric]['metric_name']
                        else:
                            tracked_metric_name = tracked_metric
                        displaying_name = tracked_metrics_config[tracked_metric]['displaying_name']
                    if tracked_metric_name not in found_metrics:
                        # save metric name and its configuration for use it during calculation of summary of groups and platforms
                        found_metrics[tracked_metric_name] = {'name_in_config': tracked_metric, 'config': tracked_metrics_config[tracked_metric]}
                    # add metric in groupped_metrics dict
                    if tracked_metric not in groupped_metrics:
                        groupped_metrics[tracked_metric] = {}
                        groupped_metrics[tracked_metric]['metrics'] = {}
                        groupped_metrics[tracked_metric]['config'] = tracked_metrics_config[tracked_metric]
                    if tracked_metric_name not in groupped_metrics[tracked_metric]['metrics']:
                        groupped_metrics[tracked_metric]['metrics'][tracked_metric_name] = {}
                        groupped_metrics[tracked_metric]['metrics'][tracked_metric_name]['displaying_name'] = displaying_name
                    # get name of function which should be used for calculate value of tracked metric
                    fuction_name = tracked_metrics_config[tracked_metric]['function']
                    if fuction_name == 'match':
                        if re.match(tracked_metrics_config[tracked_metric]['pattern'], item[tracked_metric]):
                            groups[test_package]['metrics'][test_case][tracked_metric_name] = 1
                        else:
                            groups[test_package]['metrics'][test_case][tracked_metric_name] = 0
                    elif fuction_name == 'avrg' or fuction_name == 'sum':
                        groups[test_package]['metrics'][test_case][tracked_metric_name] = item[tracked_metric]
        except Exception as e:
            if 'test_case' in item:
                case_name = item['test_case'] 
            else:
                case_name = 'Unknown'
            main_logger.error('Failed to collect tracked metrics for test case (platform: {platform}, group: {group}, case: {case}). Reason: {exception}'
                .format(platform=platform, group=test_package, case=case_name, exception=str(e)))
            main_logger.error('Traceback: {}'.format(traceback.format_exc()))


    def collect_metrics_test_group(self, platform, test_package):
        try:
            tracked_metrics_config = self.tracked_metrics_config
            tracked_metrics_data = self.tracked_metrics_data
            found_metrics = self.found_metrics
            if platform in tracked_metrics_data and test_package in tracked_metrics_data[platform]['groups']:
                tracked_metrics_summary = {}
                groups = tracked_metrics_data[platform]['groups']
                # iterate through named of saved metrics during parsing of data of test cases
                for possible_metric_name in found_metrics:                    
                    metric_summary = {}
                    number = {}
                    for test_case in groups[test_package]['metrics']:
                        if possible_metric_name in groups[test_package]['metrics'][test_case]:
                            # save init values for counters of tracked metrics (sum and number)
                            if possible_metric_name not in metric_summary:
                                metric_summary[possible_metric_name] = 0
                            if possible_metric_name not in number:
                                number[possible_metric_name] = 0
                            # update sum of some metric and number of its appearances
                            metric_summary[possible_metric_name] += groups[test_package]['metrics'][test_case][possible_metric_name]
                            number[possible_metric_name] += 1
                    # calculate summary
                    for metric_name in metric_summary:
                        if number[metric_name]:
                            # get name of metric from config
                            name_in_config = found_metrics[metric_name]['name_in_config']
                            # get name of function which should be used for calculate value of summary for test group
                            fuction_name = tracked_metrics_config[name_in_config]['function']
                            if fuction_name == 'avrg':
                                tracked_metrics_summary[metric_name] = metric_summary[metric_name] / number[metric_name]
                            elif fuction_name == 'match' or fuction_name == 'sum':
                                tracked_metrics_summary[metric_name] = metric_summary[metric_name]
                groups[test_package]['summary'] = tracked_metrics_summary
        except Exception as e:
            main_logger.error('Failed to collect tracked metrics for test group (platform: {platform}, group: {group}). Reason: {exception}'
                .format(platform=platform, group=test_package, exception=str(e)))
            main_logger.error('Traceback: {}'.format(traceback.format_exc()))


    def collect_metrics_platforms(self):
        tracked_metrics_config = self.tracked_metrics_config
        tracked_metrics_data = self.tracked_metrics_data
        found_metrics = self.found_metrics
        for platform in tracked_metrics_data:
            try:
                tracked_metrics_summary = {}
                # iterate through named of saved metrics during parsing of data of test cases
                for possible_metric_name in found_metrics:
                    groups = tracked_metrics_data[platform]['groups']
                    metric_summary = {}
                    number = {}
                    for test_group in groups:
                        # save init values for counters of tracked metrics (sum and number)
                        if possible_metric_name in groups[test_group]['summary']:
                            if possible_metric_name not in metric_summary:
                                metric_summary[possible_metric_name] = 0
                            if possible_metric_name not in number:
                                number[possible_metric_name] = 0
                            # update sum of some metric and number of its appearances
                            metric_summary[possible_metric_name] += groups[test_group]['summary'][possible_metric_name]
                            number[possible_metric_name] += 1
                    # calculate summary
                    for possible_metric_name in metric_summary:
                        if number:
                            # get name of metric from config
                            name_in_config = found_metrics[possible_metric_name]['name_in_config']
                            # get name of function which should be used for calculate value of summary for test group
                            if tracked_metrics_config[name_in_config]['function'] == 'avrg':
                                tracked_metrics_summary[possible_metric_name] = metric_summary[possible_metric_name] / number
                            else:
                                tracked_metrics_summary[possible_metric_name] = metric_summary[possible_metric_name]
                tracked_metrics_data[platform]['summary'] = tracked_metrics_summary
            except Exception as e:
                main_logger.error('Failed to collect tracked metrics for test platform (platform: {platform}). Reason: {exception}'
                    .format(platform=platform, exception=str(e)))
                main_logger.error("Traceback: {}".format(traceback.format_exc()))


    # add groupped metrics from relatedtest cases for visualize them on charts
    def add_groupped_metrics_in_cases(self):
        try:
            tracked_metrics_data = self.tracked_metrics_data
            found_metrics = self.found_metrics
            for platform in tracked_metrics_data:
                groups = tracked_metrics_data[platform]['groups']
                for test_group in groups:
                    for possible_metric_name in found_metrics:
                        # check that current metric could be splitted
                        if 'separation_field' in found_metrics[possible_metric_name]['config']:
                            separation_field = found_metrics[possible_metric_name]['config']['separation_field']
                            cases = groups[test_group]['metrics']
                            for case in cases:
                                # skip if this metric already exists in case
                                if possible_metric_name in case:
                                    continue
                                else:
                                    for other_case in cases:
                                        # try to find related cases cases by replacing of part of name with value from separation field
                                        if other_case.replace(cases[other_case][separation_field], cases[case][separation_field]) == case:
                                            if possible_metric_name in cases[other_case]:
                                                cases[case][possible_metric_name] = cases[other_case][possible_metric_name]
                                                break
        except Exception as e:
            main_logger.error("Can't add groupped metrics in cases: {}".format(str(e)))
            main_logger.error("Traceback: {}".format(traceback.format_exc()))


    def update_tracked_metrics_history(self, work_dir, build_number):
        try:
            tracked_metrics_file_path = os.path.join(work_dir, TRACKED_METRICS_LOCATION_NAME)
            if not os.path.exists(tracked_metrics_file_path):
                os.makedirs(tracked_metrics_file_path)
            with open(os.path.abspath(os.path.join(tracked_metrics_file_path, TRACKED_METRICS_JSON_NAME.format(build_number))), "w", encoding='utf8') as file:
                json.dump({"general_info": self.general_info, "data": self.tracked_metrics_data}, file, indent=4, sort_keys=True)
        except Exception as e:
            main_logger.error("Can't save tracked metrics data: {}".format(str(e)))
            main_logger.error("Traceback: {}".format(traceback.format_exc()))


    def save_general_info(self, key, value):
        self.general_info[key] = value


    @staticmethod
    def load_tracked_metrics_history(work_dir, max_files_number):
        tracked_metrics_history = OrderedDict()
        general_info_history = OrderedDict()
        try:
            tracked_metrics_file_path = os.path.join(work_dir, TRACKED_METRICS_LOCATION_NAME)
            tracked_metrics_files = sorted(glob(os.path.join(tracked_metrics_file_path ,'*.json')), key=lambda x: int(os.path.splitext(x)[0].split('_')[-1]), reverse=True)
            for i in range(max_files_number):
                if i == len(tracked_metrics_files):
                    break
                with open(tracked_metrics_files[i], 'r') as tracked_metrics_file:
                    tracked_metrics_file_data = json.load(tracked_metrics_file) 
                file_build_number = re.search(r'\d+', tracked_metrics_files[i].split(os.path.sep)[-1]).group(0)
                if "general_info" in tracked_metrics_file_data:
                    tracked_metrics_history[file_build_number] = tracked_metrics_file_data["data"]
                    general_info_history[file_build_number] = tracked_metrics_file_data["general_info"]
                else:
                    tracked_metrics_history[file_build_number] = tracked_metrics_file_data
                    general_info_history[file_build_number] = {}
            tracked_metrics_history = OrderedDict(reversed(list(tracked_metrics_history.items())))
        except Exception as e:
            main_logger.error("Can't collect history of tracked metrics: {}".format(str(e)))
            main_logger.error("Traceback: {}".format(traceback.format_exc()))

        return tracked_metrics_history, general_info_history
