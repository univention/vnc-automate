# coding: utf-8
from __future__ import absolute_import

import logging
from os.path import dirname, join

import pytest
from twisted.internet import reactor as _reactor

from vncautomate.cli import main


@pytest.fixture(autouse=True)
def reactor():
    """Reset Twisted reactor after test."""
    yield
    _reactor._startedBefore = False


def test_cli(caplog):
    with caplog.at_level(logging.INFO):
        main([join(dirname(__file__), "login.png"), "LOGIN"])
    assert caplog.record_tuples[-1] == ("root", logging.INFO, "Final click point: (278, 337)")
