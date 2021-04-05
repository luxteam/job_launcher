import pytest
from ums_client import create_ums_client


def test_execute():
    ums_client = create_ums_client("TEST")
    assert ums_client.token in not None

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
                    "rendered_image": str(i)
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
