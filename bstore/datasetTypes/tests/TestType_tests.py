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

# Register the test type
from bstore  import config
config.__Registered_DatasetTypes__.append('TestType')

from bstore.datasetTypes.TestType  import TestType
from bstore                        import database as db
from pathlib                       import Path
from os                            import remove
from os.path                       import exists
from numpy                         import array
import h5py

testDataRoot = Path(config.__Path_To_Test_Data__)

def test__repr__():
    """DatasetType generates the correct __repr__ string.
    
    """
    dsIDs           = {}
    dsIDs['prefix'] = 'test_prefix'
    
    ds = TestType(datasetIDs = dsIDs)
    
    assert_equal(ds.__repr__(), 'TestType: {\'prefix\': \'test_prefix\'}')
    
    del(ds.datasetIDs['prefix'])
    assert_equal(ds.__repr__(), 'TestType: {}')
    
def test_testType_Put_Data():
    """testType can put its own data and datasetIDs.
    
    """
    # Make up some dataset IDs and a dataset
    dsIDs           = {}
    dsIDs['prefix'] = 'test_prefix'
    dsIDs['acqID']  = 1
    ds              = TestType(datasetIDs = dsIDs)
    ds.data         = array([42])
    
    pathToDB = testDataRoot
    # Remove datastore if it exists
    if exists(str(pathToDB / Path('test_db.h5'))):
        remove(str(pathToDB / Path('test_db.h5')))
    
    myDB = db.HDFDatastore(pathToDB / Path('test_db.h5'))
    myDB.put(ds)
    
    key = 'test_prefix/test_prefix_1/TestType'
    with h5py.File(str(pathToDB / Path('test_db.h5')), 'r') as hdf:
        assert_equal(hdf[key][0],                                42)
        assert_equal(hdf[key].attrs['SMLM_datasetType'], 'TestType')
        assert_equal(hdf[key].attrs['SMLM_prefix'],   'test_prefix')
        assert_equal(hdf[key].attrs['SMLM_acqID'],                1)

    # Remove the test datastore
    remove(str(pathToDB / Path('test_db.h5')))

  
def test_testType_DatasetIDs():
    """testType can return the correct dataset IDs.
    
    """
    # Make up some dataset IDs and a dataset
    dsIDs           = {}
    dsIDs['prefix'] = 'test_prefix'
    dsIDs['acqID']  = 1
    ds              = TestType(datasetIDs = dsIDs)
    ds.data         = array([42])
    
    ids = ds.datasetIDs
    assert_equal(ids['prefix'],       'test_prefix')
    assert_equal(ids['acqID'],                    1)
    assert_equal(ds.datasetType,         'TestType')
    assert_equal(ds.attributeOf,               None)
 
def test_testType_Get_Data():
    """testType can get its own data and datasetIDs.
    
    """
    # Make up some dataset IDs and a dataset
    dsIDs           = {}
    dsIDs['prefix'] = 'test_prefix'
    dsIDs['acqID']  = 1
    ds              = TestType(datasetIDs = dsIDs)
    ds.data         = array([42])
    
    pathToDB = testDataRoot
    # Remove datastore if it exists
    if exists(str(pathToDB / Path('test_db.h5'))):
        remove(str(pathToDB / Path('test_db.h5')))
    
    myDB = db.HDFDatastore(pathToDB / Path('test_db.h5'))
    myDB.put(ds)
    
    # Create a new dataset containing only IDs to test getting of the data
    dsID = myDB.dsID('test_prefix', 1, 'TestType', None,
                     None, None, None, None)   
    
    myNewDS = myDB.get(dsID)
    ids     = myNewDS.datasetIDs
    assert_equal(ids['prefix'],       'test_prefix')
    assert_equal(ids['acqID'],                    1)
    assert_equal(ids['channelID'],             None)
    assert_equal(ids['dateID'],                None)
    assert_equal(ids['posID'],                 None)
    assert_equal(ids['sliceID'],               None)
    assert_equal(myNewDS.datasetType,    'TestType')
    assert_equal(myNewDS.attributeOf,          None)
    assert_equal(myNewDS.data,                   42)
    
    # Remove the test datastore
    remove(str(pathToDB / Path('test_db.h5')))