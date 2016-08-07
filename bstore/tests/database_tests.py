# © All rights reserved. ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Switzerland, Laboratory of Experimental Biophysics, 2016
# See the LICENSE.txt file for more details.

"""Unit tests for the database module.

Notes
-----
nosetests should be run in the directory just above the `tests` folder.

"""
 
__author__ = 'Kyle M. Douglass'
__email__ = 'kyle.m.douglass@gmail.com'

from nose.tools   import *
from bstore       import database, parsers, config
from pathlib      import Path
from pandas       import DataFrame
from numpy.random import rand
from os           import remove
import h5py

testDataRoot = Path(config.__Path_To_Test_Data__)

# Flag identifying atomic ID prefix
atomPre = config.__HDF_AtomID_Prefix__

# Flag identifying localization metadata
mdPre = config.__HDF_Metadata_Prefix__

# Test data
data = DataFrame(rand(5,2), columns = ['x', 'y'])
  
def test_Dataset_CompleteSubclass():
    """Dataset instantiation correctly detects complete subclassing.
    
    """    
    myDataset = database.Dataset('HeLa', 1, 'locResults', data,
                                 channelID = 'A647',
                                 posID     = (0,),
                                 sliceID   = 1)

@raises(TypeError)    
def test_Dataset_IncompleteSubclass():
    """Dataset instantiation correctly detects an incomplete subclassing.
    
    """
    class Dataset(database.DatabaseAtom):
        """A concrete realization of a DatabaseAtom.
    
        """
        def __init__(self, prefix, acqID, datasetType, data,
                     channelID = None, posID = None, sliceID = None):
            super(Dataset, self).__init__(prefix, acqID, datasetType, data,
                                          channelID = channelID,
                                          posID     = posID,
                                          sliceID   = sliceID)
                                                
        @property
        def acqID(self):
            pass
        
        @property
        def channelID(self):
            pass
        
        @property
        def data(self):
            pass
        
        # posID not defined: Should throw an error
        # @property
        # def posID(self):
        #    pass

        @property
        def prefix(self):
            pass
        
        @property
        def sliceID(self):
            pass
        
        @property
        def datasetType(self):
            pass

    # Should raise a TypeError because posID is not defined.
    myDataset = Dataset('HeLa', 1, 'locResults', data,
                        channelID = 'A647',
                        posID     = (0,),
                        sliceID   = 1)

@raises(ValueError)
def test_Dataset_NoAcqID():
    """Dataset instantiation correctly detects an acqID of None.
    
    """
    class Dataset(database.DatabaseAtom):
        def __init__(self, prefix, acqID, datasetType, data,
                     channelID = None, posID = None, sliceID = None):
            super(Dataset, self).__init__(prefix, acqID, datasetType, data,
                                          channelID = channelID,
                                          posID     = posID,
                                          sliceID   = sliceID)
                                                
        @property
        def acqID(self):
            pass
        
        @property
        def channelID(self):
            pass
        
        @property
        def data(self):
            pass
        
        @property
        def dateID(self):
            pass
        
        @property
        def posID(self):
            pass

        @property
        def prefix(self):
            pass
        
        @property
        def sliceID(self):
            pass
        
        @property
        def datasetType(self):
            pass

    # Should raise ValueError because acqID is None.
    myDataset = Dataset('HeLa', None, 'locResults', data,
                        channelID = 'A647',
                        posID     = (0,),
                        sliceID   = 1)

@raises(ValueError)
def test_Dataset_NoDatasetType():
    """Dataset instantiation correctly detects a datasetType of None.
    
    """
    class Dataset(database.DatabaseAtom):
        def __init__(self, prefix, acqID, datasetType, data,
                     channelID = None, posID = None, sliceID = None):
            super(Dataset, self).__init__(prefix, acqID, datasetType, data,
                                          channelID = channelID,
                                          posID     = posID,
                                          sliceID   = sliceID)
                                                
        @property
        def acqID(self):
            pass
        
        @property
        def channelID(self):
            pass
        
        @property
        def data(self):
            pass
        
        @property
        def dateID(self):
            pass
        
        @property
        def posID(self):
            pass

        @property
        def prefix(self):
            pass
        
        @property
        def sliceID(self):
            pass
        
        @property
        def datasetType(self):
            pass

    # Should throw ValueError because datasetType is None.
    myDataset = Dataset('HeLa', 1, None, data,
                        channelID = 'A647',
                        posID     = (0,),
                        sliceID   = 1)

