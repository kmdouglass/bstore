# © All rights reserved. ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Switzerland, Laboratory of Experimental Biophysics, 2016
# See the LICENSE.txt file for more details.

"""Unit tests for the testType generic dataset type.

Notes
-----
nosetests should be run in the B-Store parent directory.

"""
 
__author__ = 'Kyle M. Douglass'
__email__ = 'kyle.m.douglass@gmail.com'

from nose.tools                    import *
from bstore.generic_types.testType import testType
from bstore                        import config
from pathlib                       import Path

testDataRoot = Path(config.__Path_To_Test_Data__)

def test_testType_Instantiation():
    """testType is properly instantiated.
    
    """
    # Make up some dataset IDs
    prefix      = 'test_prefix'
    acqID       = 1
    datasetType = 'generic'
    data        = 42
    
    ds = testType(prefix, acqID, datasetType, data)