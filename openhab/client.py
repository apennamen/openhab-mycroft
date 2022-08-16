import requests
import json

from .store import OpenHabItemStore


class OpenHabRestClient:
    """Abstracts interaction wih OH REST API."""
    def __init__(self, host, port):
        self.url = "http://%s:%s/rest" % (host, port)

    def get_tagged_items(self) -> OpenHabItemStore:
        # find all the items tagged from openHAB.
        # supported tags are handled in store.py
        requestUrl = self.url+"/items?recursive=false"

        try:
            req = requests.get(requestUrl, headers={
                               "Accept": "application/json"})
            assert req.status_code == 200, "Impossible to connect to Open Hab server"

            json_response = req.json()
            store = OpenHabItemStore()
            for x in range(0, len(json_response)):
                for tag in store.supported_tags():
                    if (tag in json_response[x]['tags']):
                        store.items[tag].update(
                            {json_response[x]['name']: json_response[x]['label']})
                    else:
                        pass
            return store

        except KeyError:
            pass

    def send_status_to_item(self, ohItem, status):
        requestUrl = self.url+"/items/%s/state" % (ohItem)
        req = requests.put(requestUrl, data=str(status),
                           headers={"Content-type": "text/plain"})
        return req.status_code

    def send_command_to_item(self, ohItem, command):
        requestUrl = self.url+"/items/%s" % (ohItem)
        req = requests.post(requestUrl, data=str(command),
                            headers={"Content-type": "text/plain"})
        return req.status_code

    def get_current_item_state(self, ohItem):
        requestUrl = self.url+"/items/%s/state" % (ohItem)

        try:
            req = requests.get(requestUrl, headers={
                               "Content-type": "text/plain"})
            assert req.status_code == 200, "Some issues retrieving current item state"
            return req.text
        except KeyError:
            pass
