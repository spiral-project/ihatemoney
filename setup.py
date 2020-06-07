# -*- coding: utf-8 -*-
import os
import sys

from io import open
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))


def parse_requirements(filename):
    """ load requirements from a pip requirements file """
    with open(filename) as lines:
        lineiter = (line.strip() for line in lines)
        return [line for line in lineiter if line and not line.startswith("#")]


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
      version='4.1.4',
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
          "blinker==1.4",
          "email-validator==1.0.4",
          "Flask==1.1.1",
          "Flask-Babel==0.12.2",
          "Flask-Cors==3.0.8",
          "Flask-Mail==0.9.1",
          "Flask-Migrate==2.5.3",
          "Flask-RESTful==0.3.7",
          "Flask-Script==2.0.6",
          "Flask-SQLAlchemy==2.4.0",
          "Flask-WTF==0.14.3",
          "itsdangerous==1.1.0",
          "Jinja2==2.10.1",
          "six==1.14.0",
          "WTForms==2.2.1",
          "Werkzeug==0.16.1",
      ],
      extras_require={"dev": [
          "zest.releaser",
          "tox",
          "pytest",
          "flake8",
          "Flask-Testing",
          "mock; python_version < '3.3'"
      ]},
      entry_points=ENTRY_POINTS)
