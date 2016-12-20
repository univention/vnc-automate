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
import sys
from vncdotool import api
from vncdotool.client import VNCDoToolFactory
from .client import VNCAutomateClient


# force vncdotool to use the VNCAutomateClient class
VNCDoToolFactory.protocol = VNCAutomateClient


def init_logger(debug_level='info'):
	try:
		# adjust logging config
		logging.basicConfig(
			format='%(asctime)s.%(msecs)03d %(levelname)s [%(name)s:%(module)s:%(funcName)s]: %(message)s',
			datefmt='%Y-%m-%d %H:%M:%S',
		)
		logging.getLogger().setLevel(getattr(logging, debug_level.upper()))
	except AttributeError:
		logger.error('Given log level "%s" is unknown', debug_level)
		sys.exit(1)


def connect_vnc(host):
	logging.info('Connecting to VNC host %s', host)
	client = api.connect(host)
	client.mouseMove(1, 1)
	client.mouseMove(0, 0)
	return client


def disconnect_vnc():
	api.shutdown()


class VNCConnection(object):

	def __init__(self, host, dump_img=None):
		self.host = host

	def reconnect(self):
		return connect_vnc(self.host)

	def __enter__(self):
		return connect_vnc(self.host)

	def __exit__(self, type, value, traceback):
		disconnect_vnc()
