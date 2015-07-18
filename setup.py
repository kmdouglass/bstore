try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

config = {
    'description'     : 'Single molecule clustering analysis',
    'author'          : 'Kyle M. Douglass',
    'url'             : 'URL to get it at.',
    'download_url'    : 'Where to download it.',
    'author_email'    : 'kyle.m.douglass@gmail.com',
    'version'         : '0.1',
    'install_requires': ['nose'],
    'packages'        : ['NAME'],
    'scripts'         : [],
    'name'            : 'sm-clusters'
}

setup(**config)