@raises(ValueError)
def test_Dataset_BadDateFormat():
    """The dataset raises an error when a bad date string is supplied.
    
    """
    myDataset = database.Dataset('HeLa', 1, 'locResults', data,
                                  channelID = 'A647',
                                  # Should be 2016-06-01
                                  dateID    = '2016-06-1', 
                                  posID     = (0,),
                                  sliceID   = 1)
                                  
def test_Dataset_GoodDateFormat():
    """The dataset accepts a good date string.
    
    """
    myDataset = database.Dataset('HeLa', 1, 'locResults', data,
                                  channelID = 'A647',
                                  dateID    = '2016-06-01', 
                                  posID     = (0,),
                                  sliceID   = 1)
                                  
    ok_(myDataset.dateID == '2016-06-01')
                                  
def test_Database_CompleteSubclass():
    """Database instantiation is complete.
    
    """
    class Database(database.Database):
        
        def build(self):
            pass
        
        def get(self):
            pass

        def put(self):
            pass
        
        def query(self):
            pass
    
    dbName = 'myDB.h5'
    myDatabase = Database(dbName)
    
def test_HDFDatabase_KeyGeneration():
    """Key names are generated correctly from DatabaseAtoms.
    
    """
    myDatasets = [
                  database.Dataset('HeLa_Control', 1, 'locResults', data,
                                   channelID = 'A647',
                                   posID     = (0,)),
                  database.Dataset('HeLa_Control', 43, 'locResults', data,
                                   posID = (0,)),
                  database.Dataset('HeLa_Control', 6, 'locResults', data),
                  database.Dataset('HeLa_Control', 6, 'locResults', data,
                                   channelID = 'Cy5',
                                   posID     = (1,),
                                   sliceID   = 3),
                  database.Dataset('HeLa_Control', 89, 'locResults', data,
                                   channelID = 'DAPI',
                                   posID = (3, 12),
                                   sliceID = 46),
                  database.Dataset('HeLa_Control', 76, 'widefieldImage', data,
                                   channelID = 'A750',
                                   posID = (0,2)),
                  database.Dataset('HeLa_Control', 76, 'widefieldImage', data,
                                   channelID = 'A750',
                                   dateID    = '2016-05-05',
                                   posID = (0,2)),
                  database.Dataset('HeLa_Control', 76, 'locMetadata', data,
                                   channelID = 'A750',
                                   posID = (0,2))
                 ]
     
    # The last one should be locResults and not locMetadata because
    # metadata gets appended to locResults            
    keys       = [
                  'HeLa_Control/HeLa_Control_1/locResults_A647_Pos0',
                  'HeLa_Control/HeLa_Control_43/locResults_Pos0',
                  'HeLa_Control/HeLa_Control_6/locResults',
                  'HeLa_Control/HeLa_Control_6/locResults_Cy5_Pos1_Slice3',
                  'HeLa_Control/HeLa_Control_89' + \
                      '/locResults_DAPI_Pos_003_012_Slice46',
                  'HeLa_Control/HeLa_Control_76' + \
                      '/widefieldImage_A750_Pos_000_002',
                  'HeLa_Control/d2016_05_05/HeLa_Control_76' + \
                      '/widefieldImage_A750_Pos_000_002',
                  'HeLa_Control/HeLa_Control_76' + \
                      '/locResults_A750_Pos_000_002'
                 ]
    
    dbName = 'myDB.h5'
    myDatabase = database.HDFDatabase(dbName)
    
    for ds, key in zip(myDatasets, keys):
        keyString = myDatabase._genKey(ds)
        assert_equal(keyString, key)
        
