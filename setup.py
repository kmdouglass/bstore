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
    'version'         : '0.2.1',
    'packages'        : ['bstore'],
    'scripts'         : [],
    'name'            : 'bstore'
}

setup(**config)
