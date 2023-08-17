#!/usr/bin/python3
# SPDX-FileCopyrightText: 2016-2023 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

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
        deferred.addBoth(lambda _: self)  # clear VNCAutomateException and prepare next vncdotool.client.deferred
        return deferred

    def waitForText(self, text, timeout=30, wait=True, result=None):
        # type: (str, int, bool, Optional[List[Tuple[int, int]]]) -> Deferred
        self.log.info('waitForText("%s", timeout=%.1f)', text, timeout)
        deferred = self._find_text(text, timeout=timeout, wait=wait)
        if result is not None:
            deferred.addCallback(lambda pos: result.append(pos))
        deferred.addBoth(lambda _: self)  # clear VNCAutomateException and prepare next vncdotool.client.deferred
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
