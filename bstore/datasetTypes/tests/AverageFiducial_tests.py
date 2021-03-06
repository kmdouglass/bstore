# © All rights reserved. ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Switzerland, Laboratory of Experimental Biophysics, 2016-2018
# See the LICENSE.txt file for more details.

"""Unit tests for the testType generic dataset type.

Notes
-----
nosetests should be run in the B-Store parent directory.

"""
 
__author__ = 'Kyle M. Douglass'
__email__ = 'kyle.m.douglass@gmail.com'

from nose.tools                    import assert_equal, ok_

# Register the type
from bstore  import config
config.__Registered_DatasetTypes__.append('AverageFiducial')

from bstore.datasetTypes.AverageFiducial import AverageFiducial
from bstore                        import database as db
from bstore                        import parsers, readers
from pathlib                       import Path
from os                            import remove
from os.path                       import exists

import pandas as pd
import h5py

testDataRoot = Path(config.__Path_To_Test_Data__)

def test_averageFiducial_Instantiation():
    """testType is properly instantiated.
    
    """
    # Make up some dataset IDs
    dsIDs           = {}
    dsIDs['prefix'] = 'test_prefix'
    dsIDs['acqID']  = 1
    
    AverageFiducial(datasetIDs = dsIDs)
    
def test__repr__():
    """DatasetType generates the correct __repr__ string.
    
    """
    dsIDs           = {}
    dsIDs['prefix'] = 'test_prefix'
    
    ds = AverageFiducial(datasetIDs = dsIDs)
    
    assert_equal(
        ds.__repr__(),
        'AverageFiducial: {\'prefix\': \'test_prefix\'}')
        
    del(ds.datasetIDs['prefix'])
    assert_equal(ds.__repr__(), 'AverageFiducial: {}')

def test_averageFiducial_Put_Data():
    """averageFiducial can put its own data and datasetIDs.
    
    """
    try:
        # Make up some dataset IDs and a dataset
        dsIDs           = {}
        dsIDs['prefix'] = 'test_prefix'
        dsIDs['acqID']  = 1
        ds      = AverageFiducial(datasetIDs = dsIDs)
        ds.data = pd.DataFrame({'A' : [1,2], 'B' : [3,4]})
        
        pathToDB = testDataRoot
        # Remove datastore if it exists
        if exists(str(pathToDB / Path('test_db.h5'))):
            remove(str(pathToDB / Path('test_db.h5')))
        
        with db.HDFDatastore(pathToDB / Path('test_db.h5')) as myDB:
            myDB.put(ds)
        
        key = 'test_prefix/test_prefix_1/AverageFiducial'
        with h5py.File(str(pathToDB / Path('test_db.h5')), 'r') as hdf:
            assert_equal(hdf[key].attrs['SMLM_datasetType'], 'AverageFiducial')
        
        df = pd.read_hdf(str(pathToDB / Path('test_db.h5')), key = key)
        assert_equal(df.loc[0, 'A'], 1)
        assert_equal(df.loc[1, 'A'], 2)
        assert_equal(df.loc[0, 'B'], 3)
        assert_equal(df.loc[1, 'B'], 4)
    finally:
        # Remove the test datastore
        remove(str(pathToDB / Path('test_db.h5')))
        
def test_averageFiducial_Get_Data():
    """The DatasetType can get its own data and datasetIDs.
    
    """
    try:
        # Make up some dataset IDs and a dataset
        dsIDs           = {}
        dsIDs['prefix'] = 'test_prefix'
        dsIDs['acqID']  = 1
        ds      = AverageFiducial(datasetIDs = dsIDs)
        ds.data = pd.DataFrame({'A' : [1,2], 'B' : [3,4]})
        
        pathToDB = testDataRoot
        # Remove datastore if it exists
        if exists(str(pathToDB / Path('test_db.h5'))):
            remove(str(pathToDB / Path('test_db.h5')))
        
        with db.HDFDatastore(pathToDB / Path('test_db.h5')) as myDB:
            myDB.put(ds)
        
        # Create a new dataset containing only IDs to test getting of the data
        myNewDSID = db.DatasetID('test_prefix', 1, 'AverageFiducial', None,
                                 None, None, None, None, None)
        myNewDS = myDB.get(myNewDSID)
        ids     = myNewDS.datasetIDs
        assert_equal(ids['prefix'],              'test_prefix')
        assert_equal(ids['acqID'],                           1)
        assert_equal(myNewDS.datasetType,    'AverageFiducial')
        assert_equal(ids['channelID'],                    None)
        assert_equal(ids['dateID'],                       None)
        assert_equal(ids['posID'],                        None)
        assert_equal(ids['sliceID'],                      None)
        assert_equal(ids['replicateID'],                  None)
        assert_equal(myNewDS.data.loc[0, 'A'], 1)
        assert_equal(myNewDS.data.loc[1, 'A'], 2)
        assert_equal(myNewDS.data.loc[0, 'B'], 3)
        assert_equal(myNewDS.data.loc[1, 'B'], 4)
    finally:
        # Remove the test datastore
        remove(str(pathToDB / Path('test_db.h5')))
        
