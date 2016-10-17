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

from nose.tools   import assert_equal, assert_true, raises, ok_

# Register the TestType DatasetType
from bstore  import config
config.__Registered_DatasetTypes__.append('TestType')

from bstore       import database, parsers
from pathlib      import Path
from pandas       import DataFrame
from numpy.random import rand
from numpy        import array_equal
from os           import remove
import h5py
import bstore.datasetTypes.TestType as TestType

testDataRoot = Path(config.__Path_To_Test_Data__)

# Flag identifying atomic ID prefix
atomPre = config.__HDF_AtomID_Prefix__

# Flag identifying localization metadata
mdPre = config.__HDF_Metadata_Prefix__

# Test data
data = DataFrame(rand(5,2), columns = ['x', 'y'])

def test_Dataset_IDs():
    """Dataset IDs are assigned correctly.
    
    """
    t = TestType.TestType()
    t.datasetIDs = {'prefix' : 'HeLa', 'acqID' : 1}
    assert_equal(t.datasetIDs['prefix'], 'HeLa')
    assert_equal(t.datasetIDs['acqID'],       1)

@raises(TypeError)    
def test_Dataset_IDs_Bad_Input_Type():
    """Exception is raised when a non-dict is passed to datasetIDs.
    
    """
    t = TestType.TestType()
    t.datasetIDs = 2
    
def test_DatasetIDs_Initialize_With_IDs():
    """Datasets can be initialized with IDs.
    
    """
    t = TestType.TestType(datasetIDs = {'prefix' : 'HeLa', 'acqID' : 1})
    assert_equal(t.datasetIDs['prefix'], 'HeLa')
    assert_equal(t.datasetIDs['acqID'],       1)
    
def test_UnpackDatasetIDs():
    """DatasetIDs are successfully interpreted by the Datastore.
    
    """
    myDB = database.HDFDatastore('test_db.h5')
    
    t1   = TestType.TestType(datasetIDs = {'prefix' : 'HeLa', 'acqID' : 1})
    t2   = TestType.TestType(datasetIDs = {'prefix' : 'HeLa', 'acqID' : 2,
                                           'channelID' : 'A647',
                                           'dateID'    : '2016-09-16',
                                           'posID'     : (0,),
                                           'sliceID'   : 1})
    ids1 = myDB._unpackDatasetIDs(t1)
    ids2 = myDB._unpackDatasetIDs(t2)
    
    # Ground truths
    gt1  = myDB.dsID(prefix = 'HeLa', acqID = 1, datasetType = 'TestType',
                     attributeOf = None, channelID = None, dateID = None,
                     posID = None, sliceID = None)
    gt2  = myDB.dsID(prefix = 'HeLa', acqID = 2, datasetType = 'TestType',
                     attributeOf = None, channelID = 'A647',
                     dateID = '2016-09-16', posID = (0,), sliceID = 1)
    
    assert_equal(ids1, gt1)
    assert_equal(ids2, gt2)
    
@raises(AssertionError)
def test_UnpackDatasetIDs_AcqIDIsNone():
    """HDFDatastore correctly detects an acqID of None.
    
    """
    myDB = database.HDFDatastore('test_db.h5')
    
    t1   = TestType.TestType(datasetIDs = {'prefix' : 'HeLa', 'acqID' : None})
    myDB._unpackDatasetIDs(t1)
    
@raises(AssertionError)
def test_UnpackDatasetIDs_PrefixIsNone():
    """HDFDatastore correctly detects an acqID of None.
    
    """
    myDB = database.HDFDatastore('test_db.h5')
    
    t1   = TestType.TestType(datasetIDs = {'prefix' : None, 'acqID' : 1})
    myDB._unpackDatasetIDs(t1)
    
@raises(database.DatasetIDError)
def test_UnpackDatasetIDs_AcqIDIsMissing():
    """HDFDatastore correctly detects an acqID of None.
    
    """
    myDB = database.HDFDatastore('test_db.h5')
    
    t1   = TestType.TestType(datasetIDs = {'prefix' : 'HeLa'})
    myDB._unpackDatasetIDs(t1)
    
