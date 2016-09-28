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

def test_Put_Data():
    """The datasetType can put its own data and datasetIDs.
    
    Notes
    -----
    This also tests that the pixel size is correctly extracted from the
    Micro-Manager metadata.
    
    """
    imgPath = testDataRoot / Path('database_test_files') \
              / Path('Cos7_A647_WF1/') \
              / Path('Cos7_A647_WF1_MMStack_Pos0.ome.tif')
        
    try:
        # Make up some dataset IDs and a dataset
        parser = parsers.MMParser()
        parser.parseFilename(str(imgPath), 'WidefieldImage')
        ds = parser.dataset
        ds.data = ds.readFromFile(str(imgPath), readTiffTags = True)
        
        pathToDB = testDataRoot
        # Remove database if it exists
        if exists(str(pathToDB / Path('test_db.h5'))):
            remove(str(pathToDB / Path('test_db.h5')))
        
        myDB = db.HDFDatabase(pathToDB / Path('test_db.h5'))
        myDB.put(ds)
        
        key = 'Cos7/Cos7_1/WidefieldImage_A647_Pos0'
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
        # Remove the test database
        remove(str(pathToDB / Path('test_db.h5')))
   
def test_Put_Data_kwarg_WidefieldPixelSize():
    """The WidefieldImage will write the correct pixel size if provided.
    
    """
    # TODO: Rewrite this test to ensure that we really overwrite the metadata
    # pixel size.
    imgPath = testDataRoot / Path('test_experiment_2/HeLaS_Control_IFFISH') \
              / Path('HeLaS_Control_IFFISH_A647_WF1') \
              / Path('HeLaS_Control_IFFISH_A647_WF1_MMStack_Pos0.ome.tif')
    try:
        # Make up some dataset IDs and a dataset
        parser = parsers.MMParser()
        parser.parseFilename(str(imgPath), 'WidefieldImage')
        ds = parser.dataset
        ds.data = ds.readFromFile(str(imgPath), readTiffTags = False)
        
        pathToDB = testDataRoot
        # Remove database if it exists
        if exists(str(pathToDB / Path('test_db.h5'))):
            remove(str(pathToDB / Path('test_db.h5')))
        
        myDB = db.HDFDatabase(pathToDB / Path('test_db.h5'))
        myDB.put(ds, widefieldPixelSize = (0.13, 0.14))

        # Note that pixel sizes are saved in zyx order.
        # These values will be equal to 0.108, 0.108 if no widefieldPixelSize
        # is supplied because the default behavior is to read the MM or OME-XML
        # metadata.        
        key = ('HeLaS_Control_IFFISH/HeLaS_Control_IFFISH_1/'
               'WidefieldImage_A647_Pos0')
        with h5py.File(str(pathToDB / Path('test_db.h5')), 'r') as hdf:
            assert_equal(hdf[key + '/image_data'].attrs['element_size_um'][0],
                         1)
            assert_equal(hdf[key + '/image_data'].attrs['element_size_um'][1],
                         0.14)
            assert_equal(hdf[key + '/image_data'].attrs['element_size_um'][2],
                         0.13)
    finally:
        # Remove the test database
        remove(str(pathToDB / Path('test_db.h5')))
              
