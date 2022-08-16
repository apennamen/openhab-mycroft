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
from mycroft.util.log import getLogger
from rapidfuzz import fuzz

from .openhab.client import OpenHabRestClient

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

LOGGER = getLogger(__name__)


class OpenHabSkill(MycroftSkill):

    def __init__(self):
        super(OpenHabSkill, self).__init__(name="openHABSkill")

        self.openhab_client = None
        self.shutterItemsDic = dict()

    def initialize(self):
        supported_languages = ["en-us", "it-it", "de-de", "es-es", "fr-fr"]

        if self.lang not in supported_languages:
            LOGGER.error("Unsupported language " + self.lang + " for " +
                         self.name + ", shutting down skill.")
            self.shutdown()

        self.configure_openhab_client()

        self.register_entity_file('item.entity')
        self.register_entity_file('value.entity')

        self.settings_change_callback = self.handle_websettings_update

    def get_config(self, key):
        return (self.settings.get(key) or self.config_core.get('openHABSkill', {}).get(key))

    def configure_openhab_client(self):
        if self.get_config('host') is not None and self.get_config('port') is not None:
            self.openhab_client = OpenHabRestClient(
                self.get_config('host'), self.get_config('port'))
            self.speak_dialog('ConfigurationUpdated')
            self.handle_refresh_tagged_items_intent("")
        else:
            self.openhab_client = None
            self.speak_dialog('ConfigurationNeeded')
            

    def handle_websettings_update(self):
        self.configure_openhab_client()

    def findItemName(self, itemDictionary, messageItem):

        bestScore = 0
        score = 0
        bestItem = None

        try:
            for itemName, itemLabel in list(itemDictionary.items()):
                score = fuzz.ratio(messageItem, itemLabel,
                                   score_cutoff=bestScore)
                if score > bestScore:
                    bestScore = score
                    bestItem = itemName
        except KeyError:
            pass

        return bestItem

    def getItemsFromDict(self, typeStr, itemsDict):
        if len(itemsDict) == 0:
            return ""
        else:
            return "%s: %s" % (typeStr, ', '.join(list(itemsDict.values())))

    @intent_handler(IntentBuilder("ListItemsIntent").require("ListItemsKeyword"))
    def handle_list_items_intent(self, message):
        msg = self.getItemsFromDict("Shutters", self.shutterItemsDic)
        self.speak_dialog('FoundItems', {'items': msg.strip()})

    @intent_handler(IntentBuilder("RefreshTaggedItemsIntent").require("RefreshTaggedItemsKeyword"))
    def handle_refresh_tagged_items_intent(self, message):
        # to refresh the openHAB items labeled list we use an intent, we can ask Mycroft to make the refresh
        try:
            self.shutterItemsDic = self.openhab_client.get_tagged_items()
            dictLenght = len(self.shutterItemsDic)
            self.speak_dialog('RefreshTaggedItems', {'number_item': dictLenght})
        except Exception:
            self.speak_dialog('GetItemsListError')
            self.speak_dialog('CheckOpenHabServer')
                

    @intent_handler('shutter.open.intent')
    def handle_shutter_open_intent(self, message):
        messageItem = message.data.get('item')
        LOGGER.debug("Item: %s" % (messageItem))
        messageValue = message.data.get('value')
        LOGGER.debug("WantedValue: %s" % (messageValue))

        if messageItem is None:
            LOGGER.error("Item not found!")
            self.speak_dialog('ItemNotFoundError')
            return

        if messageValue is None:
            messageValue = 0
        else:
            messageValue = max(0, int(messageValue))

        return self.move_shutter_to_value(messageItem, messageValue)

    @intent_handler('shutter.close.intent')
    def handle_shutter_close_intent(self, message):
        messageItem = message.data.get('item')
        LOGGER.debug("Item: %s" % (messageItem))
        messageValue = message.data.get('value')
        LOGGER.debug("WantedValue: %s" % (messageValue))

        if messageItem is None:
            LOGGER.error("Item not found!")
            self.speak_dialog('ItemNotFoundError')
            return

        if messageValue is None:
            messageValue = 100
        else:
            messageValue = min(int(messageValue), 100)

        return self.move_shutter_to_value(messageItem, messageValue)

    def move_shutter_to_value(self, item, value):
        self.currStatusItemsDic = dict()

        unitOfMeasure = self.translate('Percentage')
        self.currStatusItemsDic.update(self.shutterItemsDic)

        ohItem = self.findItemName(self.currStatusItemsDic, item)

        if ohItem != None:
            currentItemStatus = int(self.getCurrentItemStatus(ohItem))
            LOGGER.debug("CurrentValue: %s" % (currentItemStatus))

            # Nothing to do, we simply inform
            if currentItemStatus == value:
                if currentItemStatus == 0:
                    self.speak_dialog('AlreadyOpen', {'item': item})
                if currentItemStatus == 100:
                    self.speak_dialog('AlreadyClose', {'item': item})
                else:
                    self.speak_dialog('AlreadyAtValue', {
                                      'value': value, 'item': item, 'units_of_measurement': unitOfMeasure})
                return

            # We update shutter to wanted value
            statusCode = self.openhab_client.send_command_to_item(ohItem, value)
            if statusCode == 200 or statusCode == 202:
                if currentItemStatus > value:
                    self.speak_dialog('OpenToValue', {
                                      'value': value, 'item': item, 'units_of_measurement': unitOfMeasure})
                else:
                    self.speak_dialog('CloseToValue', {
                                      'value': value, 'item': item, 'units_of_measurement': unitOfMeasure})
            elif statusCode == 404:
                LOGGER.error(
                    "Some issues with the command execution! Item not found")
                self.speak_dialog('ItemNotFoundError')
            else:
                LOGGER.error("Some issues with the command execution!")
                self.speak_dialog('CommunicationError')
        else:
            LOGGER.error("Item not found!")
            self.speak_dialog('ItemNotFoundError')

    @intent_handler(IntentBuilder("WhatStatus_Intent").require("Status").require("Item"))
    def handle_what_status_intent(self, message):
        messageItem = message.data.get('Item')
        LOGGER.debug("Item: %s" % (messageItem))

        if messageItem == None:
            LOGGER.error("Item not found!")
            self.speak_dialog('ItemNotFoundError')
            return False

        self.currStatusItemsDic = dict()

        unitOfMeasure = self.translate('Percentage')
        self.currStatusItemsDic.update(self.shutterItemsDic)

        ohItem = self.findItemName(self.currStatusItemsDic, messageItem)

        if ohItem != None:
            try:
                state = self.openhab_client.get_current_item_state(ohItem)
                if state == "0":
                    self.speak_dialog('OpenStatus', {'item': messageItem})
                elif state == "100":
                    self.speak_dialog('CloseStatus', {'item': messageItem})
                else:
                    self.speak_dialog('ClosePercentageStatus', {
                                    'item': messageItem, 'value': state, 'units_of_measurement': unitOfMeasure})
            except Exception:
                LOGGER.error("Error retrieving current item state")
                self.speak_dialog('CommunicationError')
        else:
            LOGGER.error("Item not found!")
            self.speak_dialog('ItemNotFoundError')

    def stop(self):
        pass


def create_skill():
    return OpenHabSkill()
