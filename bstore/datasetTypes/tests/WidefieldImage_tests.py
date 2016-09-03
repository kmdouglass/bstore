# © All rights reserved. ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Switzerland, Laboratory of Experimental Biophysics, 2016
# See the LICENSE.txt file for more details.

"""Unit tests for the WidefieldImage DatasetType.

Notes
-----
nosetests should be run in the B-Store parent directory.

"""
 
__author__ = 'Kyle M. Douglass'
__email__  = 'kyle.m.douglass@gmail.com'

from nose.tools                    import *

# Register the type
from bstore  import config
config.__Registered_DatasetTypes__.append('WidefieldImage')
config.__Registered_DatasetTypes__.append('Localizations')

from bstore.datasetTypes.WidefieldImage import WidefieldImage
from bstore.datasetTypes.Localizations  import Localizations
from bstore                             import database as db
from pathlib                            import Path
from os                                 import remove
from os.path                            import exists
from matplotlib.pyplot                  import imread
import bstore.parsers as parsers
import h5py

testDataRoot = Path(config.__Path_To_Test_Data__)

def test_Instantiation():
    """The datasetType is properly instantiated.
    
    """
    # Make up some dataset IDs
    prefix      = 'test_prefix'
    acqID       = 1
    datasetType = 'generic'
    data        = 42
    
    WidefieldImage(prefix, acqID, datasetType, data)

def test_Put_Data():
    """The datasetType can put its own data and datasetIDs.
    
    """
    imgPath = testDataRoot / Path('test_experiment_2/HeLaS_Control_IFFISH') \
              / Path('HeLaS_Control_IFFISH_A647_WF1') \
              / Path('HeLaS_Control_IFFISH_A647_WF1_MMStack_Pos0.ome.tif')
    img = imread(str(imgPath))
    try:
        # Make up some dataset IDs and a dataset
        prefix      = 'test_prefix'
        acqID       = 1
        datasetType = 'generic'
        data        = img
        ds          = WidefieldImage(prefix, acqID, datasetType, data)
        
        pathToDB = testDataRoot
        # Remove database if it exists
        if exists(str(pathToDB / Path('test_db.h5'))):
            remove(str(pathToDB / Path('test_db.h5')))
        
        myDB = db.HDFDatabase(pathToDB / Path('test_db.h5'))
        myDB.put(ds)
        
        key = 'test_prefix/test_prefix_1/WidefieldImage'
        with h5py.File(str(pathToDB / Path('test_db.h5')), 'r') as hdf:
            assert_equal(hdf[key].attrs['SMLM_datasetType'], 'generic')
            assert_equal(hdf[key].attrs['SMLM_datasetTypeName'],
                         'WidefieldImage')
            imgData = hdf[key + '/image_data'].value

        assert_equal(imgData.shape, (927, 927))
    finally:
        # Remove the test database
        remove(str(pathToDB / Path('test_db.h5')))
    
def test_Put_Data_kwarg_WidefieldPixelSize():
    """The WidefieldImage will write the correct pixel size if provided.
    
    """
    imgPath = testDataRoot / Path('test_experiment_2/HeLaS_Control_IFFISH') \
              / Path('HeLaS_Control_IFFISH_A647_WF1') \
              / Path('HeLaS_Control_IFFISH_A647_WF1_MMStack_Pos0.ome.tif')
    img = imread(str(imgPath))
    try:
        # Make up some dataset IDs and a dataset
        prefix      = 'test_prefix'
        acqID       = 1
        datasetType = 'generic'
        data        = img
        ds          = WidefieldImage(prefix, acqID, datasetType, data)
        
        pathToDB = testDataRoot
        # Remove database if it exists
        if exists(str(pathToDB / Path('test_db.h5'))):
            remove(str(pathToDB / Path('test_db.h5')))
        
        myDB = db.HDFDatabase(pathToDB / Path('test_db.h5'))
        myDB.put(ds, widefieldPixelSize = (0.13, 0.13))
        
        key = 'test_prefix/test_prefix_1/WidefieldImage'
        with h5py.File(str(pathToDB / Path('test_db.h5')), 'r') as hdf:
            assert_equal(hdf[key + '/image_data'].attrs['element_size_um'][0],
                         1)
            assert_equal(hdf[key + '/image_data'].attrs['element_size_um'][1],
                         0.13)
            assert_equal(hdf[key + '/image_data'].attrs['element_size_um'][2],
                         0.13)
    finally:
        # Remove the test database
        remove(str(pathToDB / Path('test_db.h5')))
        
