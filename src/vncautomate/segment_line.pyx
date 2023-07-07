# distutils: language = c++
#cython: language_level=3
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


import logging

import numpy as np

cimport numpy as np
from libcpp.vector cimport vector

FLOAT = np.float32
ctypedef np.float32_t FLOAT_t
INT = np.int64
ctypedef np.int64_t INT_t


cdef void segment_line(int _x, int _y, int label, np.ndarray[FLOAT_t, ndim=2] edges, np.ndarray[INT_t, ndim=2] line_segments, FLOAT_t line_segment_low_threshold, vector[int] &stack, vector[FLOAT_t] &line_pixels):
    assert edges.dtype == FLOAT and line_segments.dtype == INT
    line_pixels.clear()
    stack.clear()
    stack.push_back(_x)
    stack.push_back(_y)
    cdef int x, y
    while stack.size():
        y = stack.back()
        stack.pop_back()
        x = stack.back()
        stack.pop_back()
        if x < 0 or y < 0 or x >= edges.shape[1] or y >= edges.shape[0]:
            # pixel is not in image anymore
            continue

        if edges[y, x] > line_segment_low_threshold and line_segments[y, x] < 0:
            # unlabeld edge pixel...
            line_pixels.push_back(x)
            line_pixels.push_back(y)
            line_segments[y, x] = label

            # add direct neighbor pixels to stack
            stack.push_back(x - 1)
            stack.push_back(y)
            stack.push_back(x + 1)
            stack.push_back(y)
            stack.push_back(x)
            stack.push_back(y - 1)
            stack.push_back(x)
            stack.push_back(y + 1)


cdef void line_from_pixels(vector[FLOAT_t] &_line_pixels, FLOAT_t line_segment_min_covariance, FLOAT_t line_min_length, vector[FLOAT_t] &line):
    log = logging.getLogger(__name__)
    cdef int i
    if _line_pixels.size() == 0:
        for i in range(4): line[i] = 0
        return

    line_pixels = np.array(_line_pixels, dtype=FLOAT)
    line_pixels = line_pixels.reshape((_line_pixels.size() / 2, 2))
    cdef np.ndarray[FLOAT_t, ndim=1] mean = line_pixels.mean(0)
    cdef np.ndarray[FLOAT_t, ndim=1] line_min = line_pixels.min(0)
    cdef np.ndarray[FLOAT_t, ndim=1] line_max = line_pixels.max(0)
    cdef np.ndarray[FLOAT_t, ndim=1] variance = line_pixels.var(0)
    cdef FLOAT_t covariance = variance[0] / (variance[1] + 0.0000001)  # avoid division by zero
    if 1.0 / line_segment_min_covariance < covariance < line_segment_min_covariance:
        # segment is not narrow enough and more blob-like
        log.debug('  Ignoring line segment: Segment is no line!')
        for i in range(4): line[i] = 0
        return

    cdef FLOAT_t length
    if variance[0] > variance[1]:
        # horizontal line
        line[0] = line_min[0]
        line[1] = mean[1]
        line[2] = line_max[0]
        line[3] = mean[1]
        length = line[2] - line[0]
    else:
        # vertical line
        line[0] = mean[0]
        line[1] = line_min[1]
        line[2] = mean[0]
        line[3] = line_max[1]
        length = line[3] - line[1]

    if length < line_min_length:
        log.debug('  Ignoring line segment: Line is too short')
        for i in range(4): line[i] = 0


def find_lines(np.ndarray[FLOAT_t, ndim=2] edges not None, np.ndarray[INT_t, ndim=2] line_segments not None, config):
    log = logging.getLogger(__name__)
    log.debug('Detecting line segments in image...')
    cdef vector[FLOAT_t] _lines  # [line1_min_x, line1_min_y, line1_max_x, line1_max_y, line2_min_x, ...]
    cdef vector[FLOAT_t] line_pixels  # [x1, y1, x2, y2, x3, ...]
    cdef vector[int] pixel_stack  # [x1, y1, x2, y2, x3, ...]
    cdef vector[FLOAT_t] line = (0, 0, 0, 0)  # [min_x, min_y, max_x, max_y]
    cdef int x, y, i
    for y in range(edges.shape[0]):
        for x in range(edges.shape[1]):
            if edges[y, x] > config.line_segment_high_threshold and line_segments[y, x] < 0:
                segment_line(x, y, _lines.size() / 4, edges, line_segments, config.line_segment_low_threshold, pixel_stack, line_pixels)
                line_from_pixels(line_pixels, config.line_segment_min_covariance, config.line_min_length, line)

                for i in range(4):
                    _lines.push_back(line[i])

    log.debug('%s lines have been segmented in total', len(_lines) / 4)

    # convert lines to 2d structure
    lines = np.array(_lines)
    lines = lines.reshape((_lines.size() / 4, 4))

    return lines
