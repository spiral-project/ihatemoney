# -*- coding: utf-8 -*-
import codecs
import os
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))


def read_file(filename):
    """Open a related file and return its content."""
    with codecs.open(os.path.join(here, filename), encoding='utf-8') as f:
        content = f.read()
    return content


README = read_file('README.rst')
CHANGELOG = read_file('CHANGELOG.rst')

REQUIREMENTS = [
    'flask>=0.11',
    'flask-wtf>=0.13',
    'flask-sqlalchemy',
    'flask-mail>=0.8',
    'Flask-Migrate>=1.8.0',
    'flask-babel',
    'flask-rest',
    'jinja2>=2.6',
    'raven',
    'blinker',
    'six>=1.10',
]

DEPENDENCY_LINKS = [
]

ENTRY_POINTS = {
    'paste.app_factory': [
        'main = budget.run:main',
    ],
}


setup(name='ihatemoney',
      version='1.0',
      description='A simple shared budget manager web application.',
      long_description="{}\n\n{}".format(README, CHANGELOG),
      license='Custom BSD Beerware',
      classifiers=[
          "Programming Language :: Python",
	  "Programming Language :: Python :: 2.7",
          "Programming Language :: Python :: 3",
          "Programming Language :: Python :: 3.5",
          "Programming Language :: Python :: Implementation :: CPython",
          "Topic :: Internet :: WWW/HTTP",
          "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
      ],
      keywords="web budget",
      author='Alexis Métaireau & contributors',
      author_email='alexis@notmyidea.org',
      url='https://github.com/spiral-project/ihatemoney',
      packages=find_packages(),
      package_data={'': ['*.rst', '*.py', '*.yaml', '*.po', '*.mo', '*.html',
                         '*.css', '*.js', '*.eot', '*.svg', '*.woff', '*.txt',
                         '*.png', '*.ini', '*.cfg']},
      include_package_data=True,
      zip_safe=False,
      install_requires=REQUIREMENTS,
      dependency_links=DEPENDENCY_LINKS,
entry_points=ENTRY_POINTS)
