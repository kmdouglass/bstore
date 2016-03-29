from nose.tools import *
from DataSTORM  import batch
from pathlib    import Path
    
def test_Dataset_CompleteSubclass():
    """Dataset correctly detects complete subclassing.
    
    """
    class DataSTORM_Dataset(batch.Dataset):
        def __init__(self, acqID, channelID, posID,
                     prefix, sliceID, datasetType):
            super(DataSTORM_Dataset, self).__init__(acqID, channelID, posID,
                                                    prefix, sliceID,
                                                    datasetType)
                                                
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
    
    myDataset = DataSTORM_Dataset(1, 'A647', (0,), 'HeLa', 1, 'locResults')
    
def test_Dataset_IncompleteSubclass():
    """Dataset correctly detects an incomplete subclassing.
    
    """
    class DataSTORM_Dataset(batch.Dataset):
        def __init__(self, acqID, channelID, posID,
                     prefix, sliceID, datasetType):
            super(DataSTORM_Dataset, self).__init__(acqID, channelID, posID,
                                                    prefix, sliceID,
                                                    datasetType)
                                                
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
        myDataset = DataSTORM_Dataset(1, 'A647', (0,), 'HeLa', 1, 'locResults')
    except TypeError:
        # Incomplete substantiation throws a TypeError
        pass
    else:
        # Raise an exception because no error was detected,
        # even though a TypeError should have been raised.
        raise Exception('TypeError was not thrown.')
    