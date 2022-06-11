# coding: utf-8
from __future__ import absolute_import

import logging
import unittest
from os.path import dirname, join

import numpy as np
from PIL import Image

from vncautomate import init_logger, segment_line  # type: ignore
from vncautomate.config import OCRConfig
from vncautomate.ocr import OCRAlgorithm


def np_from_img(im):
	return np.asarray(im, dtype=np.float32)


class TestCython(unittest.TestCase):

	def setup(self):
		init_logger('info')

	def test_xgrad(self):
		self._compare('xgrad.png')

	def test_ygrad(self):
		self._compare('ygrad.png')

	def _compare(self, img_name):
		logging.info('==== Testing %s ====', img_name)

		img_path = join(dirname(__file__), img_name)
		with Image.open(img_path) as img:
			img = img.convert('L')

		mat_shape = tuple(reversed(img.size))
		mat = np_from_img(img)

		algo = OCRAlgorithm()
		labels_old = -np.ones(mat_shape, dtype='int64')
		lines_old = algo.find_lines(mat, labels_old)

		logging.info('Second round with cython')
		labels_new = -np.ones(mat_shape, dtype='int64')
		lines_new = segment_line.find_lines(mat, labels_new, OCRConfig())

		self.assertTrue((labels_old == labels_new).all())
		self.assertEqual(len(lines_old), len(lines_new))
		for i, (iline, jline) in enumerate(zip(lines_old, lines_new)):
			equal = (jline == jline).all()
			self.assertTrue(equal, '[%s]: %s != %s' % (i, iline, jline))


if __name__ == '__main__':
	unittest.main()
