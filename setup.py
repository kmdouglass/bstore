try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

config = {
    'description'     : 'Data management and analysis for single molecule microscopy',
    'author'          : 'Kyle M. Douglass',
    'url'             : 'https://github.com/kmdouglass/DataSTORM',
    'download_url'    : 'https://github.com/kmdouglass/DataSTORM',
    'author_email'    : 'kyle.m.douglass@gmail.com',
    'version'         : '0.1.0',
    'install_requires': ['nose',
                         'scikit-learn',
                         'pandas',
                         'trackpy',
                         'numpy',
                         'scipy',
                         'matplotlib',
                         'pyhull',
                         'h5py'],
    'packages'        : [],
    'scripts'         : [],
    'name'            : 'DataSTORM'
}

setup(**config)
