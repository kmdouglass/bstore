try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

config = {
    'description'     : 'Lightweight data management and analysis tools for single-molecule microscopy.',
    'author'          : 'Kyle M. Douglass',
    'url'             : 'https://github.com/kmdouglass/bstore',
    'download_url'    : 'https://github.com/kmdouglass/bstore',
    'author_email'    : 'kyle.m.douglass@gmail.com',
    'version'         : '1.0.0dev',
    'packages'        : ['bstore'],
    'scripts'         : ['bin/bstore'],
    'name'            : 'bstore'
}

setup(**config)
