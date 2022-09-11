import requests
import json

from .store import OpenHabItemStore


class OpenHabClient:
    """Abstracts interaction wih OH REST API."""
    def __init__(self, host, port):
        self.url = "http://%s:%s/rest" % (host, port)
        self.refresh_cached_items()
    
    def refresh_cached_items(self):
        # refresh tagged items from openHAB.
        # supported tags are handled in store.py
        requestUrl = self.url+"/items?recursive=false"

        resp = requests.get(requestUrl, headers={
                            "Accept": "application/json"})
        assert resp.status_code == 200, "Impossible to connect to Open Hab server"

        json_response = resp.json()
        self.oh_item_store = OpenHabItemStore(json_response)
        return self.oh_item_store.items_count()

    def send_status_to_item(self, ohItem, status):
        requestUrl = self.url+"/items/%s/state" % (ohItem)
        resp = requests.put(requestUrl, data=str(status),
                           headers={"Content-type": "text/plain"})
        return resp.status_code

    def send_command_to_item(self, ohItem, command):
        requestUrl = self.url+"/items/%s" % (ohItem)
        resp = requests.post(requestUrl, data=str(command),
                            headers={"Content-type": "text/plain"})
        return resp.status_code

    def get_current_item_state(self, ohItem):
        requestUrl = self.url+"/items/%s/state" % (ohItem)
        resp = requests.get(requestUrl, headers={
                            "Content-type": "text/plain"})
        assert resp.status_code == 200, "Some issues retrieving current item state"
        return resp.text

    def find_item_name_and_type(self, message_item):
        return self.oh_item_store.find_item(message_item)
    
    def find_shutter_item_name(self, message_item):
        (ohItem, _) = self.oh_item_store.find_item_of_type(message_item, "Shutter")
        return ohItem
    
    def find_temperature_item_name(self, message_item):
        (ohItem, _) = self.oh_item_store.find_item_of_type(message_item, "TemperatureSensor")
        return ohItem
    
    def print_items(self):
        return self.oh_item_store.print_items()
