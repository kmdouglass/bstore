from abc import ABCMeta, abstractproperty

class DatabaseAtom(metaclass = ABCMeta):
    def __init__(self, acqID, channelID, posID, prefix, sliceID, datasetType):
        if acqID is None:
            raise ValueError('acqID cannot be \'None\'.')
                
        if datasetType is None:
            raise ValueError('datasetType cannot be \'None\'.')
            
        self._acqID       = acqID
        self._channelID   = channelID
        self._posID       = posID
        self._prefix      = prefix
        self._slice       = sliceID
        self._datasetType = datasetType
        
    @abstractproperty
    def acqID(self):
        pass
    
    @abstractproperty
    def channelID(self):
        pass
    
    @abstractproperty
    def posID(self):
        pass
    
    @abstractproperty
    def prefix(self):
        pass
    
    @abstractproperty
    def sliceID(self):
        pass
    
    @abstractproperty
    def datasetType(self):
        pass