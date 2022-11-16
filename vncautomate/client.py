#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# Python VNC automate
#
# Copyright 2016-2022 Univention GmbH
#
# https://www.univention.de/
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

from .config import OCRConfig
from .ocr import OCRAlgorithm, np_from_img
from PIL import Image
from scipy import ndimage
from scipy import signal
from time import time
from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.internet.task import deferLater
from vncdotool.client import VNCDoToolClient
from time import sleep
import logging


class VNCAutomateException(ValueError):
	pass


class VNCAutomateClient(VNCDoToolClient):

	ocr_algo = None

	def __init__(self):
		VNCDoToolClient.__init__(self)
		self.ocr_algo = OCRAlgorithm()
		self.log = logging.getLogger(__name__)

	def updateOCRConfig(self, *args, **kwargs):
		if len(args) == 1 and isinstance(args[0], OCRConfig):
			# OCRConfig instance has been passed as parameter
			self.ocr_algo.config = args[0]
		elif kwargs:
			# a key-value pairs have been passed as parameter
			self.ocr_algo.config.update(kwargs)
		return self

	def updateRectangle(self, *args):
		self.log.debug('Frame buffer update for region %s', args[:4])
		VNCDoToolClient.updateRectangle(self, *args)

	def saveScreenshot(self, path):
		self.framebufferUpdateRequest()
		self.ocr_algo.save_image(self.screen, path)
		return self

	def _find_text(self, text, timeout=-1, defer=1e-2, start_time=-1, prevent_screen_saver=False):
		if start_time < 0:
			start_time = time()

		def _check_timeout(click_point):
			duration = time() - start_time
			if click_point is not None:
				# done, we found the text :)
				self.log.info('Found %r [%.1f sec]', text, duration)
				return click_point
			else:
				# check timeout
				self.log.debug('Not found %r [%.1f sec]', text, duration)
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

	def findSubimage(self, subimage_path, timeout=30, defer=1e-2, start_time=-1, min_match=0.9):
		self.log.info('findSubimage("%s", timeout=%.1f, min_match=%.2f)', subimage_path, timeout, min_match)

		subimage = Image.open(subimage_path)
		if start_time < 0:
			start_time = time()

		def _check_timeout(match_value, pos):
			self.log.info('_check_timeout: %s %s', match_value, pos)
			duration = time() - start_time
			if match_value >= min_match:
				# Pattern found
				self.log.info('Search pattern found, with a match value of %.2f/1.00 [%.1f sec]', match_value, duration)
				return match_value, pos
			else:
				# check timeout
				self.log.info('No match for search pattern; match value was %.2f<%.2f [%.1f sec]', match_value, min_match, duration)
				if timeout > 0 and duration >= timeout:
					raise VNCAutomateException('Search for sub-image "%s" in VNC screen timed out after %.1f seconds!' % (subimage_path, duration))
				# Return None to try again
				return None

		self.framebufferUpdateRequest()
		self.deferred = Deferred()
		self.deferred.addCallback(lambda _none: deferLater(reactor, defer, lambda: None))
		self.deferred.addCallback(lambda _none: self.image_match_value(self.screen, subimage))
		self.deferred.addCallback(lambda result: _check_timeout(result[0], result[1]))
		self.deferred.addCallback(lambda result: self.findSubimage(subimage_path, timeout=timeout, defer=1e-2, start_time=start_time, min_match=min_match) if result is None else result)
		return self.deferred

	# Returns a value from 0 to 1, where 1 means the subimg is a pixel-perfect
	# part of the img. Also returns the position of the match in img.
	def image_match_value(self, img, subimg):
		img = img.convert('L')
		subimg = subimg.convert('L')

		img = np_from_img(img)
		subimg = np_from_img(subimg)

		img = ndimage.sobel(img, axis=0) + ndimage.sobel(img, axis=1)
		subimg = ndimage.sobel(subimg, axis=0) + ndimage.sobel(subimg, axis=1)

		match_maxtrix = signal.fftconvolve(img, subimg[::-1, ::-1], mode='same')
		normalized_match_matrix = match_maxtrix / (subimg * subimg).sum()
		best_match_value = normalized_match_matrix.max()

		best_match_x = normalized_match_matrix.argmax() % normalized_match_matrix.shape[1]
		best_match_y = normalized_match_matrix.argmax() / normalized_match_matrix.shape[1]

		self.log.info('image_match_value: %s %s %s', best_match_value, best_match_x, best_match_y)
		return best_match_value, (best_match_x, best_match_y)

	def mouseMoveToText(self, text, timeout=30, defer=1e-2, log=True):
		if log:
			self.log.info('mouseMoveToText("%s", timeout=%.1f, defer=%.2f)', text, timeout, defer)
		deferred = self._find_text(text, defer=defer, timeout=timeout)
		deferred.addCallback(lambda pos: self.mouseMove(*pos))
		return deferred

	def mouseClickOnText(self, text, timeout=30, defer=1e-2):
		self.log.info('mouseClickOnText("%s", timeout=%.1f, defer=%.2f)', text, timeout, defer)
		deferred = self.mouseMoveToText(text, timeout=timeout, defer=defer, log=False)
		deferred.addCallback(lambda _client: deferLater(reactor, 0.1, self.mousePress, 1))
		deferred.addCallback(lambda _client: deferLater(reactor, 0.1, self.mouseMove, 0, 0))
		return deferred

	def waitForText(self, text, timeout=30, defer=1e-2, prevent_screen_saver=False):
		self.log.info('waitForText("%s", timeout=%.1f, defer=%.2f)', text, timeout, defer)
		deferred = self._find_text(text, timeout=timeout, defer=defer, prevent_screen_saver=prevent_screen_saver)
		deferred.addCallback(lambda _pos: self)  # make sure to return self
		return deferred

	def enterKeys(self, keys, log=True):
		if log:
			self.log.info('enterKeys(%r)', keys)
		if not keys:
			return self

		ikey = {
			" ": "space",
			"\t": "tab",
			"\n": "enter",
		}.get(keys[0], keys[0])
		sleep(0.5)
		self.keyPress(ikey)
		return deferLater(reactor, 0.1, self.enterKeys, keys[1:], log=False)

	def enterText(self, text):
		self.log.info('enterText(%r)', text)
		return self.enterKeys(text, log=False)
