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

from __future__ import absolute_import, division

import difflib
import logging
import os
import re
from datetime import datetime
from tempfile import gettempdir
from typing import Iterable, List, Optional, Sequence, Set, Tuple, Union  # noqa: F401

try:
    import lxml.etree as ET
except ImportError:
    import xml.etree.ElementTree as ET  # type: ignore

import numpy as np
from PIL import Image, ImageDraw, ImageOps
from scipy.signal import sepfir2d
from twisted.internet import utils
from twisted.internet.defer import Deferred, gatherResults

from . import segment_line  # type: ignore
from .config import OCRConfig

P2D = Tuple[int, int]
BBox = Tuple[int, int, int, int]

KEEP_TMP = os.getenv("VNCAUTOMATE_TMP", "")


def img_from_np(ar):
    # type: (np.array) -> Image
    return Image.fromarray(ar.round().astype(np.uint8))


def np_from_img(im):
    # type: (Image) -> np.array
    return np.asarray(im, dtype=np.float32)


class _OCRWord(object):
    def __init__(self, word, bbox):
        # type: (str, np.array) -> None
        self.word = word or ""
        self.bbox = bbox

    def resize(self, resize):
        # type: (float) -> None
        self.bbox = self.bbox * resize

    def offset(self, offset):
        # type: (Tuple[int, int]) -> None
        self.bbox = np.concatenate([offset, offset]) + self.bbox

    def fuzzy_match(self, another_string):
        # type: (str) -> float
        assert type(self.word) is type(another_string), (type(self.word), repr(self.word), type(another_string), repr(another_string))
        return difflib.SequenceMatcher(None, self.word.lower(), another_string.lower()).ratio()

    def __str__(self):
        # type: () -> str
        return "%r@%s" % (self.word, self.bbox)

    def __repr__(self):
        # type: () -> str
        return "%s(%r, %r)" % (self.__class__.__name__, self.word, self.bbox)


