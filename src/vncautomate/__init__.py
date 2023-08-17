#!/usr/bin/python3
# SPDX-FileCopyrightText: 2016-2023 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

import logging
import logging.config
import os
import sys
from types import TracebackType  # noqa: F401
from typing import Optional, Type  # noqa: F401

from vncdotool import api

from .client import VNCAutomateClient, VNCAutomateFactory  # noqa: F401


def init_logger(debug_level="info"):
    # type: (str) -> None
    debug = os.getenv("VNCAUTOMATE_DEBUG", "")
    if debug and os.path.exists(debug):
        if debug.endswith((".ini", ".cfg")):
            logging.config.fileConfig(debug)
        elif debug.endswith((".yaml", ".yml", ".json")):
            import yaml

            with open(debug, "r") as fd:
                conf = yaml.safe_load(fd)

            logging.config.dictConfig(conf)
        else:
            sys.exit("Unknown log configuration %r" % (debug,))

        return

    try:
        level = getattr(logging, debug_level.upper())
    except AttributeError:
        sys.exit("Unknown log level %r" % (debug_level,))

    logging.basicConfig(
        format="%(asctime)s %(levelname)s [%(name)s:%(module)s:%(funcName)s]: %(message)s",
        level=level,
    )


def connect_vnc(host):
    # type: (str) -> VNCAutomateClient
    log = logging.getLogger(__name__)
    log.info("Connecting to VNC host %s", host)
    client = api.connect(host, factory_class=VNCAutomateFactory)
    client.mouseMove(1, 1)
    client.mouseMove(0, 0)
    return client


def disconnect_vnc():
    # type: () -> None
    api.shutdown()


class VNCConnection(object):
    def __init__(self, host, dump_img=None):
        # type: (str, Optional[str]) -> None
        self.host = host

    def reconnect(self):
        # type: () -> VNCAutomateClient
        return connect_vnc(self.host)

    def __enter__(self):
        # type: () -> VNCAutomateClient
        return connect_vnc(self.host)

    def __exit__(self, type, value, traceback):
        # type: (Optional[Type[Exception]], Optional[Exception], Optional[TracebackType]) -> None
        disconnect_vnc()