def test_HDFDatabase_Put_Keys_AtomicMetadata():
    """Database creates an HDF file with the right keys and atomic metadata.
    
    """
    dbName = testDataRoot / Path('database_test_files/myDB.h5')
    if dbName.exists():
        remove(str(dbName))
    
    myDB  = database.HDFDatabase(dbName)
    myDS  = database.Dataset('Cos7', 1, 'locResults', data,
                             channelID = 'A647',
                             posID     = (0,))
    myDS2 = database.Dataset('Cos7', 1, 'locResults', data, 
                             channelID = 'A647',
                             posID     = (1,2))
    myDS3 = database.Dataset('Cos7', 1, 'locResults', data, 
                             channelID = 'A647',
                             dateID    = '2016-05-05',
                             posID     = (1,2))
    
    myDB.put(myDS)
    myDB.put(myDS2)
    myDB.put(myDS3)
    assert_true(dbName.exists())
    
    # Get keys and attributes
    with h5py.File(str(dbName), 'r') as f:
        keys = sorted(list(f['Cos7/Cos7_1'].keys()))
        assert_equal(keys[0], 'locResults_A647_Pos0')
        assert_equal(keys[1], 'locResults_A647_Pos_001_002')
    
        keyString0 = 'Cos7/Cos7_1/' + keys[0]
        assert_equal(f[keyString0].attrs[atomPre + 'acqID'],                 1)
        assert_equal(f[keyString0].attrs[atomPre + 'channelID'],        'A647')
        assert_equal(f[keyString0].attrs[atomPre + 'posID'],                 0)
        assert_equal(f[keyString0].attrs[atomPre + 'prefix'],           'Cos7')
        assert_equal(f[keyString0].attrs[atomPre + 'sliceID'],          'None')
        assert_equal(f[keyString0].attrs[atomPre + 'datasetType'],'locResults')
        
        keyString1 = 'Cos7/Cos7_1/' + keys[1]
        assert_equal(f[keyString1].attrs[atomPre + 'acqID'],                 1)
        assert_equal(f[keyString1].attrs[atomPre + 'channelID'],        'A647')
        assert_equal(f[keyString1].attrs[atomPre + 'posID'][0],              1)
        assert_equal(f[keyString1].attrs[atomPre + 'posID'][1],              2)
        assert_equal(f[keyString1].attrs[atomPre + 'prefix'],           'Cos7')
        assert_equal(f[keyString1].attrs[atomPre + 'sliceID'],          'None')
        assert_equal(f[keyString1].attrs[atomPre + 'datasetType'],'locResults')
        
        keyString2 = 'Cos7/d2016_05_05/Cos7_1/' + keys[1]
        assert_equal(f[keyString2].attrs[atomPre + 'acqID'],                 1)
        assert_equal(f[keyString2].attrs[atomPre + 'channelID'],        'A647')
        assert_equal(f[keyString2].attrs[atomPre + 'posID'][0],              1)
        assert_equal(f[keyString2].attrs[atomPre + 'posID'][1],              2)
        assert_equal(f[keyString2].attrs[atomPre + 'prefix'],           'Cos7')
        assert_equal(f[keyString2].attrs[atomPre + 'sliceID'],          'None')
        assert_equal(f[keyString2].attrs[atomPre + 'datasetType'],'locResults')
        f.close()

def test_HDFDatabase_Get():
    """HDFDatabase.get() returns the correct Dataset.
    
    """
    dbName   = testDataRoot / Path('database_test_files/myDB.h5')
    # Created in test_HDFDatabase_Put_Keys_AtomicMetadata()    
    myDB     = database.HDFDatabase(dbName)
    
    # Create an ID with empty data for retrieving the dataset     
    myDSID   = database.Dataset('Cos7', 1, 'locResults', None,
                                channelID = 'A647',
                                posID     = (0,))
    
    # Get the data from the database and compare it to the input data
    retrievedDataset = myDB.get(myDSID)
    ok_((data['x'] == retrievedDataset.data['x']).all())
    ok_((data['y'] == retrievedDataset.data['y']).all())
    
def test_HDFDatabase_GetWithDate():
    """HDFDatabase.get() returns the correct Dataset with a dateID.
    
    """
    dbName   = testDataRoot / Path('database_test_files/myDB.h5')
    # Created in test_HDFDatabase_Put_Keys_AtomicMetadata()  
    myDB     = database.HDFDatabase(dbName)
     
    # Create an ID with empty data for retrieving the dataset     
    myDSID   = database.Dataset('Cos7', 1, 'locResults', None,
                                channelID = 'A647',
                                dateID    = '2016-05-05',
                                posID     = (1,2))
    
    # Get the data from the database and compare it to the input data
    retrievedDataset = myDB.get(myDSID)
    ok_((data['x'] == retrievedDataset.data['x']).all())
    ok_((data['y'] == retrievedDataset.data['y']).all())
    
