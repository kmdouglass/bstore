import bstore.config as cfg
import sys, os

__version__ = cfg.__bstore_Version__

# Add the configuration and plugin directory to the Python path
cdir = os.path.expanduser(os.path.join(*cfg.__Custom_Dir__))
os.makedirs(cdir, exist_ok = True)
sys.path.append(cdir)
del(sys, os)