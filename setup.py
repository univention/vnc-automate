#!/usr/bin/python2.7
import io
from setuptools import setup
from Cython.Build import cythonize
from email.utils import parseaddr
from debian.changelog import Changelog
from debian.deb822 import Deb822

dch = Changelog(io.open('debian/changelog', 'r', encoding='utf-8'))
dsc = Deb822(io.open('debian/control', 'r', encoding='utf-8'))
realname, email_address = parseaddr(dsc['Maintainer'])

setup(
    packages=['vncautomate'],
    package_dir={'': '.'},
    ext_modules=cythonize('vncautomate/*.pyx', language='c++'),
    description='GUI test framework for Python',
    install_requires=[
        "lxml",
        "numpy",
        "Pillow",
        "scipy",
        'Twisted',
        'vncdotool',
        'future',
    ],
    test_suite='tests',

    url='https://www.univention.de/',
    license='GNU Affero General Public License v3',

    name=dch.package,
    version=dch.version.full_version,
    maintainer=realname,
    maintainer_email=email_address,
)
