from pathlib import PurePath, Path
from abc import ABCMeta, abstractmethod, abstractproperty
from pandas import HDFStore

class DatabaseAtom(metaclass = ABCMeta):
    """Represents one organizational unit in the database.
    
    """
    def __init__(self, acqID, channelID, data,
                 posID, prefix, sliceID, datasetType):
        if acqID is None:
            raise ValueError('acqID cannot be \'None\'.')
                
        if datasetType is None:
            raise ValueError('datasetType cannot be \'None\'.')
            
        if datasetType not in ['locResults','locMetadata','widefieldImage']:
            raise ValueError('Invalid datasetType; \'{:s}\' provided.'.format(
                                                                  datasetType))
            
        self._acqID       = acqID
        self._channelID   = channelID
        self._data        = data
        self._posID       = posID
        self._prefix      = prefix
        self._sliceID     = sliceID
        self._datasetType = datasetType
        
    @abstractproperty
    def acqID(self):
        pass
    
    @abstractproperty
    def channelID(self):
        pass
    
    @abstractproperty
    def data(self):
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
    
class Database(metaclass = ABCMeta):
    """Represents the database structure.
    
    Terminology is meant to mirror Pandas HDFStore API where methods
    are similar.
    
    """
    def __init__(self, dbName):
        """Initialize the database.
        
        Parameters
        ----------
        dbName : str or Path
        
        """
        # Convert Path objects to strings
        if isinstance(dbName, PurePath):
            dbName = str(dbName.name)
            
        self._dbName = dbName
    
    @abstractmethod
    def append(self):
        """Append data to a database atom.
        
        """
        pass
    
    @abstractmethod
    def build(self):
        """Create new database from a list of atoms.
        
        """
        pass
    
    @abstractmethod
    def get(self):
        """Retrieve database atom from the database.
        
        """
        pass    
    
    @abstractmethod
    def put(self):
        """Place a database atom into the database.
        
        """
        pass

class Dataset(DatabaseAtom):
    """A concrete realization of a DatabaseAtom.
    
    """
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

class HDFDatabase(Database):
    """An HDFDatabase structure for managing SMLM data.
    
    """
    def append(self):
        raise NotImplementedError
    
    def build(self):
        # Should call self.put() repeatedly for a list of atomic inputs.
        raise NotImplementedError

    def _genKey(self, atom, idFlag = ''):
        """Generate a key name for a dataset atom.
        
        Parameters
        ----------
        atoms       : DatabaseAtom
        idFlag : str
        
        """
        acqKey    = '/'.join([atom.prefix, atom.prefix]) + \
                    '_' + str(atom.acqID)
                                 
        otherIDs = ''
        if atom.channelID is not None:
            otherIDs += '_' + atom.channelID
        if atom.posID is not None:
            if len(atom.posID) == 1:
                posID = atom.posID[0]    
                otherIDs += '_Pos{:d}'.format(posID)
            else:
                otherIDs += '_Pos_{0:0>3d}_{1:0>3d}'.format(atom.posID[0], 
                                                            atom.posID[1])
        if atom.sliceID is not None:
            otherIDs += '_Slice{:d}'.format(atom.sliceID)
            
        return acqKey + '/' + atom.datasetType + otherIDs
        
    def get(self):
        raise NotImplementedError
        
    def put(self, atom, idFlag = ''):
        """Writes a single database atom into the database.
        
        Parameters
        ----------
        atom   : DatabaseAtom
        idFlag : str
            Any additional information to place into the key of the
            HDF dataset.
        
        """
        # The put routine varies with atom's dataset type
        if atom.datasetType == 'locResults':
            key = self._genKey(atom, idFlag)
            
            try:
                hdf = HDFStore(self._dbName)
                hdf.put(key, atom.data, format = 'table',
                        data_columns = True, index = False)
            except:
                hdf.close()