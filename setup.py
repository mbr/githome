#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from setuptools import setup, find_packages


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name='githome',
    version='0.1dev',
    description='A tiny server for your git repositories, allowing '
                'configurable levels of access for multiple users.',
    long_description=read('README.rst'),
    author='Marc Brinkmann',
    author_email='git@marcbrinkmann.de',
    url='http://github.com/mbr/githome',
    license='MIT',
    packages=find_packages(exclude=['tests']),
    install_requires=['logbook', 'click', 'pathlib', 'sqlalchemy', 'sshkeys'],
    entry_points={
        'console_scripts': [
            'githome = githome.cmd:run_cli',
        ],
    }
)