def test_HDFDatabase_Get_Dict():
    """HDFDatabase.get() works when a dict is supplied.
    
    """
    dbName   = testDataRoot / Path('database_test_files/myDB.h5')
    myDB     = database.HDFDatabase(dbName)
     
    # Create a dict of IDs for retrieving the dataset     
    myDSID   = {
                'acqID'       : 1,
                'channelID'   : 'A647',
                'dateID'      : '2016-05-05',
                'posID'       : (1,2),
                'prefix'      : 'Cos7',
                'sliceID'     : None,
                'datasetType' : 'locResults'
                }
    
    # Get the data from the database and compare it to the input data
    retrievedDataset = myDB.get(myDSID)
    ok_((data['x'] == retrievedDataset.data['x']).all())
    ok_((data['y'] == retrievedDataset.data['y']).all())

@raises(KeyError)    
def test_HDFDatabase_Get_Dict_KeyError():
    """HDFDatabase.get() detects when KeyError raised.
    
    """
    dbName   = testDataRoot / Path('database_test_files/myDB.h5')
    myDB     = database.HDFDatabase(dbName)
     
    # Create a dict of IDs for retrieving the dataset     
    myDSID   = {
                'acqID'       : 1,
                'channelID'   : 'A647',
                'posID'       : (0,),
                'prefix'      : 'Cos7',
                #'sliceID'     : None,
                'datasetType' : 'locResults'
                }
    
    # Should raise a key error because sliceID is not defined in myDSID
    retrievedDataset = myDB.get(myDSID)
    
def test_HDFDatabase_Put_LocMetadata():
    """HDFDatabase correctly places metadata into the database.
    
    """
    dbName   = testDataRoot / Path('database_test_files/myDB.h5')
    myDB     = database.HDFDatabase(dbName)

    # Load a json metadata file
    f           = 'HeLa_Control_A750_2_MMStack_Pos0_locMetadata.json'
    inputFile   = testDataRoot / Path('database_test_files') / Path(f)
    datasetType = 'locMetadata'
    mmParser    = parsers.MMParser()
    mmParser.parseFilename(inputFile, datasetType)
    
    # Create the dataset; locMetadata needs locResults, so put those first
    dsLocs = database.Dataset(mmParser.prefix, mmParser.acqID, 'locResults',
                              data,
                              channelID = mmParser.channelID,
                              posID     = mmParser.posID, 
                              sliceID   = mmParser.sliceID, )
    dsMeta = database.Dataset(mmParser.prefix, mmParser.acqID,
                              mmParser.datasetType, mmParser.data,
                              channelID = mmParser.channelID,
                              posID     = mmParser.posID, 
                              sliceID   = mmParser.sliceID, )
                          
    # Write the metadata into the database
    myDB.put(dsLocs)
    myDB.put(dsMeta)
    
    # Read a few of the attributes to ensure they were put correctly
    hdf = h5py.File(str(dbName), 'r')
    putKey = 'HeLa_Control/HeLa_Control_2/locResults_A750_Pos0'
    assert_equal(hdf[putKey].attrs[mdPre + 'MetadataVersion'],            '10')
    assert_equal(hdf[putKey].attrs[mdPre + 'Height'],                    '512')
    assert_equal(hdf[putKey].attrs[mdPre + 'Frames'],                    '100')
    
