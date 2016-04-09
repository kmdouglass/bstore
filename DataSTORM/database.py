from pathlib import PurePath, Path
from abc import ABCMeta, abstractmethod, abstractproperty
from pandas import HDFStore, read_hdf
import h5py
import json

typesOfAtoms = (
                'locResults',
                'locMetadata',
                'widefieldImage'
               )

def _checkType(typeString):
    if typeString not in typesOfAtoms:
        raise DatasetError('Invalid datasetType; \'{:s}\' provided.'.format(
                                                                  datasetType))

class DatasetError(Exception):
    """Error raised when a bad datasetType is passed.
    
    """
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class DatabaseAtom(metaclass = ABCMeta):
    """Represents one organizational unit in the database.
    
    """
    def __init__(self, acqID, channelID, data,
                 posID, prefix, sliceID, datasetType):
        if acqID is None:
            raise ValueError('acqID cannot be \'None\'.')
                
        if datasetType is None:
            raise ValueError('datasetType cannot be \'None\'.')
            
        _checkType(datasetType)
            
        self._acqID       = acqID
        self._channelID   = channelID
        self._data        = data
        self._posID       = posID
        self._prefix      = prefix
        self._sliceID     = sliceID
        self._datasetType = datasetType
        
    def getInfo(self):
        """Returns the dataset information (without the data) as a tuple.
        
        """
        return self._acqID, self._channelID, self._posID, \
               self._prefix, self._sliceID, self._datasetType
        
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
            dbName = str(dbName)
            
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
    
    @data.setter
    def data(self, value):
        self._data = value
    
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
        atoms  : DatabaseAtom
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
        if idFlag != '':
            otherIDs += idFlag
        
        # locMetadata should be appended to a key starting with locResults
        if atom.datasetType != 'locMetadata':        
            return acqKey + '/' + atom.datasetType + otherIDs
        else:
            return acqKey + '/locResults' + otherIDs
        
    def get(self, dsID):
        """Returns an atomic dataset matching dsID from the database.
        
        Parameters
        ----------
        dsID  : dict or DatabaseAtom
            Either key-value pairs uniquely identifying the dataset in
            the database or a DatabaseAtom with a possibly empty 'data'
            field that may be used to identify the dataset.
            
        Returns
        -------
        returnDS : Dataset
        
        """
        if not isinstance(dsID, DatabaseAtom):
            try:
                acqID       = dsID['acqID']
                channelID   = dsID['channelID']
                posID       = dsID['posID']
                prefix      = dsID['prefix']
                sliceID     = dsID['sliceID']
                datasetType = dsID['datasetType']
            except KeyError as e:
                print(('There is an error with the dict supplied to get(). '
                       'Were the following keys supplied?'))
                print(e.args)
                raise
        else:
            acqID, channelID, posID, prefix, sliceID, datasetType = \
                                                                 dsID.getInfo()
            
        # Use returnAtom to get the key pointing to the dataset
        returnDS = Dataset(acqID, channelID, None, posID,
                           prefix, sliceID, datasetType)
        hdfKey   = self._genKey(returnDS)
        
        if datasetType == 'locResults':
            returnDS.data = read_hdf(self._dbName, key = hdfKey)
            
        return returnDS
        
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
                
            # Write the attributes to the dataset;
            # h5py can't convert None values natively
            # Reopening the file just to write attributes is awkward;
            # Can attributes be written through the HDFStore interface?
            try:
                hdf = h5py.File(self._dbName, mode = 'a')
                hdf[key].attrs['SMLM_acqID']       = atom.acqID
                hdf[key].attrs['SMLM_channelID']   = \
                    'None' if atom.channelID is None else atom.channelID
                hdf[key].attrs['SMLM_posID']       = \
                    'None' if atom.posID is None else atom.posID
                hdf[key].attrs['SMLM_prefix']      = atom.prefix
                hdf[key].attrs['SMLM_sliceID']     = \
                    'None' if atom.sliceID is None else atom.sliceID
                hdf[key].attrs['SMLM_datasetType'] = atom.datasetType
            except:
                hdf.close()
        elif atom.datasetType == 'locMetadata':
            self._putLocMetadata(atom)
        elif atom.datasetType == 'widefieldImage':
            pass
    
    def _putLocMetadata(self, atom):
        """Writes localization metadata into the database.
        
        Parameters
        ----------
        atom   : DatabaseAtom
            
        """
        assert atom.datasetType == 'locMetadata', \
            'Error: atom\'s datasetType is not \'locMetadata\''
        dataset = self._genKey(atom)
        
        try:
            hdf = h5py.File(self._dbName, mode = 'a')
                
            # Loop through metadata and write each attribute to the key
            for currKey in atom.data.keys():
                attrKey = 'SMLM_{0:s}'.format(currKey)
                attrVal = json.dumps(atom.data[currKey])
                hdf[dataset].attrs[attrKey] = attrVal
        finally:
            hdf.close()