@raises(database.DatasetIDError)
def test_UnpackDatasetIDs_PrefixIsMissing():
    """HDFDatastore correctly detects an acqID of None.
    
    """
    myDB = database.HDFDatastore('test_db.h5')
    
    t1   = TestType.TestType(datasetIDs = {'acqID' : 1})
    myDB._unpackDatasetIDs(t1)

@raises(ValueError)
def test_UnpackDatasetIDs_BadDateFormat():
    """The dataset raises an error when a bad date string is supplied.
    
    """
    myDB = database.HDFDatastore('test_db.h5')
    
    t2   = TestType.TestType(datasetIDs = {'prefix' : 'HeLa', 'acqID' : 2,
                                           'channelID' : 'A647',
                                           # Should be YYYY-MM-DD
                                           'dateID'    : '2016-9-16',
                                           'posID'     : (0,),
                                           'sliceID'   : 1})
    myDB._unpackDatasetIDs(t2)
    
def test_UnpackDatasetIDs_DateIsNone():
    """A dateID of None will not raise an error in _unpackDatasetIDs
    
    """
    myDB = database.HDFDatastore('test_db.h5')
    
    t2   = TestType.TestType(datasetIDs = {'prefix' : 'HeLa', 'acqID' : 2,
                                           'channelID' : 'A647',
                                           'dateID'    : None,
                                           'posID'     : (0,),
                                           'sliceID'   : 1})
    myDB._unpackDatasetIDs(t2)
                                
def test_HDFDatastore__repr__():
    """__repr__() returns the correct string representation.
    
    """
    myDB = database.HDFDatastore('the_name', widefieldPixelSize=(0.108, 0.108))
    assert_equal(myDB.__repr__(),
                 ('HDFDatastore(\'the_name\', '
                  'widefieldPixelSize = (0.1080, 0.1080))'))
                  
    myDB = database.HDFDatastore('the_name')
    assert_equal(myDB.__repr__(),
                 ('HDFDatastore(\'the_name\', '
                  'widefieldPixelSize = None)'))
  
def test_HDFDatastore_KeyGeneration():
    """Key names are generated correctly from Datasets.
    
    """
    myDatasetIDs = [
                  {'prefix' : 'HeLa_Control', 'acqID' : 1,
                   'channelID' : 'A647', 'posID' : (0,)},

                  {'prefix' : 'HeLa_Control', 'acqID' : 43, 'posID' : (0,)},
                   
                  {'prefix': 'HeLa_Control', 'acqID' : 6},

                  {'prefix': 'HeLa_Control', 'acqID' : 6,
                   'channelID' : 'Cy5', 'posID' : (1,),
                   'sliceID'   : 3},
                   
                  {'prefix' : 'HeLa_Control', 'acqID' : 89,
                   'channelID' : 'DAPI', 'posID' : (3, 12),
                   'sliceID' : 46},
                   
                  {'prefix' : 'HeLa_Control', 'acqID' : 76,
                   'channelID' : 'A750', 'posID' : (0,2)},

                  {'prefix' : 'HeLa_Control', 'acqID' : 76,
                   'channelID' : 'A750', 'dateID' : '2016-05-05',
                   'posID' : (0,2)},

                  {'prefix': 'HeLa_Control', 'acqID' : 76,
                   'channelID' : 'A750', 'posID' : (0,2)}
                 ]
     
    # The last one should be locResults and not locMetadata because
    # metadata gets appended to locResults            
    keys       = [
                  'HeLa_Control/HeLa_Control_1/TestType_ChannelA647_Pos0',
                  'HeLa_Control/HeLa_Control_43/TestType_Pos0',
                  'HeLa_Control/HeLa_Control_6/TestType',
                  'HeLa_Control/HeLa_Control_6/TestType_ChannelCy5_Pos1_Slice3',
                  'HeLa_Control/HeLa_Control_89' + \
                      '/TestType_ChannelDAPI_Pos_003_012_Slice46',
                  'HeLa_Control/HeLa_Control_76' + \
                      '/TestType_ChannelA750_Pos_000_002',
                  'HeLa_Control/d2016_05_05/HeLa_Control_76' + \
                      '/TestType_ChannelA750_Pos_000_002',
                  'HeLa_Control/HeLa_Control_76' + \
                      '/TestType_ChannelA750_Pos_000_002'
                 ]
    
    dbName = 'myDB.h5'
    myDatastore = database.HDFDatastore(dbName)
    
    for currID, key in zip(myDatasetIDs, keys):
        ds = TestType.TestType(datasetIDs = currID)
        keyString, _ = myDatastore._genKey(ds)
        assert_equal(keyString, key)

