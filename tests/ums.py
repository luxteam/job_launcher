import pytest
import os
from ums_client import UMS_Client


def test_execute():
    ums_client = UMS_Client(
        job_id=os.getenv("UMS_JOB_ID"),
        url=os.getenv("UMS_URL"),
        build_id=os.getenv("UMS_BUILD_ID"),
        env_label=os.getenv("UMS_ENV_LABEL"),
        suite_id=None,
        login=os.getenv("UMS_LOGIN"),
        password=os.getenv("UMS_PASSWORD")
    )
    print("UMS Client created with url {url}\n build_id: {build_id}\n env_label: {label} \n job_id: {job_id}".format(
             url=ums_client.url,
             build_id=ums_client.build_id,
             label=ums_client.env_label,
             job_id=ums_client.job_id
         )
    )
    assert ums_client.token is not None

    for group in os.getenv('TEST_FILTER').split(','):
        response = ums_client.get_suite_id_by_name(group)
        assert response.status_code == 200

        env = {
            "hostname": "PC-TESTING",
            "cpu": "Intel",
            "cpu_count": 4,
            "ram": 16,
            "gpu": "AMD"
        }

        response = ums_client.define_environment(env)
        assert response.status_code == 200

        res = [
            {
                "artefacts": {
                    "rendered_image": "i-" + str(i)
                },
                "status": "passed",
                "metrics": {
                    "render_time": 10 * i
                },
                "name": str(i)
            } for i in range(10)
        ]

        response = ums_client.send_test_suite(res=res, env=env)
        assert response.status_code == 200
