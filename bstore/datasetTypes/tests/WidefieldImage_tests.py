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

from nose.tools                    import assert_equal, ok_

# Register the type
from bstore  import config
config.__Registered_DatasetTypes__.append('WidefieldImage')
config.__Registered_DatasetTypes__.append('Localizations')

from bstore.datasetTypes.WidefieldImage import WidefieldImage
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
    dsIDs           = {}
    dsIDs['prefix'] = 'test_prefix'
    dsIDs['acqID']  = 1
    
    WidefieldImage(datasetIDs = dsIDs)
    
def test__repr__():
    """DatasetType generates the correct __repr__ string.
    
    """
    dsIDs           = {}
    dsIDs['prefix'] = 'test_prefix'
    
    ds = WidefieldImage(datasetIDs = dsIDs)
    
    assert_equal(
        ds.__repr__(),
        'WidefieldImage: {\'prefix\': \'test_prefix\'}')
    
    del(ds.datasetIDs['prefix'])
    assert_equal(ds.__repr__(), 'WidefieldImage: {}')

def test_Put_Data():
    """The datasetType can put its own data and datasetIDs.
    
    Notes
    -----
    This also tests that the pixel size is correctly extracted from the
    Micro-Manager metadata.
    
    """
    imgPath = testDataRoot / Path('database_test_files') \
              / Path('Cos7_A647_WF1/') \
              / Path('Cos7_A647_1_MMStack_Pos0.ome.tif')
        
    try:
        # Make up some dataset IDs and a dataset
        parser = parsers.PositionParser(positionIDs = {
                                            0 : 'prefix', 
                                            1 : 'channelID', 
                                            2 : 'acqID'})
        parser.parseFilename(str(imgPath), 'WidefieldImage')
        ds = parser.dataset
        ds.data = ds.readFromFile(str(imgPath), readTiffTags = True)
        
        pathToDB = testDataRoot
        # Remove datastore if it exists
        if exists(str(pathToDB / Path('test_db.h5'))):
            remove(str(pathToDB / Path('test_db.h5')))
        
        myDB = db.HDFDatastore(pathToDB / Path('test_db.h5'))
        myDB.put(ds)
        
        key = 'Cos7/Cos7_1/WidefieldImage_ChannelA647'
        with h5py.File(str(pathToDB / Path('test_db.h5')), 'r') as hdf:
            assert_equal(hdf[key].attrs['SMLM_datasetType'], 'WidefieldImage')
            imgData = hdf[key + '/image_data'].value
            
            assert_equal(hdf[key + '/image_data'].attrs['element_size_um'][0],
                         1)
            assert_equal(hdf[key + '/image_data'].attrs['element_size_um'][1],
                         0)
            assert_equal(hdf[key + '/image_data'].attrs['element_size_um'][2],
                         0)
    
        assert_equal(imgData.shape, (512, 512))
    finally:
        # Remove the test datastore
        remove(str(pathToDB / Path('test_db.h5')))
   
def test_Put_Data_kwarg_WidefieldPixelSize():
    """The WidefieldImage will write the correct pixel size if provided.
    
    """
    # TODO: Rewrite this test to ensure that we really overwrite the metadata
    # pixel size.
    imgPath = testDataRoot / Path('database_test_files') \
              / Path('Cos7_A647_WF1/') \
              / Path('Cos7_A647_1_MMStack_Pos0.ome.tif')
    try:
        # Make up some dataset IDs and a dataset
        parser = parsers.PositionParser(positionIDs = {
                                            0 : 'prefix', 
                                            1 : 'channelID', 
                                            2 : 'acqID'})
        parser.parseFilename(str(imgPath), 'WidefieldImage')
        ds = parser.dataset
        ds.data = ds.readFromFile(str(imgPath), readTiffTags = False)
        
        pathToDB = testDataRoot
        # Remove datastore if it exists
        if exists(str(pathToDB / Path('test_db.h5'))):
            remove(str(pathToDB / Path('test_db.h5')))
        
        myDB = db.HDFDatastore(pathToDB / Path('test_db.h5'))
        myDB.put(ds, widefieldPixelSize = (0.13, 0.14))

        # Note that pixel sizes are saved in zyx order.
        # These values will be equal to 0.108, 0.108 if no widefieldPixelSize
        # is supplied because the default behavior is to read the MM or OME-XML
        # metadata.        
        key = 'Cos7/Cos7_1/WidefieldImage_ChannelA647'
        with h5py.File(str(pathToDB / Path('test_db.h5')), 'r') as hdf:
            assert_equal(hdf[key + '/image_data'].attrs['element_size_um'][0],
                         1)
            assert_equal(hdf[key + '/image_data'].attrs['element_size_um'][1],
                         0.14)
            assert_equal(hdf[key + '/image_data'].attrs['element_size_um'][2],
                         0.13)
    finally:
        # Remove the test datastore
        remove(str(pathToDB / Path('test_db.h5')))
              
