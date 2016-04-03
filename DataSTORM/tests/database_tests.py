"""Unit tests for the database module.

Notes
-----
nosetests should be run in the directory just above the `tests` folder.

"""
 
__author__ = 'Kyle M. Douglass'
__email__ = 'kyle.m.douglass@gmail.com'

from nose.tools   import *
from DataSTORM    import database
from pathlib      import Path
from pandas       import DataFrame
from numpy.random import rand
from os           import remove
import h5py

# Test data
data = DataFrame(rand(5,2), columns = ['x', 'y'])
  
def test_Dataset_CompleteSubclass():
    """Dataset instantiation correctly detects complete subclassing.
    
    """    
    myDataset = database.Dataset(1, 'A647', data, (0,),
                                 'HeLa', 1, 'locResults')

@raises(TypeError)    
def test_Dataset_IncompleteSubclass():
    """Dataset instantiation correctly detects an incomplete subclassing.
    
    """
    class Dataset(database.DatabaseAtom):
        def __init__(self, acqID, channelID, data,
                     posID, prefix, sliceID, datasetType):
            super(Dataset, self).__init__(acqID, channelID, data, posID, 
                                          prefix, sliceID, datasetType)
                                                
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
    myDataset = Dataset(1, 'A647', data, (0,), 'HeLa', 1, 'locResults')

@raises(ValueError)
def test_Dataset_NoAcqID():
    """Dataset instantiation correctly detects an acqID of None.
    
    """
    class Dataset(database.DatabaseAtom):
        def __init__(self, acqID, channelID, data, posID,
                     prefix, sliceID, datasetType):
            super(Dataset, self).__init__(acqID, channelID, data, posID,
                                          prefix, sliceID, datasetType)
                                                
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
    myDataset = Dataset(None, 'A647', data, (0,), 'HeLa', 1, 'locResults')

@raises(ValueError)
def test_Dataset_NoDatasetType():
    """Dataset instantiation correctly detects a datasetType of None.
    
    """
    class Dataset(database.DatabaseAtom):
        def __init__(self, acqID, channelID, data, posID,
                     prefix, sliceID, datasetType):
            super(Dataset, self).__init__(acqID, channelID, posID, data,
                                          prefix, sliceID, datasetType)
                                                
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
    myDataset = Dataset(1, 'A647', data, (0,), 'HeLa', 1, None)

        
def test_Database_CompleteSubclass():
    """Database instantiation is complete.
    
    """
    class Database(database.Database):
                                                
        def append(self):
            pass
        
        def build(self):
            pass
        
        def get(self):
            pass

        def put(self):
            pass
    
    dbName = 'myDB.h5'
    myDatabase = Database(dbName)
    
def test_HDFDatabase_KeyGeneration():
    """Key names are generated correctly from DatabaseAtoms.
    
    """
    myDatasets = [
                  database.Dataset(1, 'A647', data, (0,),
                                   'HeLa_Control', None, 'locResults'),
                  database.Dataset(43, None, data, (0,),
                                   'HeLa_Control', None, 'locResults'),
                  database.Dataset(6, None, data, None,
                                   'HeLa_Control', None, 'locResults'),
                  database.Dataset(6, 'Cy5', data, (1,),
                                   'HeLa_Control', 3, 'locResults'),
                  database.Dataset(89, 'DAPI', data, (3, 12),
                                  'HeLa_Control', 46, 'locResults'),
                  database.Dataset(76, 'A750', data, (0,2),
                                   'HeLa_Control', None, 'widefieldImage'),
                  database.Dataset(76, 'A750', data, (0,2),
                                   'HeLa_Control', None, 'locMetadata')
                 ]
                 
    keys       = [
                  'HeLa_Control/HeLa_Control_1/locResults_A647_Pos0',
                  'HeLa_Control/HeLa_Control_43/locResults_Pos0',
                  'HeLa_Control/HeLa_Control_6/locResults',
                  'HeLa_Control/HeLa_Control_6/locResults_Cy5_Pos1_Slice3',
                  'HeLa_Control/HeLa_Control_89' + \
                      '/locResults_DAPI_Pos_003_012_Slice46',
                  'HeLa_Control/HeLa_Control_76' + \
                      '/widefieldImage_A750_Pos_000_002',
                  'HeLa_Control/HeLa_Control_76' + \
                      '/locMetadata_A750_Pos_000_002'
                 ]
    
    dbName = 'myDB.h5'
    myDatabase = database.HDFDatabase(dbName)
    
    for ds, key in zip(myDatasets, keys):
        keyString = myDatabase._genKey(ds)
        assert_equal(keyString, key)
        