def test_Get_Data():
    """The datasetType can get its own data and datasetIDs.
    
    """
     # Load the database
    imgPath = testDataRoot / Path('test_experiment_2/HeLaS_Control_IFFISH') \
              / Path('HeLaS_Control_IFFISH_A647_WF1') \
              / Path('HeLaS_Control_IFFISH_A647_WF1_MMStack_Pos0.ome.tif')
    img = imread(str(imgPath))
    try:
        # Make up some dataset IDs and a dataset
        dsIDs           = {}
        dsIDs['prefix'] = 'test_prefix'
        dsIDs['acqID']  = 1
        ds      = WidefieldImage(datasetIDs = dsIDs)
        ds.data = img
        
        pathToDB = testDataRoot
        # Remove database if it exists
        if exists(str(pathToDB / Path('test_db.h5'))):
            remove(str(pathToDB / Path('test_db.h5')))
        
        myDB = db.HDFDatabase(pathToDB / Path('test_db.h5'))
        myDB.put(ds, widefieldPixelSize = (0.13, 0.13))
        
        myNewDSID = myDB.dsID('test_prefix', 1, 'WidefieldImage', None,
                              None, None, None, None)
        imgDS = myDB.get(myNewDSID)
        ids     = imgDS.datasetIDs
        assert_equal(ids['prefix'],              'test_prefix')
        assert_equal(ids['acqID'],                           1)
        assert_equal(imgDS.datasetType,       'WidefieldImage')
        assert_equal(ids['channelID'],                    None)
        assert_equal(ids['dateID'],                       None)
        assert_equal(ids['posID'],                        None)
        assert_equal(ids['sliceID'],                      None)   
        assert_equal(imgDS.data.shape, img.shape)
    finally:
        # Remove the test database
        remove(str(pathToDB / Path('test_db.h5')))

def test_HDF_Database_Build():
    """The database build is performed successfully.
    
    Notes
    -----
    This also tests that the Micro-Manager metadata is read correctly to obtain
    the widefield image pixel size.
    
    """
    dbName   = testDataRoot / Path('database_test_files/myDB_Build.h5')
    if dbName.exists():
        remove(str(dbName))
    myDB     = db.HDFDatabase(dbName)
    myParser = parsers.MMParser()    
    
    # Directory to traverse for acquisition files
    searchDirectory = testDataRoot / Path('test_experiment')
    
    # Build database
    myDB.build(myParser, searchDirectory,
               filenameStrings  = {'WidefieldImage' : '.ome.tif',
                                   'Localizations'  : 'locResults.dat'},
               dryRun = False, readTiffTags = True)
               
    # Test for existence of the data.
    # Pixel sizes should have been obtained from Micro-Manager meta data.
    with h5py.File(str(dbName), mode = 'r') as hdf:
        key1 = ('HeLaL_Control/HeLaL_Control_1/WidefieldImage_A647_Pos0/'
                'image_data')
        ok_('HeLaL_Control/HeLaL_Control_1/Localizations_A647_Pos0' in hdf)
        ok_('HeLaL_Control/HeLaL_Control_1/WidefieldImage_A647_Pos0' in hdf)
        ok_('element_size_um' in hdf[key1].attrs)
        assert_equal(hdf[key1].attrs['element_size_um'][0],     1)
        assert_equal(hdf[key1].attrs['element_size_um'][1], 0.108)
        assert_equal(hdf[key1].attrs['element_size_um'][2], 0.108)
        
        key2 = ('HeLaS_Control/HeLaS_Control_2/WidefieldImage_A647_Pos0/'
                'image_data')
        ok_('HeLaS_Control/HeLaS_Control_2/Localizations_A647_Pos0' in hdf)
        ok_('HeLaS_Control/HeLaS_Control_2/WidefieldImage_A647_Pos0' in hdf)
        ok_('element_size_um' in hdf[key2].attrs)
        assert_equal(hdf[key2].attrs['element_size_um'][0],     1)
        assert_equal(hdf[key2].attrs['element_size_um'][1], 0.108)
        assert_equal(hdf[key2].attrs['element_size_um'][2], 0.108)
    
    # Remove test database file
    remove(str(dbName))

def test_HDF_Database_WidefieldPixelSize_OMEXML_Only():
    """element_size_um is correct when only OME-XML metadata is present."
    
    """
    dbName   = testDataRoot / Path('database_test_files/myDB_Build.h5')
    if dbName.exists():
        remove(str(dbName))
    myDB     = db.HDFDatabase(dbName)
    myParser = parsers.MMParser()    
    
    # Directory to traverse for acquisition files
    searchDirectory = testDataRoot \
                    / Path('database_test_files/OME-TIFF_No_MM_Metadata')
    
    # Build database
    myDB.build(myParser, searchDirectory,
               filenameStrings  = {'WidefieldImage' : '.ome.tif',
                                   'Localizations'  : 'locResults.dat'},
               dryRun = False, readTiffTags = True)
    
    # Test for existence of the data
    with h5py.File(str(dbName), mode = 'r') as hdf:
        key1 = ('Cos7/Cos7_2/WidefieldImage_A647_Pos0/image_data')
        ok_('Cos7/Cos7_2/WidefieldImage_A647_Pos0' in hdf)
        ok_('element_size_um' in hdf[key1].attrs)
        assert_equal(hdf[key1].attrs['element_size_um'][0], 1)
        assert_equal(hdf[key1].attrs['element_size_um'][1], 0.1)
        assert_equal(hdf[key1].attrs['element_size_um'][2], 0.1)
    
    # Remove test database file
    remove(str(dbName))

