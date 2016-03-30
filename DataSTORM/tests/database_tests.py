from nose.tools import *
from DataSTORM  import database
from pathlib    import Path
    
def test_Dataset_CompleteSubclass():
    """Dataset instantiation correctly detects complete subclassing.
    
    """
    class Dataset(database.DatabaseAtom):
        def __init__(self, acqID, channelID, posID,
                     prefix, sliceID, datasetType):
            super(Dataset, self).__init__(acqID, channelID, posID, prefix,
                                          sliceID, datasetType)
                                                
        @property
        def acqID(self):
            pass
        
        @property
        def channelID(self):
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
    
    myDataset = Dataset(1, 'A647', (0,), 'HeLa', 1, 'locResults')
    
def test_Dataset_IncompleteSubclass():
    """Dataset instantiation correctly detects an incomplete subclassing.
    
    """
    class Dataset(database.DatabaseAtom):
        def __init__(self, acqID, channelID, posID,
                     prefix, sliceID, datasetType):
            super(Dataset, self).__init__(acqID, channelID, posID, prefix,
                                          sliceID, datasetType)
                                                
        @property
        def acqID(self):
            pass
        
        @property
        def channelID(self):
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
        myDataset = Dataset(1, 'A647', (0,), 'HeLa', 1, 'locResults')
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
        def __init__(self, acqID, channelID, posID,
                     prefix, sliceID, datasetType):
            super(Dataset, self).__init__(acqID, channelID, posID, prefix,
                                          sliceID, datasetType)
                                                
        @property
        def acqID(self):
            pass
        
        @property
        def channelID(self):
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
        myDataset = Dataset(None, 'A647', (0,), 'HeLa', 1, 'locResults')
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
        def __init__(self, acqID, channelID, posID,
                     prefix, sliceID, datasetType):
            super(Dataset, self).__init__(acqID, channelID, posID, prefix,
                                          sliceID, datasetType)
                                                
        @property
        def acqID(self):
            pass
        
        @property
        def channelID(self):
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
        myDataset = Dataset(1, 'A647', (0,), 'HeLa', 1, None)
    except ValueError:
        # datasetType = None throws an error.
        pass
    else:
        # Raise an exception because no error was detected,
        # even though a ValueError should have been raised.
        raise Exception('ValueError was not thrown.')