def test_HDFDatabase_Put_Keys_AtomicMetadata():
    """Database creates an HDF file with the right keys and atomic metadata.
    
    """
    dbName = Path('./tests/test_files/myDB.h5')
    if dbName.exists():
        remove(str(dbName))
    
    myDB  = database.HDFDatabase(dbName)
    myDS  = database.Dataset(1, 'A647', data, (0,),
                             'Cos7', None, 'locResults')
    myDS2 = database.Dataset(1, 'A647', data, (1,2),
                             'Cos7', None, 'locResults')
    
    myDB.put(myDS)
    myDB.put(myDS2)
    assert_true(dbName.exists())
    
    # Get keys and attributes
    with h5py.File(str(dbName), 'r') as f:
        keys = sorted(list(f['Cos7/Cos7_1'].keys()))
        assert_equal(keys[0], 'locResults_A647_Pos0')
        assert_equal(keys[1], 'locResults_A647_Pos_001_002')
    
        keyString0 = 'Cos7/Cos7_1/' + keys[0]
        assert_equal(f[keyString0].attrs['SMLM_acqID'],                      1)
        assert_equal(f[keyString0].attrs['SMLM_channelID'],             'A647')
        assert_equal(f[keyString0].attrs['SMLM_posID'],                      0)
        assert_equal(f[keyString0].attrs['SMLM_prefix'],                'Cos7')
        assert_equal(f[keyString0].attrs['SMLM_sliceID'],               'None')
        assert_equal(f[keyString0].attrs['SMLM_datasetType'],     'locResults')
        
        keyString1 = 'Cos7/Cos7_1/' + keys[1]
        assert_equal(f[keyString1].attrs['SMLM_acqID'],                      1)
        assert_equal(f[keyString1].attrs['SMLM_channelID'],             'A647')
        assert_equal(f[keyString1].attrs['SMLM_posID'][0],                   1)
        assert_equal(f[keyString1].attrs['SMLM_posID'][1],                   2)
        assert_equal(f[keyString1].attrs['SMLM_prefix'],                'Cos7')
        assert_equal(f[keyString1].attrs['SMLM_sliceID'],               'None')
        assert_equal(f[keyString1].attrs['SMLM_datasetType'],     'locResults')
        f.close()
        
def test_HDFDatabase_Get():
    """HDFDatabase.get() returns the correct Dataset.
    
    """
    dbName   = Path('./tests/test_files/myDB.h5')
    myDB     = database.HDFDatabase(dbName)
     
    # Create an ID with empty data for retrieving the dataset     
    myDSID   = database.Dataset(1, 'A647', None, (0,),
                                'Cos7', None, 'locResults')
    
    # Get the data from the database and compare it to the input data
    retrievedDataset = myDB.get(myDSID)
    ok_((data['x'] == retrievedDataset.data['x']).all())
    ok_((data['y'] == retrievedDataset.data['y']).all())
    
def test_HDFDatabase_Get_Dict():
    """HDFDatabase.get() works when a dict is supplied.
    
    """
    dbName   = Path('./tests/test_files/myDB.h5')
    myDB     = database.HDFDatabase(dbName)
     
    # Create a dict of IDs for retrieving the dataset     
    myDSID   = {
                'acqID'       : 1,
                'channelID'   : 'A647',
                'posID'       : (0,),
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
    """HDFDatabase.get() displays the correct information when KeyError raised.
    
    """
    dbName   = Path('./tests/test_files/myDB.h5')
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