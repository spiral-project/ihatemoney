# -*- coding: utf-8 -*-
import os
import sys

from io import open
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))

README = open('README.rst', encoding='utf-8').read()
CHANGELOG = open('CHANGELOG.rst', encoding='utf-8').read()

description = u'\n'.join([README, CHANGELOG])
if sys.version_info.major < 3:
    description = description.encode('utf-8')

ENTRY_POINTS = {
    'paste.app_factory': [
        'main = ihatemoney.run:main',
    ],
    'console_scripts': [
        'ihatemoney = ihatemoney.manage:main'
    ],
}

setup(name='ihatemoney',
      version='4.2.dev0',
      description='A simple shared budget manager web application.',
      long_description=description,
      license='Custom BSD Beerware',
      classifiers=[
          "Programming Language :: Python",
          "Programming Language :: Python :: 2.7",
          "Programming Language :: Python :: 3",
          "Programming Language :: Python :: 3.5",
          "Programming Language :: Python :: 3.6",
          "Programming Language :: Python :: 3.7",
          "Programming Language :: Python :: Implementation :: CPython",
          "Topic :: Internet :: WWW/HTTP",
          "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
      ],
      keywords="web budget",
      author='Alexis Métaireau & contributors',
      author_email='alexis@notmyidea.org',
      url='https://github.com/spiral-project/ihatemoney',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          "flask",
          "flask-wtf",
          "flask-sqlalchemy<3.0",
          "flask-mail",
          "Flask-Migrate",
          "Flask-script",
          "flask-babel",
          "flask-restful",
          "jinja2",
          "blinker",
          "flask-cors",
          "six",
          "itsdangerous",
          "email_validator",
          "debts"],
      entry_points=ENTRY_POINTS)
