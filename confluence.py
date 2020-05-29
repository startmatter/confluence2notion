import os
import tempfile
from urllib.parse import urlparse, unquote_plus
import requests


class Confluence:
    def __init__(self, base_url, auth):
        self.base_url = base_url
        self.auth = auth

    def download_file(self, file_url):
        if file_url.startswith("/"):
            file_url = self.base_url + file_url
        dir = tempfile.mkdtemp()

        filename = unquote_plus(urlparse(file_url).path.split("/")[-1])

        with open(os.path.join(dir, filename), "wb") as tf:
            with requests.get(file_url, stream=True, auth=self.auth) as r:
                r.raise_for_status()
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:  # filter out keep-alive new chunks
                        tf.write(chunk)
            tf.flush()
            tf.seek(0)
        return tf

    def get_list(self, url, params=None):
        start = 0

        while True:
            if params:
                params.update({"start": start})
            else:
                params = {"start": start}

            resp = requests.get(url, params, auth=self.auth)
            resp.raise_for_status()
            data = resp.json()

            limit = data["limit"]
            size = data["size"]

            for data_item in data["results"]:
                yield data_item

            if start + limit >= size:
                break

            start = start + limit

    def get_spaces(self):
        return self.get_list(f"{self.base_url}/rest/api/space")

    def get_page(self, page_url):
        resp = requests.get(
            f"{self.base_url}{page_url}",
            {"expand": ["body.export_view", "children"]},
            auth=self.auth,
        )
        data = resp.json()
        if data.get("statusCode", 200) > 299:
            raise ValueError(str(data))
        return data

    def get_children(self, page_content):
        return self.get_list(
            f"{self.base_url}{page_content['_expandable']['children']}/page",
            {"expand": ["body.export_view", "children"]},
        )

    def get_attachments(self, page_content):
        resp = requests.get(
            f"{self.base_url}{page_content['_expandable']['children']}/attachment",
            auth=self.auth,
        )
        results = resp.json()["results"]

        for child_page in results:  # TODO handle pagination
            yield child_page