def test_HDFDatastore_genDataset():
    """Empty datasets are generated properly from id tuples.
    
    """
    myDB = database.HDFDatastore('test_db.h5')
    ids  = myDB.dsID('test_prefix', 2, 'TestType', None,
                     'A647', None, (0,), 3)
    
    ds = myDB._genDataset(ids)
    assert_equal(ds.datasetIDs['prefix'], 'test_prefix')
    assert_equal(ds.datasetIDs['acqID'],              2)
    assert_equal(ds.datasetIDs['channelID'],     'A647')
    assert_equal(ds.datasetIDs['dateID'],          None)
    assert_equal(ds.datasetIDs['posID'],           (0,))
    assert_equal(ds.datasetIDs['sliceID'],            3)
    assert_equal(ds.datasetType,         'TestType')
    assert_equal(ds.attributeOf,                   None)
    ok_(isinstance(ds,               TestType.TestType))
             
def test_HDFDatastore_Put_Keys_DatastoreMetadata():
    """Datastore creates an HDF file with the right keys and metadata.
    
    """
    dbName = testDataRoot / Path('database_test_files/myDB.h5')
    if dbName.exists():
        remove(str(dbName))
    
    myDB  = database.HDFDatastore(dbName)
    myDS  = TestType.TestType(datasetIDs = {'prefix' : 'Cos7', 'acqID' : 1,
                                   'channelID' : 'A647', 'posID' : (0,)})
    myDS2 = TestType.TestType(datasetIDs = {'prefix' : 'Cos7', 'acqID' : 1, 
                                   'channelID' : 'A647', 'posID' : (1,2)})
    myDS3 = TestType.TestType(datasetIDs = {'prefix' : 'Cos7', 'acqID' : 1,
                                   'channelID' : 'A647',
                                   'dateID' : '2016-05-05', 'posID' : (1,2)})
    myDS.data  = data.as_matrix()
    myDS2.data = data.as_matrix()
    myDS3.data = data.as_matrix()
    
    myDB.put(myDS)
    myDB.put(myDS2)
    myDB.put(myDS3)
    assert_true(dbName.exists())
    
    # Get keys and attributes
    with h5py.File(str(dbName), 'r') as f:
        keys = sorted(list(f['Cos7/Cos7_1'].keys()))
        assert_equal(keys[0], 'TestType_ChannelA647_Pos0')
        assert_equal(keys[1], 'TestType_ChannelA647_Pos_001_002')
    
        keyString0 = 'Cos7/Cos7_1/' + keys[0]
        assert_equal(f[keyString0].attrs[atomPre + 'acqID'],                 1)
        assert_equal(f[keyString0].attrs[atomPre + 'channelID'],        'A647')
        assert_equal(f[keyString0].attrs[atomPre + 'posID'],                 0)
        assert_equal(f[keyString0].attrs[atomPre + 'prefix'],           'Cos7')
        assert_equal(f[keyString0].attrs[atomPre + 'sliceID'],          'None')
        assert_equal(f[keyString0].attrs[atomPre + 'datasetType'],  'TestType')
        
        keyString1 = 'Cos7/Cos7_1/' + keys[1]
        assert_equal(f[keyString1].attrs[atomPre + 'acqID'],                 1)
        assert_equal(f[keyString1].attrs[atomPre + 'channelID'],        'A647')
        assert_equal(f[keyString1].attrs[atomPre + 'posID'][0],              1)
        assert_equal(f[keyString1].attrs[atomPre + 'posID'][1],              2)
        assert_equal(f[keyString1].attrs[atomPre + 'prefix'],           'Cos7')
        assert_equal(f[keyString1].attrs[atomPre + 'sliceID'],          'None')
        assert_equal(f[keyString1].attrs[atomPre + 'datasetType'],  'TestType')
        
        keyString2 = 'Cos7/d2016_05_05/Cos7_1/' + keys[1]
        assert_equal(f[keyString2].attrs[atomPre + 'acqID'],                 1)
        assert_equal(f[keyString2].attrs[atomPre + 'channelID'],        'A647')
        assert_equal(f[keyString2].attrs[atomPre + 'posID'][0],              1)
        assert_equal(f[keyString2].attrs[atomPre + 'posID'][1],              2)
        assert_equal(f[keyString2].attrs[atomPre + 'prefix'],           'Cos7')
        assert_equal(f[keyString2].attrs[atomPre + 'sliceID'],          'None')
        assert_equal(f[keyString2].attrs[atomPre + 'datasetType'],  'TestType')