def test_Put_WidefieldImage_TiffFile():
    """Insertion of widefield image data works when parsed as a TiffFile.
    
    """
    # Remake the database
    dbName   = testDataRoot / Path('database_test_files/myDB_WF_Metadata.h5')
    if dbName.exists():
        remove(str(dbName))
    myDB     = db.HDFDatabase(dbName)    
    
    # Load the widefield image and convert it to an atom
    f = 'Cos7_A647_WF1_MMStack_Pos0.ome.tif'
    inputFile = testDataRoot / Path('database_test_files') \
              / Path('Cos7_A647_WF1/') / Path(f)
    
    # Read TiffTags
    mmParser = parsers.MMParser()
    mmParser.parseFilename(inputFile, datasetType = 'WidefieldImage')
    mmParser.dataset.data = mmParser.dataset.readFromFile(inputFile,
                                                          readTiffTags = True)
    
    # Put the widefield image into the database
    myDB.put(mmParser.dataset)
    
    # Check that the data was put correctly
    saveKey = 'Cos7/Cos7_1/WidefieldImage_A647_Pos0'
    with h5py.File(myDB._dbName, mode = 'r') as dbFile:
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
    # Remake the database
    dbName   = testDataRoot / Path('database_test_files/myDB_WF_Metadata.h5')
    if dbName.exists():
        remove(str(dbName))
    myDB     = db.HDFDatabase(dbName)    
    
    # Load the widefield image and convert it to an atom
    f = 'Cos7_A647_WF1_MMStack_Pos0.ome.tif'
    inputFile = testDataRoot / Path('database_test_files') \
              / Path('Cos7_A647_WF1/') / Path(f)
    
    # Set the parser to read TiffTags
    mmParser = parsers.MMParser()
    mmParser.parseFilename(inputFile, 'WidefieldImage')
    mmParser.dataset.data = mmParser.dataset.readFromFile(inputFile,
                                                          readTiffTags = True)
    
    # Put the widefield image into the database
    myDB.put(mmParser.dataset)
    
    # Check that the dataset IDs were put correctly
    saveKey = 'Cos7/Cos7_1/WidefieldImage_A647_Pos0'
    with h5py.File(myDB._dbName, mode = 'r') as dbFile:
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
        assert_equal(dbFile[saveKey].attrs['SMLM_posID'], (0,))
        assert_equal(dbFile[saveKey].attrs['SMLM_sliceID'], 'None')

def test_WidefieldImage_Database_Query():
    """The database query is performed successfully with the datasetType.
    
    """
    dbName   = testDataRoot / Path('database_test_files/myDB_Build.h5')
    if dbName.exists():
        remove(str(dbName))
    myDB     = db.HDFDatabase(dbName)
    myParser = parsers.MMParser()    
    
    # Directory to traverse for acquisition files
    searchDirectory = testDataRoot / Path('test_experiment_2')
    
    # Build database
    myDB.build(myParser, searchDirectory,
               filenameStrings  = {'WidefieldImage'  : '.ome.tif'},
               dryRun = False)
    
    results = myDB.query(datasetType = 'WidefieldImage')
    
    ok_(len(results) != 0, 'Error: No dataset types found in DB.')

    # There are 8 widefield images    
    assert_equal(len(results), 8)
    for ds in results:
        assert_equal(ds.datasetType, 'WidefieldImage')
    
    # Remove test database file
    remove(str(dbName))