class OCRAlgorithm(object):
    RE_BBOX = re.compile(r"\bbbox ([0-9]+) ([0-9]+) ([0-9]+) ([0-9]+)\b")

    def __init__(self, *args, **kwargs):
        # type: (*OCRConfig, **str) -> None
        self.log = logging.getLogger(__name__)
        if len(args) == 1 and isinstance(args[0], OCRConfig):
            # OCRConfig instance has been passed as parameter
            self.config = args[0]
        elif kwargs:
            # key-value pairs have been passed as parameter
            self.config = OCRConfig(**kwargs)
        else:
            # nothing has been passed ... use all default values
            self.config = OCRConfig()

    def detect_edges(self, img):
        # type: (Image) -> Tuple[np.array, np.array]
        self.log.debug("Detecting horizontal and vertical edges in screen")
        mat = np_from_img(img)
        gradient_kernel = np.array((0, 1, 0, -1, 0), dtype="float32")
        smoothing_kernel = np.ones(7, dtype="float32")

        vertical_edges = sepfir2d(mat, gradient_kernel, smoothing_kernel) / 7
        vertical_edges_positive = vertical_edges * (vertical_edges > 0)
        vertical_edges_negative = vertical_edges * (vertical_edges < 0)
        vertical_edges = (np.roll(vertical_edges_positive, -1, axis=1) - np.roll(vertical_edges_negative, 1, axis=1)) / 2

        horizontal_edges = sepfir2d(mat, smoothing_kernel, gradient_kernel) / 7
        horizontal_edges_positive = horizontal_edges * (horizontal_edges > 0)
        horizontal_edges_negative = horizontal_edges * (horizontal_edges < 0)
        horizontal_edges = (np.roll(horizontal_edges_positive, -1, axis=0) - np.roll(horizontal_edges_negative, 1, axis=0)) / 2

        if self.config.dump_x_gradients:
            img_from_np(vertical_edges).save(self.config.dump_x_gradients)
        if self.config.dump_y_gradients:
            img_from_np(horizontal_edges).save(self.config.dump_y_gradients)

        return horizontal_edges, vertical_edges

    def segment_line(self, x, y, label, edges, line_segments):
        # type: (int, int, int, np.array, np.array) -> List[P2D]
        # UNUSED in favor of segment_line.pyx
        self.log.debug("Seeding line pixel segmentation at (%s, %s)", x, y)
        line_pixels = []  # type: List[P2D]
        stack = [(x, y)]  # type: List[P2D]
        while stack:
            x, y = stack.pop(0)
            if not (0 <= y < edges.shape[0] and 0 <= x < edges.shape[1]):
                continue
            if line_segments[y, x] >= 0:
                continue
            if edges[y, x] <= self.config.line_segment_low_threshold:
                continue
            # unlabeld edge pixel...
            line_pixels.append((x, y))
            line_segments[y, x] = label

            # add direct neighbor pixels to stack
            stack += [
                (x - 1, y),
                (x + 1, y),
                (x, y - 1),
                (x, y + 1),
            ]

        return line_pixels

    def line_from_pixels(self, pixels):
        # type: (Iterable[P2D]) -> BBox
        # UNUSED in favor of segment_line.pyx
        line_pixels = np.array(pixels)
        mean = line_pixels.mean(0)
        line_min = line_pixels.min(0)
        line_max = line_pixels.max(0)

        variance = line_pixels.var(0)
        covariance = variance[0] / (variance[1] + 0.0000001)  # avoid division by zero
        if 1.0 / self.config.line_segment_min_covariance < covariance < self.config.line_segment_min_covariance:
            # segment is not narrow enough and more blob-like
            raise ValueError("Segment is no line!")

        if variance[0] > variance[1]:
            # horizontal line
            line = (line_min[0], mean[1], line_max[0], mean[1])
            length = line[2] - line[0]
        else:
            # vertical line
            line = (mean[0], line_min[1], mean[0], line_max[1])
            length = line[3] - line[1]

        if length < self.config.line_min_length:
            raise ValueError("Line is too short!")

        return line

    def find_lines(self, edges, line_segments):
        # type: (np.array, np.array) -> List[BBox]
        # UNUSED in favor of segment_line.pyx
        self.log.debug("Detecting line segments in image...")
        lines = []  # type: List[BBox]
        it = np.nditer(edges, flags=["multi_index"])
        for edge in it:
            y, x = it.multi_index
            if edge > self.config.line_segment_high_threshold and line_segments[y, x] < 0:
                try:
                    line_pixels = self.segment_line(x, y, len(lines), edges, line_segments)
                    line = self.line_from_pixels(line_pixels)
                except ValueError as exc:
                    # add dummy line in order to match with the segmentation labels
                    line = (0, 0, 0, 0)
                    self.log.debug("  Ignoring line segment: %s", exc)
                lines.append(line)

        self.log.debug("%s lines have been segmented in total", len(lines))
        return lines

    def match_line_in_neighborhood(self, _x, _y, _label, lines, line_segments):
        # type: (float, float, int, Sequence[BBox], np.array) -> Tuple[Optional[BBox], int]
        _x = int(round(_x))
        _y = int(round(_y))
        matches = set()  # type: Set[int]
        self.log.debug("Find neighboring lines at (%s, %s)", _x, _y)

        def _test_label(x, y):
            # type: (int, int) -> None
            if 0 <= y < line_segments.shape[0] and 0 <= x < line_segments.shape[1]:
                label = line_segments[y, x]
                if 0 <= label != _label:
                    matches.add(label)

        def _dist_square(line):
            # type: (BBox) -> float
            return min(
                (line[0] - _x) ** 2 + (line[1] - _y) ** 2,
                (line[2] - _x) ** 2 + (line[3] - _y) ** 2,
            )

        # ......... ......... ......... 1----->27
        # ......... ......... .1--->27. 5       |
        # ......... ..1->27.. .5     |. |       |
        # ...127... ..5   |.. .|     |. |       |
        # ...508... ..| 0 V.. .|  0  |. |   0   |
        # ...634... ..V   8.. .|     V. |       |
        # ......... ..63->4.. .V     8. |       V
        # ......... ......... .63--->4. V       8
        # ......... ......... ......... 63----->4
        for dist in range(1, 5):
            for x in range(_x - dist, _x + dist):
                # scan above the origin
                _test_label(x, _y - dist)
                # scan below the origin
                _test_label(x + 1, _y + dist)
            for y in range(_y - dist, _y + dist):
                # scan left of the origin
                _test_label(_x - dist, y + 1)
                # scan right of the origin
                _test_label(_x + dist, y)

        # find closest match
        best_match = -1
        best_distance_square = self.config.box_corner_points_max_distance**2  # 10 pixel max distance
        for ilabel in matches:
            line = lines[ilabel]
            dist_square = _dist_square(line)
            self.log.debug("  Line %s matches (squared distance: %s)", ilabel, dist_square)
            if dist_square < best_distance_square:
                best_match = ilabel
                best_distance_square = dist_square

        if best_match >= 0:
            self.log.debug("Best match: line %s, squared distance: %s", best_match, best_distance_square)
            return lines[best_match], best_match
        return None, best_match

    def prune_small_boxes(self, boxes):
        # type: (Sequence[BBox]) -> List[BBox]
        new_boxes = [
            ibox
            for ibox in boxes
            if (ibox[2] - ibox[0]) > self.config.box_min_width and (ibox[3] - ibox[1]) > self.config.box_min_height
        ]
        self.log.debug("Pruning %s boxes that are too small", len(boxes) - len(new_boxes))
        return new_boxes

    def prune_large_boxes(self, boxes):
        # type: (Sequence[BBox]) -> List[BBox]
        new_boxes = [ibox for ibox in boxes if (ibox[3] - ibox[1]) < self.config.box_max_height]
        self.log.debug("Pruning %s boxes that are too large", len(boxes) - len(new_boxes))
        return new_boxes

    def detect_boxes(self, horizontal_lines, vertical_lines, horizontal_line_segments, vertical_line_segments):
        # type: (Sequence[BBox], Sequence[BBox], np.array, np.array) -> List[BBox]
        # iterate over all horizontal lines and try to create
        # a rectangle starting from the top left corner
        self.log.debug("Detecting boxes in image given the detected lines")
        boxes = []  # type: List[BBox]
        for itop, top in enumerate(horizontal_lines):
            left, ileft = self.match_line_in_neighborhood(top[0], top[1], itop, vertical_lines, vertical_line_segments)
            if left is None:
                continue
            bottom, ibottom = self.match_line_in_neighborhood(left[2], left[3], ileft, horizontal_lines, horizontal_line_segments)
            if bottom is None:
                continue
            right, iright = self.match_line_in_neighborhood(top[2], top[3], itop, vertical_lines, vertical_line_segments)
            if right is None:
                continue
            new_box = (left[0], top[1], right[2], bottom[3])
            self.log.debug("  Detected new box %s", new_box)
            boxes.append(new_box)

        self.log.debug("Detected %s box candidates", len(boxes))
        boxes = self.prune_small_boxes(boxes)
        boxes = self.prune_large_boxes(boxes)
        self.log.debug("Detected %s final boxes", len(boxes))
        return boxes

    def draw_lines_and_boxes(self, horizontal_lines, vertical_lines, boxes, size):
        # type: (Iterable[BBox], Iterable[BBox], Iterable[BBox], Tuple[int, int]) -> Image
        self.log.debug("Drawing detected lines and boxes")
        img_result = Image.new("RGB", size, "white")
        draw = ImageDraw.Draw(img_result)
        for line in horizontal_lines:
            draw.line(line, "#00ff00")
        for line in vertical_lines:
            draw.line(line, "#ff0000")
        for box in boxes:
            draw.rectangle(box, outline="#0000ff")
        return img_result

    def get_words_from_hocr(self, xml_data):
        # type: (bytes) -> List[List[_OCRWord]]
        self.log.debug("Parsing words from XML OCR data")
        try:
            xml = ET.fromstring(xml_data, parser=ET.XMLParser())
        except ET.ParseError as err:
            # return an empty list of words to enable continuation
            self.log.warning("XML output from tesseract is malformed: %s", err)
            return []

        words = []  # type: List[List[_OCRWord]]
        for line in xml.findall(".//{http://www.w3.org/1999/xhtml}span[@class='ocr_line']"):
            words_in_line = []
            for word in line:
                # get the bounding box for the word
                title = word.attrib.get("title", "")
                match = self.RE_BBOX.search(title)
                if match:
                    bbox = np.array([int(i) for i in match.groups()])
                else:
                    bbox = np.zeros(4)

                while len(word):
                    # the word might be packed into an HTML tag such as <strong>
                    word = word[0]

                try:
                    _word = _OCRWord(word.text, bbox)
                    words_in_line.append(_word)
                except UnicodeDecodeError as err:
                    self.log.warning("Ignoring wrongly encoded word: %s", err)
            words.append(words_in_line)

        self.log.debug("Found %s words altogether", len(words))
        return words

    def ocr_img(self, _img, box):
        # type: (Image, Optional[BBox]) -> Deferred
        if box:
            self.log.debug("Performing OCR on VNC screen in area %s and with resizing %s", box, self.config.img_resize)
        else:
            self.log.debug("Performing OCR on VNC screen with resizing %s", self.config.img_resize)

        # temporary file for tesseract
        out_file_path = os.path.join(gettempdir(), "vnc_automate_%s" % datetime.now().isoformat())
        hocr_file_path = out_file_path + ".hocr"
        img_file_path = out_file_path + ".tiff"

        img = _img.crop(box) if box else _img
        new_width = int(round(img.width * self.config.img_resize))
        new_height = int(round(img.height * self.config.img_resize))
        img = img.resize((new_width, new_height))
        img.save(img_file_path)

        processDeferred = Deferred()

        def _process_output(val):
            # type: (int) -> None
            # read OCR output from temp file
            with open(hocr_file_path, "rb") as hocr_file:
                hocr_data = hocr_file.read()

            self.log.debug("Read %d bytes from tesseract exited with %d", len(hocr_data), val)

            self.log.debug("Removing %r and %r ...", hocr_file_path, img_file_path)
            if not KEEP_TMP:
                os.unlink(hocr_file_path)
                os.unlink(img_file_path)

            # get the recognized words
            words = self.get_words_from_hocr(hocr_data)
            for line in words:
                for word in line:
                    word.resize(1.0 / self.config.img_resize)
                    if box:
                        word.offset(box[0:2])

            self.log.debug("Detected words: %s", "\n".join(" ".join(iword.word if iword else "" for iword in line) for line in words))
            processDeferred.callback(words)

        cmd = ["/usr/bin/tesseract", img_file_path, out_file_path, "-l", self.config.lang, "hocr"]
        self.log.debug("Running command: %s", " ".join(cmd))
        output = utils.getProcessValue(cmd[0], cmd[1:], os.environ)
        output.addCallback(_process_output)

        return processDeferred

    def mean_point_of_boxes(self, boxes):
        # type: (Iterable[np.array]) -> np.array
        points = []  # type: List[np.array]
        for ibox in boxes:
            points.append(ibox[0:2])
            points.append(ibox[2:4])
        return np.array(points).mean(0).astype(int)

    def boxes_from_image(self, img):
        # type: (Image) -> List[BBox]
        horizontal_edges, vertical_edges = self.detect_edges(img)
        mat_shape = tuple(reversed(img.size))
        vertical_line_segments = -np.ones(mat_shape, dtype="int64")
        vertical_lines = segment_line.find_lines(vertical_edges, vertical_line_segments, self.config)
        # vertical_lines = self.find_lines(vertical_edges, vertical_line_segments)
        horizontal_line_segments = -np.ones(mat_shape, dtype="int64")
        horizontal_lines = segment_line.find_lines(horizontal_edges, horizontal_line_segments, self.config)
        # horizontal_lines = self.find_lines(horizontal_edges, horizontal_line_segments)
        boxes = self.detect_boxes(horizontal_lines, vertical_lines, horizontal_line_segments, vertical_line_segments)

        if self.config.dump_boxes:
            dump_image = self.draw_lines_and_boxes(horizontal_lines, vertical_lines, boxes, img.size)
            dump_image.save(self.config.dump_boxes)

        return boxes

    def find_best_matching_words(self, all_words, pattern):
        # type: (Iterable[Sequence[_OCRWord]], Sequence[str]) -> Tuple[float, Optional[List[_OCRWord]]]
        best_match = (self.config.min_str_match_score, None)  # type: Tuple[float, Optional[List[_OCRWord]]]
        for line in all_words:
            for iword, word in enumerate(line):
                self.log.debug("Matching word: %s", word)
                scores = np.zeros(len(pattern))
                words = []  # type: List[_OCRWord]
                for i, pat in enumerate(pattern):
                    if i + iword >= len(line):
                        break
                    scores[i] = line[iword + i].fuzzy_match(pat)
                    words.append(line[iword + i])

                # compute overall matching score and penalize slightly
                # by coverage of whole line
                self.log.debug("  Matched words: %s", ".".join(str(word) for word in words))
                score = scores.mean()
                penalty = (1.0 * len(pattern)) / len(line)
                final_score = score * (0.9 + penalty * 0.1)
                self.log.debug("  Score: %s * (0.9 + %s * 0.1)  = %s", scores, penalty, final_score)
                match = (final_score, words)
                if match > best_match:
                    self.log.debug("  Found new best match!")
                    best_match = match

        return best_match

    def find_text_in_image(self, img, pattern):
        # type: (Image, Union[str, List[str]]) -> Deferred
        if self.config.dump_dir:
            img_path = os.path.join(self.config.dump_dir, "vnc_automate_%s.png" % datetime.now().isoformat())
            img.save(img_path)

        if self.config.dump_screen:
            img.save(self.config.dump_screen)

        self.log.debug("")
        self.log.debug("==========")
        if not isinstance(pattern, list):
            # make sure that we got a list of strings as pattern
            pattern = pattern.split()
        pattern = [i.lower() for i in pattern]

        # convert image to gray scale
        img = img.convert("L")

        # invert image if predominantly dark
        avrg_value = np.asarray(img).mean(axis=0).mean() / 255
        if avrg_value < 0.5:
            img = ImageOps.invert(img)

        boxes = self.boxes_from_image(img)

        deferreds = [
            self.ocr_img(img, box).addCallback(self.find_best_matching_words, pattern) for box in [None] + boxes  # type: ignore
        ]  # type: List[Deferred]

        def _process_matches(matches):
            # type: (Sequence[Tuple[float, Sequence[_OCRWord]]]) -> Optional[np.array]
            best_match = (self.config.min_str_match_score, None)  # type: Tuple[float, Optional[List[_OCRWord]]]
            for match in matches:
                if match > best_match:
                    best_match = match

            score, matched_words = best_match
            self.log.debug("Search pattern: %s", " ".join(pattern))
            if matched_words:
                self.log.debug("Matched words: %s (score=%s)", " ".join(iword.word for iword in matched_words), score)
                self.log.debug("Matched word objects: %s", matched_words)
                click_point = self.mean_point_of_boxes([iword.bbox for iword in matched_words])
                return click_point
            self.log.debug("No matches found")
            return None

        results_deferred = gatherResults(deferreds)
        results_deferred.addCallback(_process_matches)
        return results_deferred
