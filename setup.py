#!/usr/bin/env python3
# This file is part of the recover_invoice_ar module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

import io
import os
import re
from configparser import ConfigParser
from setuptools import setup

MODULE2PREFIX = {
    'account_invoice_ar': 'trytonar',
    }


def read(fname):
    return io.open(
        os.path.join(os.path.dirname(__file__), fname),
        'r', encoding='utf-8').read()


def get_require_version(name):
    if name in LINKS:
        return '%s @ %s' % (name, LINKS[name])
    if minor_version % 2:
        require = '%s >= %s.%s.dev0, < %s.%s'
    else:
        require = '%s >= %s.%s, < %s.%s'
    require %= (name, major_version, minor_version,
        major_version, minor_version + 1)
    return require


config = ConfigParser()
config.read_file(open('tryton.cfg'))
info = dict(config.items('tryton'))
for key in ('depends', 'extras_depend', 'xml'):
    if key in info:
        info[key] = info[key].strip().splitlines()
version = info.get('version', '0.0.1')
major_version, minor_version, _ = version.split('.', 2)
major_version = int(major_version)
minor_version = int(minor_version)
name = 'trytonar_recover_invoice_ar'

download_url = 'https://github.com/tryton-ar/recover_invoice_ar/tree/%s.%s' % (
    major_version, minor_version)

LINKS = {
    'trytonar_account_invoice_ar': ('git+https://github.com/tryton-ar/'
        'account_invoice_ar.git@%s.%s#egg=trytonar_account_invoice_ar-%s.%s' %
        (major_version, minor_version, major_version, minor_version)),
    }

requires = []
for dep in info.get('depends', []):
    if not re.match(r'(ir|res)(\W|$)', dep):
        module_name = '%s_%s' % (MODULE2PREFIX.get(dep, 'trytond'), dep)
        requires.append(get_require_version(module_name))

requires.append(get_require_version('trytond'))

tests_require = [get_require_version('proteus')]
dependency_links = list(LINKS.values())

setup(name=name,
    version=version,
    description=('Tryton module for recover electronic invoice from AFIP '
        '(Argentina)'),
    long_description=read('README'),
    author='tryton-ar',
    url='https://github.com/tryton-ar/recover_invoice_ar',
    download_url=download_url,
    package_dir={'trytond.modules.recover_invoice_ar': '.'},
    packages=[
        'trytond.modules.recover_invoice_ar',
        'trytond.modules.recover_invoice_ar.tests',
        ],
    package_data={
        'trytond.modules.recover_invoice_ar': (info.get('xml', []) + [
            'tryton.cfg', 'view/*.xml', 'locale/*.po']),
        },
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Plugins',
        'Framework :: Tryton',
        'Intended Audience :: Developers',
        'Intended Audience :: Financial and Insurance Industry',
        'Intended Audience :: Legal Industry',
        'License :: OSI Approved :: GNU General Public License v3 or later'
        ' (GPLv3+)',
        'Natural Language :: English',
        'Natural Language :: Spanish',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Office/Business',
        'Topic :: Office/Business :: Financial :: Accounting',
        ],
    license='GPL-3',
    python_requires='>=3.5',
    install_requires=requires,
    dependency_links=dependency_links,
    zip_safe=False,
    entry_points="""
    [trytond.modules]
    recover_invoice_ar = trytond.modules.recover_invoice_ar
    """,
    test_suite='tests',
    test_loader='trytond.test_loader:Loader',
    tests_require=tests_require,
    )