def test_HDFDatastore_GetWithDate():
    """HDFDatastore.get() returns the correct Dataset with a dateID.
    
    """
    dbName   = testDataRoot / Path('database_test_files/myDB.h5')
    # Created in test_HDFDatastore_Put_Keys_AtomicMetadata()  
    myDB     = database.HDFDatastore(dbName)
     
    # Create an ID with empty data for retrieving the dataset     
    myDS = myDB.dsID('Cos7', 1, 'TestType', None,
                     'A647', '2016-05-05', (1,2), None)
    
    # Get the data from the datastore and compare it to the input data
    retrievedDataset = myDB.get(myDS)
    ok_(array_equal(retrievedDataset.data, data))

def test_HDFDatastore_Iterable():
    """HDFDatastore acts as an interable over dataset IDs.
    
    """
    dsName = testDataRoot / Path(('parsers_test_files/SimpleParser/'
                                  'test_id_collection_temp.h5'))
    if dsName.exists():
        remove(str(dsName))
    myDS = database.HDFDatastore(dsName)
    
    temp = config.__Registered_DatasetTypes__.copy()
    config.__Registered_DatasetTypes__ = [
        'Localizations', 'LocMetadata', 'WidefieldImage']   
    
    # Create ground-truth IDs
    gt = [myDS.dsID(name, acqID, dsType, attr, None, None, None, None)
          for name, acqID in [('HeLaL_Control', 1), ('HeLaS_Control', 2)]
          for dsType, attr in [('Localizations', None),
                               ('LocMetadata', 'Localizations'),
                               ('WidefieldImage', None)]]
        
    parser = parsers.SimpleParser()
    filenameStrings = {
        'Localizations'  : '.csv',
        'LocMetadata'    : '.txt',
        'WidefieldImage' : '.tif'}
    myDS.build(parser, dsName.parent, filenameStrings, readTiffTags = False)

    assert_equal(len(myDS), 6)
    for ds in myDS:
        ok_(ds in gt, 'Error: DatasetID not found in Datastore')
        
    # Indexing works
    ok_(myDS[0] != myDS[1])
        
    # Clean-up the file and reset the registered types
    config.__Registered_DatasetTypes__ = temp
    if dsName.exists():
        remove(str(dsName))
        
@raises(database.HDF5KeyExists)
def test_HDF_Datastore_Check_Key_Existence():
    """An error is raised if using a key that already exists for locResults.
    
    """
    # Remake the datastore
    dbName = testDataRoot / Path('database_test_files/myDB_DoubleKey.h5')
    if dbName.exists():
        remove(str(dbName))
    myDS    = database.HDFDatastore(dbName)
    ds      = TestType.TestType(datasetIDs = {
        'prefix' : 'Cos7', 'acqID' : 1, 'channelID' : 'A647', 'posID' : (0,)})
    ds.data = data
                             
    # Raises error on the second put because the key already exists.
    myDS.put(ds)
    myDS.put(ds)