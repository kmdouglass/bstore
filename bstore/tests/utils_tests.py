# -*- coding: utf-8 -*-
# © All rights reserved. ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Switzerland, Laboratory of Experimental Biophysics, 2016
# See the LICENSE.txt file for more details.

"""Tests of private functions used by B-Store to facilitate its operation.

"""

from nose.tools import assert_equal

import os
import shutil
import bstore.config as cfg
import bstore._utils as _utils
from pathlib import Path

testDataRoot = Path(cfg.__Path_To_Test_Data__)

def test_findPlugins():
    """Find plugins finds all B-Store plugins.
    
    """
    # Copy the plugins test file to the customization directory
    fName = 'test_plugins_source.py'
    pSrc  = testDataRoot / Path('_utils_test_files/test_plugins_source.py')
    cFile = os.path.expanduser(os.path.join(*(cfg.__Plugin_Dir__ + [fName])))
    shutil.copyfile(str(pSrc), cFile)
    
    plugins1 = _utils.findPlugins('Plugin1')
    plugins2 = _utils.findPlugins('Plugin2')
    
    assert_equal(len(plugins1), 1)
    assert_equal(len(plugins2), 2)
    
    assert_equal(plugins1[0][0], 'myPlugin')
    
    # Remove the test file
    if Path(cFile).exists():
        os.remove(cFile)