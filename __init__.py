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

import requests
import json

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

class openHABSkill(MycroftSkill):

	def __init__(self):
		super(openHABSkill, self).__init__(name="openHABSkill")

		self.command_headers = {"Content-type": "text/plain"}

		self.polling_headers = {"Accept": "application/json"}

		self.url = None
		self.shutterItemsDic = dict()

	def initialize(self):
		supported_languages = ["en-us", "it-it", "de-de", "es-es", "fr-fr"]

		if self.lang not in supported_languages:
			self.log.warning("Unsupported language for " + self.name + ", shutting down skill.")
			self.shutdown()

		self.handle_websettings_update()
		
		if self.url is not None:
			self.getTaggedItems()
		else:
			self.speak_dialog('ConfigurationNeeded')

		# Using Padatious for what status intent
		self.register_entity_file('item.entity')
		self.register_intent_file('what.status.intent', self.handle_what_status_intent)

		self.settings_change_callback = self.handle_websettings_update

	def get_config(self, key):
		return (self.settings.get(key) or self.config_core.get('openHABSkill', {}).get(key))

	def handle_websettings_update(self):
		if self.get_config('host') is not None and self.get_config('port') is not None:
			self.url = "http://%s:%s/rest" % (self.get_config('host'), self.get_config('port'))
			self.getTaggedItems()
		else:
			self.url = None

	def getTaggedItems(self):
		#find all the items tagged from openHAB.
		#supported tags: Lighting, Switchable, CurrentTemperature, Shutter...
		#the labeled items are stored in dictionaries

		self.shutterItemsDic = {}

		if self.url == None:
			LOGGER.error("Configuration needed!")
			self.speak_dialog('ConfigurationNeeded')
		else:			
			requestUrl = self.url+"/items?recursive=false"

			try: 
				req = requests.get(requestUrl, headers=self.polling_headers)
				if req.status_code == 200:
					json_response = req.json()
					for x in range(0,len(json_response)):
						if ("Shutter" in json_response[x]['tags']):
							self.shutterItemsDic.update({json_response[x]['name']: json_response[x]['label']})
						else:
							pass
				else:
					LOGGER.error("Some issues with the command execution!")
					self.speak_dialog('GetItemsListError')

			except KeyError:
						pass
			except Exception:
					LOGGER.error("Some issues with the command execution!")
					self.speak_dialog('GetItemsListError')

	def findItemName(self, itemDictionary, messageItem):

		bestScore = 0
		score = 0
		bestItem = None

		try:
			for itemName, itemLabel in list(itemDictionary.items()):
				score = fuzz.ratio(messageItem, itemLabel, score_cutoff=bestScore)
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
		#to refresh the openHAB items labeled list we use an intent, we can ask Mycroft to make the refresh

		self.getTaggedItems()
		dictLenght =len(self.shutterItemsDic)
		self.speak_dialog('RefreshTaggedItems', {'number_item': dictLenght})

	@intent_handler(IntentBuilder("OpenClose_CommandIntent").require("Command").require("Item"))
	def handle_openclose_command_intent(self, message):
		command = message.data.get('Command')
		messageItem = message.data.get('Item')

		ohCommand = command
		if self.voc_match(command, 'Close'):
			ohCommand = "down"
		elif self.voc_match(command, 'Open'):
			ohCommand = "up"

		ohItem = self.findItemName(self.shutterItemsDic, messageItem)

		if ohItem != None:
			statusCode = self.sendCommandToItem(ohItem, ohCommand.upper())
			if statusCode == 200:
				self.speak_dialog('OpenClose', {'command': command, 'item': messageItem})
			elif statusCode == 404:
				LOGGER.error("Some issues with the command execution!. Item not found")
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
			state = self.getCurrentItemStatus(ohItem)
			if state == 0:
				self.speak_dialog('OpenStatus', {'item': messageItem})
			elif state == 100:
				self.speak_dialog('CloseStatus', {'item': messageItem})
			else:
				self.speak_dialog('ClosePercentageStatus', {'item': messageItem, 'value': state, 'units_of_measurement': unitOfMeasure})
			return True
		else:
			LOGGER.error("Item not found!")
			self.speak_dialog('ItemNotFoundError')
			return False

	def sendStatusToItem(self, ohItem, command):
		requestUrl = self.url+"/items/%s/state" % (ohItem)
		req = requests.put(requestUrl, data=command, headers=self.command_headers)

		return req.status_code

	def sendCommandToItem(self, ohItem, command):
		requestUrl = self.url+"/items/%s" % (ohItem)
		req = requests.post(requestUrl, data=command, headers=self.command_headers)

		return req.status_code

	def getCurrentItemStatus(self, ohItem):
		requestUrl = self.url+"/items/%s/state" % (ohItem)
		state = None

		try:
			req = requests.get(requestUrl, headers=self.command_headers)

			if req.status_code == 200:
				state = req.text
			else:
				LOGGER.error("Some issues with the command execution!")
				self.speak_dialog('CommunicationError')

		except KeyError:
			pass

		return state

	def stop(self):
		pass

def create_skill():
    return openHABSkill()
