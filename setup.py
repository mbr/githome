#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from setuptools import setup, find_packages
from setuptools.command.install import install

from distutils.sysconfig import customize_compiler
from distutils.ccompiler import new_compiler


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


class InstallWithTools(install):
    def run(self):
        cc = new_compiler()
        customize_compiler(cc)
        o_files = cc.compile(['githome/gh_client.c'])
        cc.link_executable(o_files, 'githome/gh_client')

        install.run(self)  # run normal build command


setup(
    name='githome',
    version='0.3.2.dev1',
    description='A tiny server for your git repositories, allowing '
                'configurable levels of access for multiple users.',
    long_description=read('README.rst'),
    author='Marc Brinkmann',
    author_email='git@marcbrinkmann.de',
    url='http://github.com/mbr/githome',
    license='MIT',
    packages=find_packages(exclude=['tests']),
    package_data={
        'githome': ['gh_client'],
    },
    install_requires=['logbook', 'click>=4.0', 'pathlib', 'sqlalchemy',
                      'sshkeys>=0.4', 'sqlacfg', 'future', 'trollius'],
    entry_points={
        'console_scripts': [
            'githome = githome.cmd:cli',
        ],
    },
    cmdclass={
        'install': InstallWithTools,
    },
    zip_safe=False,
)
