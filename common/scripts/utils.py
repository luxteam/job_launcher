import json
import pyscreenshot
import sys
import os
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir, os.path.pardir)))
import local_config


def get_error_case(cases_path):
    # FIXME: make general implementation after refactoring of Max repository
    if local_config.tool_name == "max":
        with open(cases_path) as file:
            cases = json.loads(file.read())

        for case in cases:
            if case["status"] == "progress":
                return case["case"]
        else:
            return False
    else:
        with open(cases_path) as file:
            cases = json.load(file)

        for case in cases:
            if case["status"] == "inprogress":
                return case["case"]
        else:
            return False


def make_error_screen(case_path, absolute_screen_path, relative_screen_path):
    screen = pyscreenshot.grab()
    screen = screen.convert('RGB')
    screen.save(absolute_screen_path)

    with open(case_path) as file:
        case_json = json.load(file)[0]

    case_json["error_screen_path"] = relative_screen_path

    with open(case_path, "w") as file:
        json.dump([case_json], file, indent=4)
