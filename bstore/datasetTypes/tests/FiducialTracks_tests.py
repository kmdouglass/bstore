# © All rights reserved. ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Switzerland, Laboratory of Experimental Biophysics, 2016
# See the LICENSE.txt file for more details.

"""Unit tests for the FiducialTracks DatasetType.

Notes
-----
nosetests should be run in the B-Store parent directory.

"""
 
__author__ = 'Kyle M. Douglass'
__email__  = 'kyle.m.douglass@gmail.com'

from nose.tools                    import assert_equal, ok_

# Register the type
from bstore  import config
config.__Registered_DatasetTypes__.append('AverageFiducial')
config.__Registered_DatasetTypes__.append('FiducialTracks')

#from bstore.generic_types.averageFiducial import averageFiducial
from bstore.datasetTypes.FiducialTracks  import FiducialTracks
from bstore                        import database as db
from bstore                        import parsers
from pathlib                       import Path
from os                            import remove
from os.path                       import exists

import pandas as pd
import h5py

testDataRoot = Path(config.__Path_To_Test_Data__)

def test_fiducialTracks_Instantiation():
    """The datasetType is properly instantiated.
    
    """
    # Make up some dataset IDs
    dsIDs           = {}
    dsIDs['prefix'] = 'test_prefix'
    dsIDs['acqID']  = 1
    
    FiducialTracks(datasetIDs = dsIDs)
    
def test_fiducialTracks_Put_Data():
    """The datasetType can put its own data and datasetIDs.
    
    """
    try:
        # Make up some dataset IDs and a dataset
        dsIDs           = {}
        dsIDs['prefix'] = 'test_prefix'
        dsIDs['acqID']  = 1
        ds      = FiducialTracks(datasetIDs = dsIDs)
        ds.data = pd.DataFrame({'A' : [1,2], 'B' : [3,4]})
        
        pathToDB = testDataRoot
        # Remove database if it exists
        if exists(str(pathToDB / Path('test_db.h5'))):
            remove(str(pathToDB / Path('test_db.h5')))
        
        myDB = db.HDFDatabase(pathToDB / Path('test_db.h5'))
        myDB.put(ds)
        
        key = 'test_prefix/test_prefix_1/FiducialTracks'
        with h5py.File(str(pathToDB / Path('test_db.h5')), 'r') as hdf:
            assert_equal(hdf[key].attrs['SMLM_datasetType'], 'FiducialTracks')
        
        df = pd.read_hdf(str(pathToDB / Path('test_db.h5')), key = key)
        assert_equal(df.loc[0, 'A'], 1)
        assert_equal(df.loc[1, 'A'], 2)
        assert_equal(df.loc[0, 'B'], 3)
        assert_equal(df.loc[1, 'B'], 4)
    finally:
        # Remove the test database
        remove(str(pathToDB / Path('test_db.h5')))
      
def test_fiducialTracks_Get_Data():
    """The datasetType can get its own data and datasetIDs.
    
    """
    try:
        # Make up some dataset IDs and a dataset
        dsIDs           = {}
        dsIDs['prefix'] = 'test_prefix'
        dsIDs['acqID']  = 1
        ds      = FiducialTracks(datasetIDs = dsIDs)
        ds.data = pd.DataFrame({'A' : [1,2], 'B' : [3,4]})
        
        pathToDB = testDataRoot
        # Remove database if it exists
        if exists(str(pathToDB / Path('test_db.h5'))):
            remove(str(pathToDB / Path('test_db.h5')))
        
        myDB = db.HDFDatabase(pathToDB / Path('test_db.h5'))
        myDB.put(ds)
        
        # Create a new dataset containing only IDs to test getting of the data
        myNewDSID = myDB.dsID('test_prefix', 1, 'FiducialTracks', None,
                              None, None, None, None)
        myNewDS = myDB.get(myNewDSID)
        ids     = myNewDS.datasetIDs
        assert_equal(ids['prefix'],              'test_prefix')
        assert_equal(ids['acqID'],                           1)
        assert_equal(myNewDS.datasetType,     'FiducialTracks')
        assert_equal(ids['channelID'],                    None)
        assert_equal(ids['dateID'],                       None)
        assert_equal(ids['posID'],                        None)
        assert_equal(ids['sliceID'],                      None)   
        assert_equal(myNewDS.data.loc[0, 'A'], 1)
        assert_equal(myNewDS.data.loc[1, 'A'], 2)
        assert_equal(myNewDS.data.loc[0, 'B'], 3)
        assert_equal(myNewDS.data.loc[1, 'B'], 4)
    finally:
        # Remove the test database
        remove(str(pathToDB / Path('test_db.h5')))
    
