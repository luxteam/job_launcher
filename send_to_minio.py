import os
import argparse
from minio_client import create_mc_client
from core.config import *
import glob

res = []
transferred_test_cases = []

minio_client_prod = create_mc_client(os.getenv("UMS_JOB_ID_PROD"))
minio_client_dev = create_mc_client(os.getenv("UMS_JOB_ID_DEV"))


def send_to_minio(files_path, pattern, dest_dir=None):
    args_prod = (arg for arg in (os.getenv("UMS_BUILD_ID_PROD"), dest_dir) if arg is not None)
    args_dev = (arg for arg in (os.getenv("UMS_BUILD_ID_DEV"), dest_dir) if arg is not None)
    
    files = glob.glob(os.path.join(files_path, pattern))
    for file in files:
        if minio_client_prod:
            minio_client_prod.upload_file(file, "PROD", *args_prod)
        if minio_client_dev:
            minio_client_dev.upload_file(file, "DEV", *args_dev)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--files_path', required=True, type=str, help='path to files')
    parser.add_argument('--pattern', required=True, type=str, help='pattern for files which must be sent')
    parser.add_argument('--dest_dir', required=False, type=str, help='destination folder to save files to')

    args = parser.parse_args()

    send_to_minio(args.files_path, args.pattern, args.dest_dir)
