#!/usr/bin/python3
# SPDX-FileCopyrightText: 2016-2023 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

import argparse
import logging
import os
from typing import Optional, Sequence  # noqa: F401

from PIL import Image
from twisted.internet import reactor

from . import VNCConnection, init_logger
from .config import OCRConfig
from .ocr import OCRAlgorithm


def add_config_options_to_parser(parser):
    # type: (argparse.ArgumentParser) -> None
    # add all config options from OCRConfig to the parser
    for name in dir(OCRConfig):
        if name.startswith("_"):
            continue
        default = getattr(OCRConfig, name)
        if isinstance(default, (float, int, str)):
            parser.add_argument(
                "--%s" % (name.replace("_", "-")),
                default=default,
                type=type(default),
                help=getattr(OCRConfig, "_" + name),
                metavar="IMG_PATH" if name.startswith("dump_") else name.upper(),
                dest=name,
            )


def get_parser():
    # type: () -> argparse.ArgumentParser
    parser = argparse.ArgumentParser(description="Automation tool for VNC sessions using on OCR.")
    parser.add_argument(
        "host",
        help="Host with VNC port to connect to (can also be a file for testing purposes)",
        metavar="vnc_host",
    )
    parser.add_argument(
        "words",
        nargs="+",
        help="Words that will be matched and clicked upon in the VNC session",
        metavar="word",
    )
    parser.add_argument(
        "--log",
        "-l",
        default="info",
        choices=("debug", "info", "warn", "error", "critial"),
        help="Log level (debug, info, warn, error, critical)",
    )
    add_config_options_to_parser(parser)
    return parser


def parse_args(argv=None):
    # type: (Optional[Sequence[str]]) -> argparse.Namespace
    # parse arguments and create OCRConfig instance
    parser = get_parser()
    return parser.parse_args(argv)


def get_config_from_args(args):
    # type: (argparse.Namespace) -> OCRConfig
    return OCRConfig(**args.__dict__)


def main_vnc(host, words, config):
    # type: (str, str, OCRConfig) -> None
    logging.info("Connecting to VNC host %s", host)
    with VNCConnection(host) as client:
        client.updateOCRConfig(config)
        client.mouseClickOnText(words)


def main_img(img_path, words, config):
    # type: (str, str, OCRConfig) -> None

    logging.info("Loading image %s", img_path)
    ocr_algo = OCRAlgorithm(config)
    with Image.open(img_path) as img:
        deferred = ocr_algo.find_text_in_image(img, words)
        deferred.addCallback(lambda click_point: logging.info("Final click point: %s", click_point))
        deferred.addErrback(logging.error)
        deferred.addBoth(lambda _none: reactor.stop())

    reactor.run()


def main(argv=None):  # type: (Optional[Sequence[str]]) -> None
    args = parse_args(argv)
    config = get_config_from_args(args)
    words = " ".join(args.words)
    init_logger(args.log)

    if os.path.exists(args.host):
        main_img(args.host, words, config)
    else:
        main_vnc(args.host, words, config)


if __name__ == "__main__":
    main()