def test_HDF_Database_Build_with_fiducialTracks():
    """The database build is performed successfully.
    
    """
    dbName   = testDataRoot / Path('database_test_files/myDB_Build_Avg.h5')
    if dbName.exists():
        remove(str(dbName))
    myDB = db.HDFDatabase(dbName)
    myParser = parsers.MMParser()    
    
    # Directory to traverse for acquisition files
    searchDirectory = testDataRoot / Path('test_experiment_2')
    
    # Build database
    myDB.build(myParser, searchDirectory,
               filenameStrings   = {'FiducialTracks'  : '_Fids.dat',
                                    'AverageFiducial' : '_AvgFid.dat'},
               dryRun = False)
    
    # Test for existence of the data
    with h5py.File(str(dbName), mode = 'r') as hdf:
        key1 = 'HeLaS_Control_IFFISH/HeLaS_Control_IFFISH_1/'
        name1 = 'FiducialTracks_A647_Pos0'
        name2 = 'AverageFiducial_A647_Pos0'
        ok_(key1 + name1 in hdf)
        ok_(key1 + name2 in hdf)
        ok_(hdf[key1 + name1].attrs.__contains__('SMLM_prefix'))
        ok_(hdf[key1 + name1].attrs.__contains__('SMLM_acqID'))
        ok_(hdf[key1 + name1].attrs.__contains__('SMLM_datasetType'))
        ok_(hdf[key1 + name1].attrs.__contains__('SMLM_channelID'))
        ok_(hdf[key1 + name1].attrs.__contains__('SMLM_dateID'))
        ok_(hdf[key1 + name1].attrs.__contains__('SMLM_posID'))
        ok_(hdf[key1 + name1].attrs.__contains__('SMLM_sliceID'))
        
        
        key2 = 'HeLaS_Control_IFFISH/HeLaS_Control_IFFISH_2/'
        ok_(key2 + name1 in hdf)
        ok_(key2 + name2 in hdf)
        
        key3 = 'HeLaS_shTRF2_IFFISH/HeLaS_shTRF2_IFFISH_1/'
        ok_(key3 + name1 in hdf)
        ok_(key3 + name2 in hdf)
        
        key4 = 'HeLaS_shTRF2_IFFISH/HeLaS_shTRF2_IFFISH_2/'
        ok_(key4 + name1 in hdf)
        ok_(key4 + name2 in hdf)
    
    # Remove test database file
    remove(str(dbName))

def test_HDF_Database_Query_with_FiducialTracks():
    """The database query is performed successfully with the datasetType.
    
    """
    dbName   = testDataRoot / Path('database_test_files/myDB_Build_Avg.h5')
    if dbName.exists():
        remove(str(dbName))
    myDB = db.HDFDatabase(dbName)
    myParser = parsers.MMParser()    
    
    # Directory to traverse for acquisition files
    searchDirectory = testDataRoot / Path('test_experiment_2')
    
    # Build database
    myDB.build(myParser, searchDirectory,
               filenameStrings   = {'FiducialTracks'  : '_Fids.dat',
                                   'AverageFiducial' : '_AvgFid.dat'},
               dryRun = False)
    
    results = myDB.query(datasetType = 'FiducialTracks')
    
    ok_(len(results) != 0, 'Error: No FiducialTracks types found in DB.')
    for ds in results:
        assert_equal(ds.datasetType, 'FiducialTracks')
    
    # Remove test database file
    remove(str(dbName))