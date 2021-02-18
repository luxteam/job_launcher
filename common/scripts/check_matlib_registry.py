import winreg
import argparse
import sys


def get_reg(branch, key):
    try:
        registry_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, branch, 0, winreg.KEY_READ)
        value, regtype = winreg.QueryValueEx(registry_key, key)
        winreg.CloseKey(registry_key)
        return value
    except WindowsError: return ""


# Checks if the required keys are in the registry. 0 - if present, 1 - if absent.
if __name__ == '__main__':
    MATLIB_KEY = r'SOFTWARE\AMD\RadeonProRender\MaterialLibrary\{tool}'
    p = argparse.ArgumentParser()
    p.add_argument('--tool', required=True, help='The program for which you want to check matlib')
    print(0) if get_reg(MATLIB_KEY.format(tool=p.parse_args().tool), 'MaterialLibraryPath') else print(1)
