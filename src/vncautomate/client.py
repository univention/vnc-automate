#!/usr/bin/python3
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

from __future__ import division

import logging
from time import time
from typing import List, Optional, Sequence, Tuple, Union  # noqa: F401

from twisted.internet import reactor
from twisted.internet.defer import Deferred  # noqa: F401
from twisted.internet.task import deferLater
from vncdotool.client import VNCDoException, VNCDoToolClient, VNCDoToolFactory

from .config import OCRConfig
from .ocr import OCRAlgorithm

__all__ = [
    "VNCAutomateException",
    "VNCAutomateClient",
    "VNCAutomateFactory",
]


class VNCAutomateException(VNCDoException):
    pass


class State(object):
    HISTORY = 5

    def __init__(self):
        # type: () -> None
        self.start_time = time()
        self.seen = []  # type: List[int]
        self.last = 0

    def __str__(self):
        # type: () -> str
        return "State(%r, last=%d)" % (self.seen, self.last)

    def stable(self, key):
        # type: (int) -> bool
        """
        >>> s = State()
        >>> s.stable(1)
        False
        >>> s.stable(1)
        True
        >>> s.stable(1)
        False
        >>> s = State()
        >>> s.stable(1)
        False
        >>> s.stable(2)
        False
        >>> s.stable(1)
        True
        """
        if key in self.seen:
            if key != self.last:
                self.last = key
                return True
        else:
            self.seen.append(key)
            del self.seen[: -self.HISTORY]
        return False

    def duration(self):
        return time() - self.start_time


class VNCAutomateClient(VNCDoToolClient):
    PERIOD = 2.0  # delay between tries

    def __init__(self):
        # type: () -> None
        VNCDoToolClient.__init__(self)
        self.ocr_algo = OCRAlgorithm()
        self.log = logging.getLogger(__name__)

    def updateOCRConfig(self, *args, **kwargs):
        # type: (*OCRConfig, **str) -> VNCAutomateClient
        if len(args) == 1 and isinstance(args[0], OCRConfig):
            # OCRConfig instance has been passed as parameter
            self.ocr_algo.config = args[0]
        elif kwargs:
            # key-value pairs have been passed as parameter
            self.ocr_algo.config.update(**kwargs)
        return self

    def _find_text(self, text, timeout=0, wait=True, _state=None):
        # type: (str, int, bool, Optional[State]) -> Deferred
        state = _state or State()

        def _run_ocr(_):
            # type: (None) -> Union[Tuple[int, int], Deferred]
            if not self.screen.getbbox():
                self.keyPress("ctrl")
                return again()

            key = hash(self.screen.tobytes())
            if wait and not state.stable(key):
                self.log.debug("Unchanged screen %s", state)
                return again()

            return self.ocr_algo.find_text_in_image(self.screen, text).addCallback(_check_result)

        def _check_result(click_point):
            # type: (Optional[Tuple[int, int]]) -> Union[Tuple[int, int], Deferred]
            if click_point is not None:
                self.log.info("Found %r [%.1f sec]", text, state.duration())
                return click_point

            return again()

        def again():
            # type: () -> Deferred
            duration = state.duration()
            self.log.debug("Not found %r [%.1f sec]", text, duration)
            if 0 < abs(timeout) <= duration:
                raise VNCAutomateException("Search for string %r in VNC screen timed out after %.1f seconds!" % (text, duration))

            return deferLater(
                reactor,
                self.PERIOD,
                self._find_text,
                text,
                timeout=timeout,
                wait=wait,
                _state=state,
            )

        return self.refreshScreen().addCallback(_run_ocr)

    def mouseClickOnText(self, text, timeout=30):
        # type: (str, int) -> Deferred
        self.log.info('mouseClickOnText("%s", timeout=%.1f)', text, timeout)
        deferred = self._find_text(text).addTimeout(timeout, reactor)
        deferred.addCallback(lambda pos: self.mouseMove(*pos))
        deferred.addCallback(lambda _client: deferLater(reactor, 0.1, self.mousePress, 1))
        deferred.addCallback(lambda _client: deferLater(reactor, 0.1, self.mouseMove, 0, 0))
        return deferred

    def waitForText(self, text, timeout=30, wait=True):
        # type: (str, int, bool) -> Deferred
        self.log.info('waitForText("%s", timeout=%.1f)', text, timeout)
        deferred = self._find_text(text, timeout=timeout, wait=wait)
        deferred.addCallback(lambda _pos: self)  # make sure to return self
        return deferred

    def enterKeys(self, keys, log=True):
        # type: (Sequence[str], bool) -> VNCAutomateClient
        if log:
            self.log.info("enterKeys(%r)", keys)
        if not keys:
            return self

        ikey = {
            " ": "space",
            "\t": "tab",
            "\n": "enter",
        }.get(keys[0], keys[0])
        self.keyPress(ikey)
        return deferLater(reactor, 0.1, self.enterKeys, keys[1:], log=False)

    def enterText(self, text):
        # type: (str) -> VNCAutomateClient
        self.log.info("enterText(%r)", text)
        return self.enterKeys(text, log=False)


class VNCAutomateFactory(VNCDoToolFactory):
    protocol = VNCAutomateClient
