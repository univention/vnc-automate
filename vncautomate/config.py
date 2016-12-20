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

import inspect


class OCRConfigAttribute(object):

	def __init__(self, type=str, help='', default=None):
		self.type = type
		self.__doc__ = help
		self.default = default


class OCRConfig(object):

	lang = OCRConfigAttribute(default='eng', help='Specifies the language seen on the screen 3-character ISO 639-2 language code (eng, deu, fra ...)')
	dump_boxes = OCRConfigAttribute(help='Dumps the image of detected lines and boxes in the VNC image to the given path')
	dump_screen = OCRConfigAttribute(help='Dumps the captured VNC screen to the given path')
	dump_x_gradients = OCRConfigAttribute(help='Dumps the computed gradients on the x-axis')
	dump_y_gradients = OCRConfigAttribute(help='Dumps the computed gradients on the y-ayis')
	dump_dir = OCRConfigAttribute(help='Dump every analyzed screen into the given directory')
	img_resize = OCRConfigAttribute(type=float, default=2.0, help='Resize factor for image to improve OCR results')
	box_max_height = OCRConfigAttribute(type=int, default=200, help='Specifies the maximum height a detect box can have')
	box_min_height = OCRConfigAttribute(type=int, default=15, help='Specifies the minimum height a detect box must have')
	box_min_width = OCRConfigAttribute(type=int, default=40, help='Specifies the minimum width a detect box must have')
	box_corner_points_max_distance = OCRConfigAttribute(type=float, default=10, help='Maximum distance of the end points of two lines for being detected as box corner')
	line_min_length = OCRConfigAttribute(type=int, default=15, help='Specifies the minimum length a detected line must have')
	line_segment_min_covariance = OCRConfigAttribute(type=int, default=5, help='Specifies the minimum convariance value line segments must have on order to be detected as line')
	line_segment_low_threshold = OCRConfigAttribute(type=float, default=20, help='Minimum absolute gradient value for pixels to be included into the line segment')
	line_segment_high_threshold = OCRConfigAttribute(type=float, default=20, help='Minimum absolute gradient value for pixels to initiate a line segmentation')
	min_str_match_score = OCRConfigAttribute(type=float, default=0.7, help='Specifies the minimum score a words sequence match needs to have')

	def __init__(self, **kwargs):
		for name, member in self.get_attrs():
			setattr(self, name, kwargs.get(name, member.default))

	@classmethod
	def get_attrs(cls):
		return inspect.getmembers(cls, lambda m: issubclass(type(m), OCRConfigAttribute))

	def update(self, **kwargs):
		for name, member in self.get_attrs():
			if name in kwargs:
				setattr(self, name, kwargs[name])