'''        
def test_Get_Data():
    """The datasetType can get its own data and datasetIDs.
    
    """
    try:
        # Make up some dataset IDs and a dataset
        prefix      = 'test_prefix'
        acqID       = 1
        datasetType = 'generic'
        data        = pd.DataFrame({'A' : [1,2], 'B' : [3,4]})
        ds = Localizations(prefix, acqID, datasetType, data)
        
        pathToDB = testDataRoot
        # Remove database if it exists
        if exists(str(pathToDB / Path('test_db.h5'))):
            remove(str(pathToDB / Path('test_db.h5')))
        
        myDB = db.HDFDatabase(pathToDB / Path('test_db.h5'))
        myDB.put(ds)
        
        # Create a new dataset containing only IDs to test getting of the data
        myNewDS = myDB.get(Localizations(prefix, acqID, datasetType, None))
        ids     = myNewDS.getInfoDict()
        assert_equal(ids['prefix'],              'test_prefix')
        assert_equal(ids['acqID'],                           1)
        assert_equal(ids['datasetType'],             'generic')
        assert_equal(ids['channelID'],                    None)
        assert_equal(ids['dateID'],                       None)
        assert_equal(ids['posID'],                        None)
        assert_equal(ids['sliceID'],                      None)
        assert_equal(ids['datasetTypeName'],   'Localizations')   
        assert_equal(myNewDS.data.loc[0, 'A'], 1)
        assert_equal(myNewDS.data.loc[1, 'A'], 2)
        assert_equal(myNewDS.data.loc[0, 'B'], 3)
        assert_equal(myNewDS.data.loc[1, 'B'], 4)
    finally:
        # Remove the test database
        remove(str(pathToDB / Path('test_db.h5')))
''' 

def test_HDF_Database_Build():
    """The database build is performed successfully.
    
    """
    dbName   = testDataRoot / Path('database_test_files/myDB_Build.h5')
    if dbName.exists():
        remove(str(dbName))
    myDB = db.HDFDatabase(dbName)
    myParser = parsers.MMParser(readTiffTags = True)    
    
    # Directory to traverse for acquisition files
    searchDirectory = testDataRoot / Path('test_experiment')
    
    # Build database
    myDB.build(myParser, searchDirectory,
               filenameStrings  = {'WidefieldImage' : '.ome.tif',
                                   'Localizations'  : 'locResults.dat'},
               dryRun = False)
               
    # Test for existence of the data
    with h5py.File(str(dbName), mode = 'r') as hdf:
        key1 = ('HeLaL_Control/HeLaL_Control_1/WidefieldImage_A647_Pos0/'
                'image_data')
        ok_('HeLaL_Control/HeLaL_Control_1/Localizations_A647_Pos0' in hdf)
        ok_('HeLaL_Control/HeLaL_Control_1/WidefieldImage_A647_Pos0' in hdf)
        ok_('element_size_um' in hdf[key1].attrs)
        
        key2 = ('HeLaS_Control/HeLaS_Control_2/WidefieldImage_A647_Pos0/'
                'image_data')
        ok_('HeLaS_Control/HeLaS_Control_2/Localizations_A647_Pos0' in hdf)
        ok_('HeLaS_Control/HeLaS_Control_2/WidefieldImage_A647_Pos0' in hdf)
        ok_('element_size_um' in hdf[key2].attrs)
    
    # Remove test database file
    #remove(str(dbName))
    
'''
def test_HDF_Database_Query_with_fiducialTracks():
    """The database query is performed successfully with the datasetType.
    
    """
    dbName   = testDataRoot / Path('database_test_files/myDB_Build.h5')
    if dbName.exists():
        remove(str(dbName))
    myDB = db.HDFDatabase(dbName)
    myParser = parsers.MMParser()    
    
    # Directory to traverse for acquisition files
    searchDirectory = testDataRoot / Path('test_experiment_2')
    
    # Build database
    myDB.build(myParser, searchDirectory,
               locResultsString = '_DC.dat',
               filenameStrings  = {'Localizations'  : '_DC.dat'},
               dryRun = False)
    
    results = myDB.query(datasetType = 'generic',
                         datasetTypeName = 'Localizations')
    
    ok_(len(results) != 0, 'Error: No dataset types found in DB.')
    for ds in results:
        assert_equal(ds.datasetType, 'generic')
        assert_equal(ds.datasetTypeName, 'Localizations')
    
    # Remove test database file
    remove(str(dbName))'''