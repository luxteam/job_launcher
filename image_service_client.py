import json
from requests.auth import HTTPBasicAuth
from requests import get, post, put
from requests.exceptions import RequestException
from core.config import main_logger
import traceback


class ISClient:
    def __init__(self, url, login, password):
        self.url = url
        self.login = login
        self.password = password
        self.get_token()

    def get_token(self):
        response = post(
            url="{url}/api/login".format(url=self.url),
            auth=HTTPBasicAuth(self.login, self.password),
        )
        if response.status_code == 404:
            raise RequestException("Cant connect image service. Check url")
        content = response.content.decode("utf-8")
        if 'error' in content:
            raise RequestException('Check login and password')
        token = json.loads(content)["token"]
        self.token = token
        self.headers = {
            "Authorization": "Bearer " + token,
        }

    def get_existence_info_by_hash(self, hashes_seq):
        try:
            hashes_seq = list(hashes_seq)
            if len(hashes_seq) == 0:
                return {}
            response = get(
                url="{url}/api/?{query}".format(url=self.url, query="&".join([('hash=' + h) for h in hashes_seq])),
                headers=self.headers
            )
            json_data = json.loads(response.content.decode("utf-8"))
            return {img['hash']: img['image'] for img in json_data}
        except Exception as e:
            main_logger.error("Hash check sending error: {}".format(str(e)))
            return {}

    def send_image(self, path2img):
        try:
            main_logger.info("Try to send picture {} to Image Service".format(path2img))
            with open(path2img, 'rb') as img:
                response = post(
                    url="{url}/api/".format(url=self.url),
                    files={
                        'image': img
                    },
                    headers=self.headers
                )
                img.close()
            image_id = json.loads(response.content.decode("utf-8"))["image_id"]
            main_logger.info("Image sent. Got an image_id: {}".format(image_id))
            return image_id
        except:
            main_logger.error("Image sending error: {}".format(traceback.format_exc()))
            return -1
