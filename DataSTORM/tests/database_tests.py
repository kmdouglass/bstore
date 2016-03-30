from nose.tools import *
from DataSTORM  import database
from pathlib    import Path
from pandas     import DataFrame
from numpy.random import rand
  
# Test data
data = DataFrame(rand(10,2))
  
def test_Dataset_CompleteSubclass():
    """Dataset instantiation correctly detects complete subclassing.
    
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
    
    myDataset = Dataset(1, 'A647', data, (0,), 'HeLa', 1, 'locResults')
    
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

    try:
        myDataset = Dataset(1, 'A647', data, (0,), 'HeLa', 1, 'locResults')
    except TypeError:
        # Incomplete substantiation throws a TypeError
        pass
    else:
        # Raise an exception because no error was detected,
        # even though a TypeError should have been raised.
        raise Exception('TypeError was not thrown.')

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

    try:
        myDataset = Dataset(None, 'A647', data, (0,), 'HeLa', 1, 'locResults')
    except ValueError:
        # acqID = None throws an error.
        pass
    else:
        # Raise an exception because no error was detected,
        # even though a ValueError should have been raised.
        raise Exception('ValueError was not thrown.')
        
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

    try:
        myDataset = Dataset(1, 'A647', data, (0,), 'HeLa', 1, None)
    except ValueError:
        # datasetType = None throws an error.
        pass
    else:
        # Raise an exception because no error was detected,
        # even though a ValueError should have been raised.
        raise Exception('ValueError was not thrown.')
        
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