def test_HDF_Datastore_Build_with_AverageFiducial():
    """The datastore build is performed successfully.
    
    """
    dbName   = testDataRoot / Path('database_test_files/myDB_Build_Avg.h5')
    if dbName.exists():
        remove(str(dbName))
    parser = parsers.PositionParser(positionIDs = {
                                            1 : 'prefix', 
                                            3 : 'channelID', 
                                            4 : 'acqID'})
    readerDict = {'AverageFiducial': readers.CSVReader()}    
    
    # Directory to traverse for acquisition files
    searchDirectory = testDataRoot / Path('test_experiment_2')
    
    # Build datastore
    with db.HDFDatastore(dbName) as myDB:
        myDB.build(parser, searchDirectory,
                   filenameStrings={'AverageFiducial' : '_AvgFid.dat'},
                   readers=readerDict,
                   dryRun = False)
    
    # Test for existence of the data
    with h5py.File(str(dbName), mode = 'r') as hdf:
        key1 = 'Control/Control_1/'
        name = 'AverageFiducial_ChannelA647'
        ok_(key1 + name in hdf)
        ok_(hdf[key1 + name].attrs.__contains__('SMLM_prefix'))
        ok_(hdf[key1 + name].attrs.__contains__('SMLM_acqID'))
        ok_(hdf[key1 + name].attrs.__contains__('SMLM_datasetType'))
        ok_(hdf[key1 + name].attrs.__contains__('SMLM_channelID'))
        ok_(hdf[key1 + name].attrs.__contains__('SMLM_dateID'))
        ok_(hdf[key1 + name].attrs.__contains__('SMLM_posID'))
        ok_(hdf[key1 + name].attrs.__contains__('SMLM_sliceID'))
        
        key2 = 'Control/Control_2/'
        ok_(key2 + name in hdf)
        ok_(hdf[key2 + name].attrs.__contains__('SMLM_acqID'))
        
        key3 = 'shTRF2/shTRF2_1/'
        ok_(key3 + name in hdf)
        ok_(hdf[key3 + name].attrs.__contains__('SMLM_acqID'))
        
        key4 = 'shTRF2/shTRF2_2/'
        ok_(key4 + name in hdf)
        ok_(hdf[key4 + name].attrs.__contains__('SMLM_acqID'))
    
    # Remove test datastore file
    remove(str(dbName))
  
def test_HDF_Datastore_Query_with_AverageFiducial():
    """The datastore query is performed successfully with AverageFiducial.
    
    """
    dbName   = testDataRoot / Path('database_test_files/myDB_Build_Avg.h5')
    if dbName.exists():
        remove(str(dbName))
    parser = parsers.PositionParser(positionIDs = {
                                            1 : 'prefix', 
                                            3 : 'channelID', 
                                            4 : 'acqID'})    
    
    # Directory to traverse for acquisition files
    searchDirectory = testDataRoot / Path('test_experiment_2')
    
    # Build datastore
    with db.HDFDatastore(dbName) as myDB:
        myDB.build(parser, searchDirectory,
                   filenameStrings   = {'AverageFiducial' : '_AvgFid.dat'},
                   dryRun = False)
    
    results = myDB.query(datasetType = 'AverageFiducial')
    
    ok_(len(results) != 0, 'Error: No AverageFiducial types found in DB.')
    for ds in results:
        assert_equal(ds.datasetType, 'AverageFiducial')
    
    # Remove test datastore file
    remove(str(dbName))
