# -*- coding: iso-8859-15 -*-

#
# Copyright (c) 2010-2019 Contributors to the openHAB project
#
# See the NOTICE file(s) distributed with this work for additional
# information.
#
# This program and the accompanying materials are made available under the
# terms of the Eclipse Public License 2.0 which is available at
# http://www.eclipse.org/legal/epl-2.0
#
# SPDX-License-Identifier: EPL-2.0
#

from os.path import dirname

from adapt.intent import IntentBuilder
from mycroft import MycroftSkill, intent_handler

from .openhab import OpenHabClient

# v 0.1 - just switch on and switch off a fix light
# v 0.2 - code review
# v 0.3 - first working version on fixed light item
# v 0.4 - getTaggedItems method in order to get all the tagged items from openHAB
# v 0.5 - refresh tagged item intent
# v 0.6 - add findItemName method and import fuzzywuzzy
# v 0.7 - add intent for switchable items
# v 0.8 - merged lighting and switchable intent in onoff intent
# v 0.9 - added support to dimmable items
# v 1.0 - added Thermostat tag support
# v 1.1 - added what status Switchable tag
# v 1.2 - support to python 3.0
# v 1.3 - support german
# v 1.4 - support spanish
# v 1.5 - support to 19

__author__ = 'mortommy'