def test_HDF_Database_Get_LocMetadata():
    """The database can return localization metadata with get().
    
    """
    dbName   = testDataRoot / Path('database_test_files/myDB.h5')
    myDB     = database.HDFDatabase(dbName)
    
    # Create a dict of IDs for retrieving the dataset     
    myDSID   = {
                'acqID'       : 2,
                'channelID'   : 'A750',
                'dateID'      : None,
                'posID'       : (0,),
                'prefix'      : 'HeLa_Control',
                'sliceID'     : None,
                'datasetType' : 'locMetadata'
                }
    
    md = myDB.get(myDSID)
    
    # Check that the basic ID information is correct.
    assert_equal(md.acqID,                   2)
    assert_equal(md.channelID,          'A750')
    assert_equal(md.posID,                (0,))
    assert_equal(md.prefix,     'HeLa_Control')
    assert_equal(md.sliceID,              None)
    assert_equal(md.datasetType, 'locMetadata')
    
    # Check a few of the metadata tags
    assert_equal(md.data['BitDepth'], 8)
    assert_equal(md.data['KeepShutterOpenChannels'], False)
    assert_equal(md.data['InitialPositionList'], \
                                        {"Label": "Pos0",
                                         "GridRowIndex": 0,
                                         "DeviceCoordinatesUm": {"Z": [0],
                                                                 "XY": [0, 0]},
                                         "GridColumnIndex": 0})
    
@raises(database.LocResultsDoNotExist)
def test_HDF_Database_Put_LocMetadata_Without_LocResults():
    """locMetadata atom cannot be put if localization data doesn't exist.
    
    """
    dbName = testDataRoot / Path('database_test_files/myEmptyDB.h5')
    if dbName.exists():
        remove(str(dbName))
        
    myEmptyDB     = database.HDFDatabase(dbName)

    # Load a json metadata file
    f           = 'HeLa_Control_A750_2_MMStack_Pos0_locMetadata.json'
    inputFile   = testDataRoot / Path('database_test_files') / Path(f)
    datasetType = 'locMetadata'
    mmParser    = parsers.MMParser()
    mmParser.parseFilename(inputFile, datasetType)
    
    # Create the dataset
    dsMeta = database.Dataset(mmParser.prefix, mmParser.acqID,
                              mmParser.datasetType, mmParser.data,
                              channelID = mmParser.channelID,
                              posID     = mmParser.posID, 
                              sliceID   = mmParser.sliceID, )
                          
    # Write the metadata into the database; should raise LocResultsDoNotExist
    myEmptyDB.put(dsMeta)
    
def test_HDF_Database_Put_WidefieldImage():
    """The HDF database puts widefield images with the correct key.
    
    """
    # Load the database
    dbName   = testDataRoot / Path('database_test_files/myDB.h5')
    myDB     = database.HDFDatabase(dbName)
    
    # Load the widefield image and convert it to an atom
    f = 'Cos7_A647_WF1_MMStack_Pos0.ome.tif'
    inputFile = testDataRoot / Path('database_test_files') \
              / Path('Cos7_A647_WF1/') / Path(f)
    datasetType = 'widefieldImage'
    mmParser = parsers.MMParser()
    mmParser.parseFilename(inputFile, datasetType)
    
    # Put the widefield image into the database
    myDB.put(mmParser.getDatabaseAtom())
    
    # Check that the data was put correctly
    saveKey = 'Cos7/Cos7_1/widefieldImage_A647_Pos0/image_data'
    with h5py.File(myDB._dbName, mode = 'r') as dbFile:
        ok_(saveKey in dbFile, 'Error: Could not find widefield image key.')
        
def test_HDF_Database_Get_WidefieldImage():
    """A widefield image is properly retrieved from the database.
    
    """
     # Load the database
    dbName   = testDataRoot / Path('database_test_files/myDB.h5')
    myDB     = database.HDFDatabase(dbName)
    
    # Create a dict of IDs for retrieving the dataset     
    myDSID   = {
                'acqID'       : 1,
                'channelID'   : 'A647',
                'dateID'      : None,
                'posID'       : (0,),
                'prefix'      : 'Cos7',
                'sliceID'     : None,
                'datasetType' : 'widefieldImage'
                }
    
    img = myDB.get(myDSID)
    assert_equal(img.data.shape, (512, 512))
        
