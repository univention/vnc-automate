#!/usr/bin/python3
# SPDX-FileCopyrightText: 2016-2023 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

from setuptools import Extension, setup

setup(
    ext_modules=[
        Extension(
            "vncautomate.segment_line",
            sources=["src/vncautomate/segment_line.pyx"],
            language="c++",
        ),
    ],
    test_suite="tests",
)