class OpenHabSkill(MycroftSkill):

    #####################################
    # LIFECYCLE METHODS AND CONFIG
    #####################################
    def __init__(self):
        super(OpenHabSkill, self).__init__(name="openHABSkill")

        self.openhab_client = None

    def initialize(self):
        supported_languages = ["en-us", "it-it", "de-de", "es-es", "fr-fr"]

        if self.lang not in supported_languages:
            self.log.error("Unsupported language " + self.lang + " for " +
                           self.name + ", shutting down skill.")
            self.shutdown()

        self.configure_openhab_client()

        # used for Padatious intents like Shutters
        self.register_entity_file('item.entity')
        self.register_entity_file('value.entity')

        self.settings_change_callback = self.handle_websettings_update

    def configure_openhab_client(self):
        if self.get_config('host') is not None and self.get_config('port') is not None:
            self.openhab_client = OpenHabClient(
                self.get_config('host'), self.get_config('port'))
            self.speak_dialog('config.ConfigurationUpdated')
        else:
            self.openhab_client = None
            self.speak_dialog('config.ConfigurationNeeded')

    def handle_websettings_update(self):
        self.configure_openhab_client()

    def get_config(self, key):
        return (self.settings.get(key) or self.config_core.get('openHABSkill', {}).get(key))

    def stop(self):
        pass

    #####################################
    # GENERAL INTENTS
    #####################################
    @intent_handler(IntentBuilder("ListItemsIntent").require("ListItemsKeyword"))
    def handle_list_items_intent(self, message):
        self.speak_dialog(
            'items.found', {'items': self.openhab_client.print_items().strip()})

    @intent_handler(IntentBuilder("RefreshTaggedItemsIntent").require("RefreshTaggedItemsKeyword"))
    def handle_refresh_tagged_items_intent(self, message):
        # to refresh the openHAB items labeled list we use an intent, we can ask Mycroft to make the refresh
        try:
            items_count = self.openhab_client.refresh_cached_items()
            self.speak_dialog('items.RefreshTaggedItems', {
                              'number_item': items_count})
        except Exception:
            self.speak_dialog('error.GetItemsListError')
            self.speak_dialog('config.CheckOpenHabServer')

    @intent_handler(IntentBuilder("WhatStatus_Intent").require("Status").require("Item"))
    def handle_what_status_intent(self, message):
        messageItem = message.data.get('Item')
        self.log.debug("Item: %s" % (messageItem))

        if messageItem is None:
            self.log.error("Item not found!")
            self.speak_dialog('error.item.notfound')
            return False

        (ohItem, ohItemType) = self.openhab_client.find_item_name_and_type(messageItem)

        if ohItem is None:
            self.log.info("Item %s not found!" % (messageItem))
            return self.speak_dialog('error.item.notfound')

        if ohItemType == "Shutter":
            return self.handle_what_status_rollershutter(ohItem, messageItem)
        else:
            self.speak_dialog('error.ItemTypeNotHandled')

    #####################################
    # ROLLERSHUTTER INTENTS
    #####################################
    @intent_handler('shutter.open.intent')
    def handle_shutter_open_intent(self, message):
        messageItem = message.data.get('item')
        self.log.debug("Item: %s" % (messageItem))
        messageValue = message.data.get('value')
        self.log.debug("WantedValue: %s" % (messageValue))

        if messageItem is None:
            self.log.info("Item %s not found!" % (messageItem))
            self.speak_dialog('error.item.notfound')
            return

        if messageValue is None:
            messageValue = 0
        else:
            messageValue = max(0, int(messageValue))

        return self.move_shutter_to_value(messageItem, messageValue)

    @intent_handler('shutter.close.intent')
    def handle_shutter_close_intent(self, message):
        messageItem = message.data.get('item')
        self.log.debug("Item: %s" % (messageItem))
        messageValue = message.data.get('value')
        self.log.debug("WantedValue: %s" % (messageValue))

        if messageItem is None:
            self.log.info("Item %s not found!" % (messageItem))
            self.speak_dialog('error.item.notfound')
            return

        if messageValue is None:
            messageValue = 100
        else:
            messageValue = min(int(messageValue), 100)

        return self.move_shutter_to_value(messageItem, messageValue)

    def move_shutter_to_value(self, item, value):
        ohItem = self.openhab_client.find_shutter_item_name(item)

        if ohItem is None:
            self.log.info("Item %s not found!" % (item))
            return self.speak_dialog('error.item.notfound')

        # Float conversion necessary to deal with groups of Shutters
        currentItemStatus = int(
            float(self.openhab_client.get_current_item_state(ohItem)))
        self.log.debug("CurrentValue: %s" % (currentItemStatus))

        unitOfMeasure = self.translate('Percentage')

        # Nothing to do, we simply inform
        if currentItemStatus == value:
            if currentItemStatus == 0:
                return self.speak_dialog('status.AlreadyOpen', {'item': item})
            if currentItemStatus == 100:
                return self.speak_dialog('status.AlreadyClose', {'item': item})
            return self.speak_dialog('status.AlreadyAtValue', {
                'value': value, 'item': item, 'units_of_measurement': unitOfMeasure})

        # We update shutter to wanted value
        statusCode = self.openhab_client.send_command_to_item(ohItem, value)
        if statusCode == 200:
            if currentItemStatus > value:
                return self.speak_dialog('shutter.OpenToValue', {
                    'value': value, 'item': item, 'units_of_measurement': unitOfMeasure})
            return self.speak_dialog('shutter.CloseToValue', {
                'value': value, 'item': item, 'units_of_measurement': unitOfMeasure})

        if statusCode == 404:
            self.log.error(
                "Item not found in OpenHab REST API")
            return self.speak_dialog('error.item.notfound')

        # statusCode must be an error status (40x, 50x...)
        self.log.error("Some issues with the command execution")
        return self.speak_dialog('error.communication')

    def handle_what_status_rollershutter(self, ohItem, messageItem):
        unitOfMeasure = self.translate('Percentage')
        try:
            # Convert to int to remove decimal parts
            # Float conversion necessary to deal with groups of Shutters
            state = int(
                float(self.openhab_client.get_current_item_state(ohItem)))
            if state == 0:
                return self.speak_dialog('status.open', {'item': messageItem})
            if state == 100:
                return self.speak_dialog('status.close', {'item': messageItem})
            return self.speak_dialog('status.close.percentage', {
                'item': messageItem, 'value': state, 'units_of_measurement': unitOfMeasure})
        except Exception:
            self.log.error("Error retrieving current item state")
            self.speak_dialog('error.communication')

    #####################################
    # TEMPERATURE INTENTS
    #####################################
    @intent_handler('temperature.status.intent')
    def handle_what_temperature(self, message):
        room = message.data.get('room')
        self.log.debug("Asked temperature for room %s" % room)
        
        if room is None:
            return self.speak_dialog('error.room.notunderstood')

        ohItem = self.openhab_client.find_temperature_item_name(room)
        
        if ohItem is None:
            return self.speak_dialog('error.item.notfound')
        
        self.log.debug("Corresponding OH item %s" % (ohItem))
        
        try:
            state = self.openhab_client.get_current_item_state(ohItem)
            
            return self.speak_dialog('temperature.status', { 'room': room, 'temperature': state })
        except Exception:
            self.log.error("Error retrieving current item state")
            self.speak_dialog('error.communication')
            
    #####################################
    # HUMIDITY INTENTS
    #####################################
    @intent_handler('humidity.status.intent')
    def handle_what_temperature(self, message):
        room = message.data.get('room')
        self.log.debug("Asked humidity for room %s" % room)
        
        if room is None:
            return self.speak_dialog('error.room.notunderstood')

        ohItem = self.openhab_client.find_humidity_item_name(room)
        
        if ohItem is None:
            return self.speak_dialog('error.item.notfound')
        
        self.log.debug("Corresponding OH item %s" % (ohItem))
        
        try:
            state = self.openhab_client.get_current_item_state(ohItem)
            
            return self.speak_dialog('humidity.status', { 'room': room, 'humidity': state })
        except Exception:
            self.log.error("Error retrieving current item state")
            self.speak_dialog('error.communication')
            

def create_skill():
    return OpenHabSkill()