def test_Get_Data():
    """The datasetType can get its own data and datasetIDs.
    
    """
    dsID = db.DatasetID
     # Load the datastore
    imgPath = testDataRoot / Path('database_test_files') \
              / Path('Cos7_A647_WF1/') \
              / Path('Cos7_A647_1_MMStack_Pos0.ome.tif')
    img     = imread(str(imgPath))
    try:
        # Make up some dataset IDs and a dataset
        parser = parsers.PositionParser(positionIDs = {
                                            0 : 'prefix', 
                                            1 : 'channelID', 
                                            2 : 'acqID'})
        parser.parseFilename(str(imgPath), 'WidefieldImage')
        ds = parser.dataset
        ds.data = ds.readFromFile(str(imgPath))
        
        pathToDB = testDataRoot
        # Remove datastore if it exists
        if exists(str(pathToDB / Path('test_db.h5'))):
            remove(str(pathToDB / Path('test_db.h5')))
        
        myDB = db.HDFDatastore(pathToDB / Path('test_db.h5'))
        myDB.put(ds, widefieldPixelSize = (0.13, 0.13))
        
        myNewDSID = dsID('Cos7', 1, 'WidefieldImage', None,
                         'A647', None, None, None)
        imgDS = myDB.get(myNewDSID)
        ids     = imgDS.datasetIDs
        assert_equal(ids['prefix'],                     'Cos7')
        assert_equal(ids['acqID'],                           1)
        assert_equal(imgDS.datasetType,       'WidefieldImage')
        assert_equal(ids['channelID'],                  'A647')
        assert_equal(ids['dateID'],                       None)
        assert_equal(ids['posID'],                        None)
        assert_equal(ids['sliceID'],                      None)   
        assert_equal(imgDS.data.shape, img.shape)
    finally:
        # Remove the test datastore
        remove(str(pathToDB / Path('test_db.h5')))

def test_HDF_Datastore_Build():
    """The datastore build is performed successfully.
    
    Notes
    -----
    This also tests that the Micro-Manager metadata is read correctly to obtain
    the widefield image pixel size.
    
    """
    dbName   = testDataRoot / Path('database_test_files/myDB_Build.h5')
    if dbName.exists():
        remove(str(dbName))
    myDB     = db.HDFDatastore(dbName)
    parser = parsers.PositionParser(positionIDs = {
        0 : 'prefix', 
        2 : 'channelID', 
        3 : 'acqID'})
    
    # Directory to traverse for acquisition files
    searchDirectory = testDataRoot / Path('test_experiment')
    
    # Build datastore
    myDB.build(parser, searchDirectory,
               filenameStrings  = {'WidefieldImage' : '.ome.tif',
                                   'Localizations'  : 'locResults.dat'},
               dryRun = False, readTiffTags = True)
               
    # Test for existence of the data.
    # Pixel sizes should have been obtained from Micro-Manager meta data.
    with h5py.File(str(dbName), mode = 'r') as hdf:
        key1 = ('HeLaL/HeLaL_1/WidefieldImage_ChannelA647/'
                'image_data')
        ok_('HeLaL/HeLaL_1/Localizations_ChannelA647' in hdf)
        ok_('HeLaL/HeLaL_1/WidefieldImage_ChannelA647' in hdf)
        ok_('element_size_um' in hdf[key1].attrs)
        assert_equal(hdf[key1].attrs['element_size_um'][0],     1)
        assert_equal(hdf[key1].attrs['element_size_um'][1], 0.108)
        assert_equal(hdf[key1].attrs['element_size_um'][2], 0.108)
        
        key2 = ('HeLaS/HeLaS_2/WidefieldImage_ChannelA647/'
                'image_data')
        ok_('HeLaS/HeLaS_2/Localizations_ChannelA647' in hdf)
        ok_('HeLaS/HeLaS_2/WidefieldImage_ChannelA647' in hdf)
        ok_('element_size_um' in hdf[key2].attrs)
        assert_equal(hdf[key2].attrs['element_size_um'][0],     1)
        assert_equal(hdf[key2].attrs['element_size_um'][1], 0.108)
        assert_equal(hdf[key2].attrs['element_size_um'][2], 0.108)
    
    # Remove test datastore file
    remove(str(dbName))

