try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

config = {
    'description'     : 'Data management and analysis for single molecule microscopy',
    'author'          : 'Kyle M. Douglass',
    'url'             : 'https://github.com/kmdouglass/dataSTORM',
    'download_url'    : 'https://github.com/kmdouglass/dataSTORM',
    'author_email'    : 'kyle.m.douglass@gmail.com',
    'version'         : '0.1',
    'install_requires': ['nose'],
    'packages'        : [],
    'scripts'         : [],
    'name'            : 'dataSTORM'
}

setup(**config)
