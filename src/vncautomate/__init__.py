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
