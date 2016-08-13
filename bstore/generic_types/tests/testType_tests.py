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
from bstore                        import database as db
from pathlib                       import Path
from os                            import remove
from numpy                         import array
import h5py

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
    
def test_testType_Put_Data():
    """testType can put its own data and datasetIDs.
    
    """
     # Make up some dataset IDs and a dataset
    prefix      = 'test_prefix'
    acqID       = 1
    datasetType = 'generic'
    data        = array([42])
    ds = testType(prefix, acqID, datasetType, data)
    
    pathToDB = testDataRoot# / Path('generic_types/testType')
    
    myDB = db.HDFDatabase(pathToDB / Path('test_db.h5'))
    myDB.put(ds)
    
    key = 'test_prefix/test_prefix_1/testType'
    with h5py.File(str(pathToDB / Path('test_db.h5')), 'r') as hdf:
        assert_equal(hdf[key][0], 42)
        assert_equal(hdf[key].attrs['SMLM_datasetType'], 'generic')
        assert_equal(hdf[key].attrs['SMLM_genericTypeName'], 'testType')

    # Remove the test database
    remove(str(pathToDB / Path('test_db.h5')))