import bstore.config as cfg
import sys, os

__version__ = cfg.__bstore_Version__

# Create the configuration and plugin directories to the Python path
# Add the configuration directory to the Python path
cdir = os.path.expanduser(os.path.join(*cfg.__Custom_Dir__))
pdir = os.path.expanduser(os.path.join(*cfg.__Plugin_Dir__))
os.makedirs(cdir, exist_ok = True)
os.makedirs(pdir, exist_ok = True)
sys.path.append(cdir)
del(sys, os)