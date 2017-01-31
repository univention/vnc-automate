#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# Python VNC automate
#
# Copyright 2016 Univention GmbH
#
# http://www.univention.de/
#
# All rights reserved.
#
# The source code of this program is made available
# under the terms of the GNU Affero General Public License version 3
# (GNU AGPL V3) as published by the Free Software Foundation.
#
# Binary versions of this program provided by Univention to you as
# well as other copyrighted, protected or trademarked materials like
# Logos, graphics, fonts, specific documentations and configurations,
# cryptographic keys etc. are subject to a license agreement between
# you and Univention and not subject to the GNU AGPL V3.
#
# In the case you use this program under the terms of the GNU AGPL V3,
# the program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License with the Debian GNU/Linux or Univention distribution in file
# /usr/share/common-licenses/AGPL-3; if not, see
# <http://www.gnu.org/licenses/>.
#

import logging
from time import time
from vncdotool.client import VNCDoToolClient
from vncdotool.rfb import RAW_ENCODING, PSEUDO_DESKTOP_SIZE_ENCODING
from twisted.internet.defer import Deferred
from twisted.internet.task import deferLater
from twisted.internet import reactor
from .config import OCRConfig
from .ocr import OCRAlgorithm


class VNCAutomateException(ValueError):
	pass


class VNCAutomateClient(VNCDoToolClient):

	ocr_algo = None

	def __init__(self):
		VNCDoToolClient.__init__(self)
		self.ocr_algo = OCRAlgorithm()

	def vncConnectionMade(self):
		VNCDoToolClient.vncConnectionMade(self)
		# TODO: Other (better) encodings could possibly be used here. To avoid
		# problems I'm gonna stick with RAW_ENCODING for now.
		self.setEncodings([RAW_ENCODING, PSEUDO_DESKTOP_SIZE_ENCODING])

	def updateOCRConfig(self, *args, **kwargs):
		if len(args) == 1 and isinstance(args[0], OCRConfig):
			# OCRConfig instance has been passed as parameter
			self.ocr_algo.config = args[0]
		elif kwargs:
			# a key-value pairs have been passed as parameter
			self.ocr_algo.config.update(kwargs)
		return self

	def updateRectangle(self, *args):
		logging.debug('Frame buffer update for region %s' % (args[:4], ))
		VNCDoToolClient.updateRectangle(self, *args)

	def foo(self):
		self.framebufferUpdateRequest()
		self.deferred = Deferred()
		return self.deferred

	def _find_text(self, text, timeout=-1, defer=1e-2, start_time=-1, prevent_screen_saver=False):
		if start_time < 0:
			start_time = time()

		def _check_timeout(click_point):
			duration = time() - start_time
			if click_point is not None:
				# done, we found the text :)
				logging.info('Search pattern found [%.1f sec]', duration)
				return click_point
			else:
				# check timeout
				logging.info('No match for search pattern [%.1f sec]', duration)
				if prevent_screen_saver:
					self.keyPress('ctrl')
				if timeout > 0 and duration >= timeout:
					raise VNCAutomateException('Search for string "%s" in VNC screen timed out after %.1f seconds!' % (text, duration))

				# ... and return None to try again
				return None

		self.framebufferUpdateRequest()
		self.deferred = Deferred()
		self.deferred.addCallback(lambda _none: deferLater(reactor, defer, lambda: None))
		self.deferred.addCallback(lambda _none: self.ocr_algo.find_text_in_image(self.screen, text))
		self.deferred.addCallback(lambda _click_point: _check_timeout(_click_point))
		self.deferred.addCallback(lambda result: self._find_text(text, timeout=timeout, defer=1e-2, start_time=start_time) if result is None else result)
		return self.deferred

	def mouseMoveToText(self, text, timeout=30, defer=1e-2, log=True):
		if log:
			logging.info('mouseMoveToText("%s", timeout=%.1f, defer=%.2f)', text, timeout, defer)
		deferred = self._find_text(text, defer=defer, timeout=timeout)
		deferred.addCallback(lambda pos: self.mouseMove(*pos))
		return deferred

	def mouseClickOnText(self, text, timeout=30, defer=1e-2):
		logging.info('mouseClickOnText("%s", timeout=%.1f, defer=%.2f)', text, timeout, defer)
		deferred = self.mouseMoveToText(text, timeout=timeout, defer=defer, log=False)
		deferred.addCallback(lambda _client: deferLater(reactor, 0.1, self.mousePress, 1))
		deferred.addCallback(lambda _client: deferLater(reactor, 0.1, self.mouseMove, 0, 0))
		return deferred

	def waitForText(self, text, timeout=30, defer=1e-2, prevent_screen_saver=False):
		logging.info('waitForText("%s", timeout=%.1f, defer=%.2f)', text, timeout, defer)
		deferred = self._find_text(text, timeout=timeout, defer=defer, prevent_screen_saver=prevent_screen_saver)
		deferred.addCallback(lambda _pos: self)  # make sure to return self
		return deferred

	def enterKeys(self, keys, log=True):
		if log:
			logging.info('enterKeys(%s)', keys)
		if len(keys):
			ikey = keys[0]
			ikey = {
				' ': 'space'
			}.get(ikey, ikey)
			self.keyPress(ikey)
			return deferLater(reactor, 0.1, self.enterKeys, keys[1:], log=False)
		return self

	def enterText(self, text):
		logging.info('enterText("%s")', text)
		return self.enterKeys(text, log=False)