def test_HDF_Datastore_WidefieldPixelSize_OMEXML_Only():
    """element_size_um is correct when only OME-XML metadata is present."
    
    """
    dbName   = testDataRoot / Path('database_test_files/myDB_Build.h5')
    if dbName.exists():
        remove(str(dbName))
    myDB     = db.HDFDatastore(dbName)
    parser = parsers.PositionParser(positionIDs = {
        0 : 'prefix', 
        1 : 'channelID', 
        2 : 'acqID'})
    
    # Directory to traverse for acquisition files
    searchDirectory = testDataRoot \
                    / Path('database_test_files/OME-TIFF_No_MM_Metadata')
    
    # Build datastore
    myDB.build(parser, searchDirectory,
               filenameStrings  = {'WidefieldImage' : '2_MMStack*.ome.tif'},
               dryRun = False, readTiffTags = True)
    
    # Test for existence of the data
    with h5py.File(str(dbName), mode = 'r') as hdf:
        key1 = ('Cos7/Cos7_2/WidefieldImage_ChannelA647/image_data')
        ok_('Cos7/Cos7_2/WidefieldImage_ChannelA647' in hdf)
        ok_('element_size_um' in hdf[key1].attrs)
        assert_equal(hdf[key1].attrs['element_size_um'][0], 1)
        assert_equal(hdf[key1].attrs['element_size_um'][1], 0.1)
        assert_equal(hdf[key1].attrs['element_size_um'][2], 0.1)
    
    # Remove test datastore file
    remove(str(dbName))

def test_Put_WidefieldImage_TiffFile():
    """Insertion of widefield image data works when parsed as a TiffFile.
    
    """
    # Remake the datastore
    dbName   = testDataRoot / Path('database_test_files/myDB_WF_Metadata.h5')
    if dbName.exists():
        remove(str(dbName))
    myDB     = db.HDFDatastore(dbName)    
    
    # Load the widefield image and convert it to an atom
    f = 'Cos7_A647_1_MMStack_Pos0.ome.tif'
    inputFile = testDataRoot / Path('database_test_files') \
              / Path('Cos7_A647_WF1/') / Path(f)
    
    # Read TiffTags
    parser = parsers.PositionParser(positionIDs = {
        0 : 'prefix', 
        1 : 'channelID', 
        2 : 'acqID'})
    parser.parseFilename(str(inputFile), 'WidefieldImage')
    ds = parser.dataset
    ds.data = ds.readFromFile(str(inputFile), readTiffTags = True)
    
    # Put the widefield image into the datastore
    myDB.put(parser.dataset)
    
    # Check that the data was put correctly
    saveKey = 'Cos7/Cos7_1/WidefieldImage_ChannelA647'
    with h5py.File(myDB._dsName, mode = 'r') as dbFile:
        ok_(saveKey + '/image_data' in dbFile,
            'Error: Could not find widefield image key.')
            
        # Check that metadata was correctly inserted
        ok_(saveKey + '/OME-XML' in dbFile,
            'Error: Could not find OME-XML metadata.')
        ok_(saveKey + '/MM_Metadata' in dbFile,
            'Error: Could not find Micro-Manager metadata.')
        ok_(saveKey + '/MM_Summary_Metadata' in dbFile,
            'Error: Could not find Micro-Manager summary metadata.')

