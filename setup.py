#!/usr/bin/python2.7
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
