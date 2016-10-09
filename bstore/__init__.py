import bstore.config
import sys, os

__version__ = bstore.config.__bstore_Version__

# Add the configuration and plugin directory to the Python path
cdir = os.path.expanduser('~/.bstore')
os.makedirs(cdir, exist_ok = True)
sys.path.append(cdir)
del(sys, os)