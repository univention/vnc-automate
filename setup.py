from setuptools import setup
from Cython.Build import cythonize

with open("debian/changelog", "r") as fh:
	line = fh.readline()
	name, _ver, _tail = line.split(" ", 2)
	version = _ver.strip("()").replace("-", ".")

setup(
	name=name,
	version=version,
	ext_modules=cythonize('vncautomate/segment_line.pyx'),
	test_suite='tests',
)
