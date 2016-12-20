# coding: utf-8
import logging
from PIL import Image
import numpy as np
from vncocrclient import OCRAlgorithm, OCRConfig, init_logger
import pyximportcpp
import segment_line


def np_from_img(im):
	return np.asarray(im, dtype=np.float32)


init_logger('info')
for img_path in ('xgrad.png', 'ygrad.png'):
	logging.info('==== Testing %s ====', img_path)
	img = Image.open(img_path)
	img = img.convert('L')
	mat_shape = tuple(reversed(img.size))
	mat = np_from_img(img)
	algo = OCRAlgorithm()
	labels_old = -np.ones(mat_shape, dtype='int64')
	lines_old = algo.find_lines(mat, labels_old)
	logging.info('Second round with cython')
	labels_new = -np.ones(mat_shape, dtype='int64')
	lines_new = segment_line.find_lines(mat, labels_new, OCRConfig())

	assert (labels_old == labels_new).all()
	assert len(lines_old) == len(lines_new)
	for i in range(len(lines_new)):
		iline = lines_old[i]
		jline = lines_new[i]
		equal = (jline == jline).all()
		if not equal:
			print('[%s]: %s != %s' % (i, iline, jline))
		assert equal
