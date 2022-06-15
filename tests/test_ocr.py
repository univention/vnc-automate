# coding: utf-8
from __future__ import absolute_import

from os.path import dirname, join

import numpy as np
from numpy.testing import assert_allclose
from PIL import Image
from twisted.trial import unittest

from vncautomate.config import OCRConfig
from vncautomate.ocr import OCRAlgorithm


class TestOcr(unittest.TestCase):

	def _ocr(self, image, text, where):
		config = OCRConfig()
		algo = OCRAlgorithm(config)
		img = Image.open(join(dirname(__file__), image))
		deferred = algo.find_text_in_image(img, text)
		deferred.addCallback(lambda cp: assert_allclose(cp, np.array(where), atol=.5))
		return deferred

	def test_username(self):
		return self._ocr("login.png", "Username", (80.5, 225.))

	def test_password(self):
		return self._ocr("login.png", "Password", (78.5, 275.5))

	def test_login(self):
		return self._ocr("login.png", "LOGIN", (278.5, 337.))


if __name__ == '__main__':
	unittest.main()
