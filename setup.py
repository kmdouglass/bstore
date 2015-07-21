try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

config = {
    'description'     : 'Single molecule clustering analysis',
    'author'          : 'Kyle M. Douglass',
    'url'             : 'https://github.com/kmdouglass/sm-clusters',
    'download_url'    : 'https://github.com/kmdouglass/sm-clusters',
    'author_email'    : 'kyle.m.douglass@gmail.com',
    'version'         : '0.1',
    'install_requires': ['nose'],
    'packages'        : [],
    'scripts'         : [],
    'name'            : 'smclusters'
}

setup(**config)