def test_WidefieldImage_DatasetID_Attributes():
    """Dataset IDs are written as attributes of the widefieldImage dataset.
    
    """
    # Remake the datastore
    dbName   = testDataRoot / Path('database_test_files/myDB_WF_Metadata.h5')
    if dbName.exists():
        remove(str(dbName))
    myDB     = db.HDFDatastore(dbName)    
    
    # Load the widefield image and convert it to a dataset
    f = 'Cos7_A647_1_MMStack_Pos0.ome.tif'
    inputFile = testDataRoot / Path('database_test_files') \
              / Path('Cos7_A647_WF1/') / Path(f)
    
    # Set the parser to read TiffTags
    parser = parsers.PositionParser(positionIDs = {
                                            0 : 'prefix', 
                                            1 : 'channelID', 
                                            2 : 'acqID'})
    parser.parseFilename(str(inputFile), 'WidefieldImage')
    ds = parser.dataset
    ds.data = ds.readFromFile(str(inputFile), readTiffTags = False)
    
    # Put the widefield image into the datastore
    myDB.put(parser.dataset)
    
    # Check that the dataset IDs were put correctly
    saveKey = 'Cos7/Cos7_1/WidefieldImage_ChannelA647'
    with h5py.File(myDB._dsName, mode = 'r') as dbFile:
        ok_(dbFile[saveKey].attrs.__contains__('SMLM_prefix'))
        ok_(dbFile[saveKey].attrs.__contains__('SMLM_acqID'))
        ok_(dbFile[saveKey].attrs.__contains__('SMLM_datasetType'))
        ok_(dbFile[saveKey].attrs.__contains__('SMLM_channelID'))
        ok_(dbFile[saveKey].attrs.__contains__('SMLM_dateID'))
        ok_(dbFile[saveKey].attrs.__contains__('SMLM_posID'))
        ok_(dbFile[saveKey].attrs.__contains__('SMLM_sliceID'))
        ok_(dbFile[saveKey].attrs.__contains__('SMLM_Version'))
        
        assert_equal(dbFile[saveKey].attrs['SMLM_prefix'], 'Cos7')
        assert_equal(dbFile[saveKey].attrs['SMLM_acqID'], 1)
        assert_equal(dbFile[saveKey].attrs['SMLM_datasetType'],
                         'WidefieldImage')
        assert_equal(dbFile[saveKey].attrs['SMLM_channelID'], 'A647')
        assert_equal(dbFile[saveKey].attrs['SMLM_dateID'], 'None')
        assert_equal(dbFile[saveKey].attrs['SMLM_posID'], 'None')
        assert_equal(dbFile[saveKey].attrs['SMLM_sliceID'], 'None')

def test_WidefieldImage_Datastore_Query():
    """The datastore query is performed successfully with the datasetType.
    
    """
    dbName   = testDataRoot / Path('database_test_files/myDB_Build.h5')
    if dbName.exists():
        remove(str(dbName))
    myDB     = db.HDFDatastore(dbName)
    myParser = parsers.SimpleParser()    
    
    # Directory to traverse for acquisition files
    searchDirectory = testDataRoot / Path('parsers_test_files/SimpleParser')
    
    # Build datastore
    myDB.build(myParser, searchDirectory,
               filenameStrings  = {'WidefieldImage'  : '.tif'},
               dryRun = False)
    
    results = myDB.query(datasetType = 'WidefieldImage')
    
    ok_(len(results) != 0, 'Error: No dataset types found in DB.')

    # There are 2 widefield images    
    assert_equal(len(results), 2)
    for ds in results:
        assert_equal(ds.datasetType, 'WidefieldImage')
    
    # Remove test datastore file
    remove(str(dbName))