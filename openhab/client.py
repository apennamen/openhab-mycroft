import requests
import json


class OpenHabRestClient:
    def __init__(self, host, port):
        self.url = "http://%s:%s/rest" % (host, port)

    def get_tagged_items(self):
        # find all the items tagged from openHAB.
        # supported tags: Lighting, Switchable, CurrentTemperature, Shutter...
        # the labeled items are stored in dictionaries

        shutterItemsDic = {}

        requestUrl = self.url+"/items?recursive=false"

        try:
            req = requests.get(requestUrl, headers={
                               "Accept": "application/json"})
            assert(req.status_code == 200,
                   "Impossible to connect to Open Hab server")

            json_response = req.json()
            for x in range(0, len(json_response)):
                if ("Shutter" in json_response[x]['tags']):
                    shutterItemsDic.update(
                        {json_response[x]['name']: json_response[x]['label']})
                else:
                    pass
            return shutterItemsDic

        except KeyError:
            pass

    def send_status_to_item(self, ohItem, status):
        requestUrl = self.url+"/items/%s/state" % (ohItem)
        req = requests.put(requestUrl, data=str(status),
                           headers={"Content-type": "text/plain"})

        return req.status_code

    def send_command_to_item(self, ohItem, command):
        requestUrl = self.url+"/items/%s" % (ohItem)
        req = requests.post(requestUrl, data=command,
                            headers={"Content-type": "text/plain"})

        return req.status_code

    def get_current_item_state(self, ohItem):
        requestUrl = self.url+"/items/%s/state" % (ohItem)

        try:
            req = requests.get(requestUrl, headers=self.command_headers)

            assert(req.status_code == 200, "Some issues retrieving current item state")
            
            return req.text

        except KeyError:
            pass