def test_HDF_Database_Put_WidefieldImage_TiffFile():
    """Insertion of widefield image data works when parsed as a TiffFile.
    
    """
    # Remake the database
    dbName   = testDataRoot / Path('database_test_files/myDB_WF_Metadata.h5')
    if dbName.exists():
        remove(str(dbName))
    myDB     = database.HDFDatabase(dbName)    
    
    # Load the widefield image and convert it to an atom
    f = 'Cos7_A647_WF1_MMStack_Pos0.ome.tif'
    inputFile = testDataRoot / Path('database_test_files') \
              / Path('Cos7_A647_WF1/') / Path(f)
    datasetType = 'widefieldImage'
    
    # Set the parser to read TiffTags
    mmParser = parsers.MMParser(readTiffTags = True)
    mmParser.parseFilename(inputFile, datasetType)
    
    # Put the widefield image into the database
    myDB.put(mmParser.getDatabaseAtom())
    
    # Check that the data was put correctly
    saveKey = 'Cos7/Cos7_1/widefieldImage_A647_Pos0'
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
            
def test_HDF_Database_WidefieldImage_DatasetID_Attributes():
    """Dataset IDs are written as attributes of the widefieldImage dataset.
    
    """
    # Remake the database
    dbName   = testDataRoot / Path('database_test_files/myDB_WF_Metadata.h5')
    if dbName.exists():
        remove(str(dbName))
    myDB     = database.HDFDatabase(dbName)    
    
    # Load the widefield image and convert it to an atom
    f = 'Cos7_A647_WF1_MMStack_Pos0.ome.tif'
    inputFile = testDataRoot / Path('database_test_files') \
              / Path('Cos7_A647_WF1/') / Path(f)
    datasetType = 'widefieldImage'
    
    # Set the parser to read TiffTags
    mmParser = parsers.MMParser(readTiffTags = True)
    mmParser.parseFilename(inputFile, datasetType)
    
    # Put the widefield image into the database
    myDB.put(mmParser.getDatabaseAtom())
    
    # Check that the dataset IDs were put correctly
    saveKey = 'Cos7/Cos7_1/widefieldImage_A647_Pos0'
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
        assert_equal(dbFile[saveKey].attrs['SMLM_datasetType'],'widefieldImage')
        assert_equal(dbFile[saveKey].attrs['SMLM_channelID'], 'A647')
        assert_equal(dbFile[saveKey].attrs['SMLM_dateID'], 'None')
        assert_equal(dbFile[saveKey].attrs['SMLM_posID'], (0,))
        assert_equal(dbFile[saveKey].attrs['SMLM_sliceID'], 'None')
     
@raises(database.HDF5KeyExists)
def test_HDF_Database_Check_Key_Existence_LocResults():
    """An error is raised if using a key that already exists for locResults.
    
    """
    # Remake the database
    dbName = testDataRoot / Path('database_test_files/myDB_DoubleKey.h5')
    if dbName.exists():
        remove(str(dbName))
    myDB     = database.HDFDatabase(dbName)
    
    myDS  = database.Dataset('Cos7', 1, 'locResults', data,
                             channelID = 'A647',
                             posID = (0,))
                             
    # Raises error on the second put because the key already exists.
    myDB.put(myDS)
    myDB.put(myDS)
    
@raises(database.HDF5KeyExists)
def test_HDF_Database_Check_Key_Existence_LocMetadata():
    """An error is raised if using a key that already exists for locMetadata.
    
    """
    dbName   = testDataRoot / Path('database_test_files/myDB.h5')
    if dbName.exists():
        remove(str(dbName))
    myDB     = database.HDFDatabase(dbName)

    # Load a json metadata file
    f           = 'HeLa_Control_A750_2_MMStack_Pos0_locMetadata.json'
    inputFile   = testDataRoot / Path('database_test_files') / Path(f)
    datasetType = 'locMetadata'
    mmParser    = parsers.MMParser()
    mmParser.parseFilename(inputFile, datasetType)
    
    # Create the dataset; locMetadata needs locResults, so put those first
    dsLocs = database.Dataset(mmParser.prefix, mmParser.acqID, 'locResults',
                              data,
                              channelID = mmParser.channelID,
                              posID     = mmParser.posID, 
                              sliceID   = mmParser.sliceID)
    dsMeta = database.Dataset(mmParser.prefix, mmParser.acqID, 
                              mmParser.datasetType, mmParser.data,
                              channelID = mmParser.channelID,
                              posID     = mmParser.posID, 
                              sliceID   = mmParser.sliceID)
                          
    # Write the metadata into the database
    myDB.put(dsLocs)
    myDB.put(dsMeta)
    
    # Should raise error because metadata exists already
    myDB.put(dsMeta)

