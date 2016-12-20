#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# As proposed at:
#
#   http://stackoverflow.com/a/30610032/6103207
#
# User contributions licensed under cc by-sa 3.0 with attribution required
#
#   https://creativecommons.org/licenses/by-sa/3.0/
#


import pyximport
old_get_distutils_extension = pyximport.pyximport.get_distutils_extension


def new_get_distutils_extension(modname, pyxfilename, language_level=None):
	extension_mod, setup_args = old_get_distutils_extension(modname, pyxfilename, language_level)
	extension_mod.language = 'c++'
	return extension_mod, setup_args

pyximport.pyximport.get_distutils_extension = new_get_distutils_extension
pyximport.install()


def _pass():
	# void function to make style warnings go away
	pass
