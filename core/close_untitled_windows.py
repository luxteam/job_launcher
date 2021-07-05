import platform
import time
import psutil
from .config import main_logger

if platform.system() == 'Darwin':
    from Quartz import CGWindowListCopyWindowInfo
    from Quartz import kCGWindowListOptionOnScreenOnly
    from Quartz import kCGWindowListExcludeDesktopElements
    from Quartz import kCGNullWindowID
    from Quartz import kCGWindowName
    from Quartz import CGWindowListCreateImage
    from Quartz import CGRectMake
    from Quartz import kCGWindowImageDefault

def close_untitled_windows():
    if platform.system() == 'Darwin':
        try:
            # for receive kCGWindowName values from CGWindowListCopyWindowInfo function it's necessary to call any function of Screen Record API
            CGWindowListCreateImage(
                CGRectMake(0, 0, 1, 1),
                kCGWindowListOptionOnScreenOnly,
                kCGNullWindowID,
                kCGWindowImageDefault
            )
            ws_options = kCGWindowListOptionOnScreenOnly + kCGWindowListExcludeDesktopElements
            windows_list = CGWindowListCopyWindowInfo(ws_options, kCGNullWindowID)

            for window in windows_list:
                if not 'kCGWindowName' in window or window['kCGWindowName'] == '':
                    pid = window['kCGWindowOwnerPID']
                    p = psutil.Process(pid)
                    p_info = p.as_dict(attrs=['pid', 'name', 'cpu_percent', 'username'])
                    try:
                        main_logger.info("Trying to kill process {name}".format(name=p_info['name']))

                        p.terminate()
                        time.sleep(10)

                        p.kill()
                        time.sleep(10)

                        status = p.status()
                        main_logger.error("Process {name} is alive (status: {status}".format(
                            name=p_info["name"],
                            status=status
                        ))
                    except psutil.NoSuchProcess:
                        main_logger.info("ATTENTION: {name} is killed.".format(
                            name=p_info['name']
                        ))
        except Exception as err:
            main_logger.error(
                'Exception has occurred while closing untitled windows: {}'.format(str(err)))