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
    class Dataset(database.DatabaseAtom):
        def __init__(self, acqID, channelID, data,
                     posID, prefix, sliceID, datasetType):
            super(Dataset, self).__init__(acqID, channelID, data, posID,
                                          prefix, sliceID, datasetType)
                                                
        @property
        def acqID(self):
            return self._acqID
        
        @property
        def channelID(self):
            return self._channelID

        @property
        def data(self):
            return self._data
        
        @property
        def posID(self):
            return self._posID

        @property
        def prefix(self):
            return self._prefix
        
        @property
        def sliceID(self):
            return self._sliceID
        
        @property
        def datasetType(self):
            return self._datasetType
    
    myDatasets = [
                  Dataset(1, 'A647', data, (0,),
                         'HeLa_Control', None, 'locResults'),
                  Dataset(43, None, data, (0,),
                          'HeLa_Control', None, 'locResults'),
                  Dataset(6, None, data, None,
                          'HeLa_Control', None, 'locResults'),
                  Dataset(6, 'Cy5', data, (1,),
                          'HeLa_Control', 3, 'locResults'),
                  Dataset(89, 'DAPI', data, (3, 12),
                          'HeLa_Control', 46, 'locResults')
                 ]
                 
    keys       = [
                  'HeLa_Control/HeLa_Control_1/locs_A647_Pos0',
                  'HeLa_Control/HeLa_Control_43/locs_Pos0',
                  'HeLa_Control/HeLa_Control_6/locs',
                  'HeLa_Control/HeLa_Control_6/locs_Cy5_Pos1_Slice3',
                  'HeLa_Control/HeLa_Control_89/locs_DAPI_Pos_003_012_Slice46'
                 ]
    
    dbName = 'myDB.h5'
    myDatabase = database.HDFDatabase(dbName)
    
    for ds, key in zip(myDatasets, keys):
        keyString = myDatabase._genKey(ds, 'locs')
        assert_equal(keyString, key)