@raises(database.HDF5KeyExists)    
def test_HDF_Database_Check_Key_Existence_WidefieldImage():
    """An error is raised if using a key that already exists for widefieldImage
    
    """
    # Load the database
    dbName   = testDataRoot / Path('database_test_files/myDB.h5')
    myDB     = database.HDFDatabase(dbName)
    
    # Load the widefield image and convert it to an atom
    f = 'Cos7_A647_WF1_MMStack_Pos0.ome.tif'
    inputFile = testDataRoot / Path('database_test_files') \
              / Path('Cos7_A647_WF1/') / Path(f)
    datasetType = 'widefieldImage'
    mmParser = parsers.MMParser()
    mmParser.parseFilename(inputFile, datasetType)
    
    myDB.put(mmParser.getDatabaseAtom())
    
    # Should raise an error because the dataset is inserted twice.
    myDB.put(mmParser.getDatabaseAtom())

def test_HDF_Database_Build():
    """The database build is performed successfully.
    
    """
    dbName   = testDataRoot / Path('database_test_files/myDB_Build.h5')
    if dbName.exists():
        remove(str(dbName))
    myDB = database.HDFDatabase(dbName)
    myParser = parsers.MMParser()    
    
    # Directory to traverse for acquisition files
    searchDirectory = testDataRoot / Path('test_experiment')
    
    # Build database
    myDB.build(myParser, searchDirectory, dryRun = False)
    
    # Test for existence of the data
    with h5py.File(str(dbName), mode = 'r') as hdf:
        key1 = 'HeLaL_Control/HeLaL_Control_1/locResults_A647_Pos0'
        ok_('HeLaL_Control/HeLaL_Control_1/locResults_A647_Pos0' in hdf)
        ok_('HeLaL_Control/HeLaL_Control_1/widefieldImage_A647_Pos0' in hdf)
        ok_(hdf[key1].attrs.__contains__('SMLM_acqID'))
        ok_(hdf[key1].attrs.__contains__('SMLM_Metadata_Height'))
        
        key2 = 'HeLaS_Control/HeLaS_Control_2/locResults_A647_Pos0'
        ok_('HeLaS_Control/HeLaS_Control_2/locResults_A647_Pos0' in hdf)
        ok_('HeLaS_Control/HeLaS_Control_2/widefieldImage_A647_Pos0' in hdf)
        ok_(hdf[key2].attrs.__contains__('SMLM_acqID'))
        ok_(hdf[key2].attrs.__contains__('SMLM_Metadata_Height'))
    
    # Remove test database file
    remove(str(dbName))
    
def test_HDF_Database_GenAtomicID():
    """The database can generate the proper atomic IDs from input keys.
    
    """
    myDB = database.HDFDatabase('')
    
    testKey1 = 'HeLaL_Control/HeLaL_Control_1/locResults_A647_Pos0'
    id1      = myDB._genAtomicID(testKey1)
    assert_equal(id1.acqID,                  1)
    assert_equal(id1.channelID,         'A647')
    assert_equal(id1.posID,               (0,))
    assert_equal(id1.prefix,   'HeLaL_Control')
    assert_equal(id1.sliceID,             None)
    assert_equal(id1.datasetType, 'locResults')
    
    testKey2 = ('HeLaL_Control_WT/HeLaL_Control_WT_1/'
                'locResults_A750_Pos_001_021_Slice23')
    id2      = myDB._genAtomicID(testKey2)
    assert_equal(id2.acqID,                   1)
    assert_equal(id2.channelID,          'A750')
    assert_equal(id2.posID,              (1,21))
    assert_equal(id2.prefix, 'HeLaL_Control_WT')
    assert_equal(id2.sliceID,                23)
    assert_equal(id2.datasetType,  'locResults')
    
    testKey3 = 'HeLa/HeLaL_14/locResults_Slice5'
    id3      = myDB._genAtomicID(testKey3)
    assert_equal(id3.acqID,                 14)
    assert_equal(id3.channelID,           None)
    assert_equal(id3.posID,               None)
    assert_equal(id3.prefix,            'HeLa')
    assert_equal(id3.sliceID,                5)
    assert_equal(id3.datasetType, 'locResults')