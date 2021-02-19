import os
import time
from core.config import main_logger, MAX_UMS_SEND_RETRIES, UMS_SEND_RETRY_INTERVAL
import subprocess
import sys
import traceback
try:
    from minio import Minio
except Exception as ex:
    try:
        subprocess.call([sys.executable, "-m", "pip", "install", "--user", "Minio"])
        from minio import Minio
    except Exception as e:
        print(e)
        print("Failed to install dependency automatically.")
        print("Run: pip install twill platform shutil requests manually.")
        sys.exit(-1)

""" UMS Minio client module

Example:
mc = UMS_Minio(product_id='1793')
mc.upload_file('render_log.txt', '8253', '9152', '3071')
mc.upload_file('overall_log_suite.txt', '8253', '9152')
mc.upload_file('build.dmg', '8253')

"""


def create_mc_client(job_id):
    try:
        mc = UMS_Minio(
            product_id=job_id,
            enpoint=os.getenv("MINIO_ENDPOINT"),
            access_key=os.getenv("MINIO_ACCESS_KEY"),
            secret_key=os.getenv("MINIO_SECRET_KEY")
        )
        main_logger.info("MINIO Client created with product_id {product_id}\n enpoint: {enpoint}\n".format(
                product_id=job_id,
                enpoint=os.getenv("MINIO_ENDPOINT")
            )
        )
        return mc
    except Exception as e:
        main_logger.error("MINIO Client creation error")
        main_logger.error("Traceback: {}".format(traceback.format_exc()))


class UMS_Minio:
    # TODO: access + secret + url to env
    def __init__(self,
            product_id,
            enpoint,
            access_key,
            secret_key
        ):
        self.mc = Minio(enpoint, access_key, secret_key, secure=False)
        self.bucket_name = str(product_id).lower()
        self.__save_bucket_if_not_exits()

    def __save_bucket_if_not_exits(self):
        """ Private method for check bucket existence by name
        """
        if not self.mc.bucket_exists(self.bucket_name):
            self.mc.make_bucket(self.bucket_name)

    def upload_file(self, file_path, ums_name, *args):
        """ Method for upload file to storage
        
        @Arguments:
        file_path - file path (log.txt)
        args - (build_id, tsr_id, tcr_id)
        """
        
        # generate artifact name PATH/TO/FILE.EXT
        send_try = 0
        while send_try < MAX_UMS_SEND_RETRIES:
            file_sent = False
            try:
                artifact_name = "/".join(args) + "/" + os.path.split(file_path)[1]
                file_size = os.stat(file_path).st_size
                with open(file_path, 'rb') as data:
                    self.mc.put_object(
                        bucket_name=self.bucket_name,
                        object_name=artifact_name,
                        data=data,
                        length=file_size
                    )
                main_logger.info("Artifact '{}' sent to MINIO".format(artifact_name))
                file_sent = True
            except TypeError as e:
                main_logger.error("Could not build artifact name")
                main_logger.error("Traceback: {}".format(traceback.format_exc()))
                break
            except Exception as e:
                main_logger.error("MINIO file sending error")
                main_logger.error("Traceback: {}".format(traceback.format_exc()))
            main_logger.info('File {} sent to MINIO for UMS {} with result {} (try #{})'.format(file_path, ums_name, file_sent, send_try))
            if file_sent:
                break
            send_try += 1
            time.sleep(UMS_SEND_RETRY_INTERVAL)
