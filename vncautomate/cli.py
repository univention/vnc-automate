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

import argparse
import logging
import os

from PIL import Image
from twisted.internet import reactor
from twisted.internet.threads import deferToThread

from . import VNCConnection, init_logger
from .config import OCRConfig
from .ocr import OCRAlgorithm


def add_config_options_to_parser(parser):
	# add all config options from OCRConfig to the parser
	for name in dir(OCRConfig):
		if name.startswith("_"):
			continue
		default = getattr(OCRConfig, name)
		if isinstance(default, (float, int, str)):
			parser.add_argument(
				"--%s" % (name.replace("_", "-")),
				default=default,
				type=type(default),
				help=getattr(OCRConfig, "_" + name),
				metavar="IMG_PATH" if name.startswith("dump_") else name.upper(),
				dest=name,
			)


def get_parser():
	parser = argparse.ArgumentParser(description='Automation tool for VNC sessions using on OCR.')
	parser.add_argument('host', metavar='vnc_host', help='Host with VNC port to connect to (can also be a file for testing purposes)')
	parser.add_argument('words', nargs='+', metavar='word', help='Words that will be matched and clicked upon in the VNC session')
	parser.add_argument('--log', '-l', dest='log', default='info', help='Log level (debug, info, warn, error, critical)', choices=('debug', 'info', 'warn', 'error', 'critial'))
	add_config_options_to_parser(parser)
	return parser


def parse_args():
	# parse arguments and create OCRConfig instance
	parser = get_parser()
	return parser.parse_args()


def get_config_from_args(args):
	return OCRConfig(**args.__dict__)


def main_vnc(host, words, config):
	logging.info('Connecting to VNC host %s', host)
	with VNCConnection(host) as client:
		client.updateOCRConfig(config)
		client.mouseClickOnText(words)


def main_img(img_path, words, config):

	def run_on_img():
		logging.info('Loading image %s', img_path)
		ocr_algo = OCRAlgorithm(config)
		with Image.open(img_path) as img:
			deferred = ocr_algo.find_text_in_image(img, words)
			deferred.addCallback(lambda click_point: logging.info('Final click point: %s', click_point))
			deferred.addBoth(lambda _none: reactor.stop())

	def err_handler(err):
		logging.error(err)

	deferToThread(run_on_img).addErrback(err_handler)
	reactor.run()


if __name__ == '__main__':
	args = parse_args()
	config = get_config_from_args(args)
	words = ' '.join(args.words)
	init_logger(args.log)

	if os.path.exists(args.host):
		main_img(args.host, words, config)
	else:
		main_vnc(args.host, words, config)
