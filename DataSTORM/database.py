from pathlib import PurePath
from abc import ABCMeta, abstractmethod, abstractproperty
from pandas import HDFStore, read_hdf
import h5py
import json
import DataSTORM.config as config
import sys

# TODO: Move this to config.py
typesOfAtoms = (
                'locResults',
                'locMetadata',
                'widefieldImage'
               )

def _checkType(typeString):
    if typeString not in typesOfAtoms:
        raise DatasetError('Invalid datasetType; \'{:s}\' provided.'.format(
                                                                   typeString))
                                                                  
import os
def touch(fname, mode=0o666, dir_fd=None, **kwargs):
    """Implements UNIX touch routine.
    
    touch() is used to create an empty HDF database or update its timestamps.
    
    References
    ----------
    http://stackoverflow.com/questions/1158076/implement-touch-using-python
    
    """
    # TODO: Test this on Windows
    flags = os.O_CREAT | os.O_APPEND
    with os.fdopen(os.open(fname, flags=flags, mode=mode, dir_fd=dir_fd)) as f:
        os.utime(f.fileno() if os.utime in os.supports_fd else fname,
            dir_fd=None if os.supports_fd else dir_fd, **kwargs)

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
    @property
    def atomPrefix(self):
        return config.__HDF_AtomID_Prefix__
    
    def append(self):
        raise NotImplementedError
    
    def build(self, parser, searchDirectory,
              locResultsString = 'locResults.dat',
              locMetadataString = 'locMetadata.json',
              widefieldImageString = '*WF*.ome.tiff'):
        """Builds a database by traversing a directory for experimental files.
        
        Parameters
        ----------
        parser               : Parser
            Instance of a parser for converting files to DatabaseAtoms.
        searchDirectory      : str or Path
            This directory and all subdirectories will be traversed.
        locResultsString     : str
            String that identifies locResults files.
        locMetadataString    : str
            String that identifies locMetadata files.
        widefieldImageString : str
            Glob string that identifies widefield images.
            
        """
        # Should call self.put() repeatedly for a list of atomic inputs.
        raise NotImplementedError
        
        searchDirectory   = Path(searchDirectory)
        locResultFilesGen = searchDirectory.glob('**/*{:s}'.format(locResultsString))
        locResultFiles    = sorted(locResultFilesGen)
        
    def _checkKeyExistence(self, atom):
        """Checks for the existence of a key.
        
        Parameters
        ----------
        atom : DatabaseAtom
        
        """
        key = self._genKey(atom)        
        
        # If Database file doesn't exist, return without checking
        try:
            with h5py.File(self._dbName, mode = 'r') as dbFile:
                if key in dbFile and atom.datasetType != 'locMetadata':
                    raise HDF5KeyExists(('Error: '
                                         '{0:s} already exists.'.format(key)))
                elif key in dbFile and atom.datasetType == 'locMetadata':
                    # Search for metadata flag presence in locResults dataset
                    attrID = config.__HDF_Metadata_Prefix__                 
                    mdKeys = dbFile[key].attrs.keys()
                    for currKey in mdKeys:
                        if attrID in currKey:
                            raise HDF5KeyExists(('Error: '
                                                 '{0:s} already '
                                                 'exists.'.format(key)))                    
        except IOError as e:
            print('Error: Could not open file.')
            print(e.args)

    def _genKey(self, atom):
        """Generate a key name for a dataset atom.
        
        Parameters
        ----------
        atoms  : DatabaseAtom
        
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
        
        # locMetadata should be appended to a dataset starting with locResults
        if atom.datasetType != 'locMetadata':        
            return acqKey + '/' + atom.datasetType + otherIDs
        else:
            return acqKey + '/locResults' + otherIDs
            
    def _getLocMetadata(self, hdfKey):
        """Returns the primary dataset ID's used by DataSTORM.
        
        Parameters
        ----------
        hdfKey : str
            The key in the hdf file containing the dataset.

        
        Returns
        -------
        md     : dict
            Metadata as key value pairs. All values are strings compatible
            with Python's JSON's dump.
        """
        try:
            # Open the HDF file and get the dataset's attributes
            hdf      = h5py.File(self._dbName, mode = 'r')
            attrKeys = hdf[hdfKey].attrs.keys()
            attrID   = config.__HDF_Metadata_Prefix__
            md = {}            
            
            # Currently h5py raises IOError when attributes are empty.
            # See https://github.com/h5py/h5py/issues/279
            # For this reason, I can't use a simple list comprehension
            # with a filter over attrs.items() to get the metadata.
            for currAttr in attrKeys:
                try:
                    # Filter out attributes irrelevant to the database.
                    # Also remove the database's attribute flag.
                    if currAttr[:len(attrID)] == attrID:
                        print(currAttr)
                        sys.stdout.flush()
                        md[currAttr[len(attrID):]] = \
                                        json.loads(hdf[hdfKey].attrs[currAttr])
                except IOError:
                    # Ignore attirbutes that are empty.
                    # See above comment.
                    pass
                        
            # TODO: Check that SMLM Metadata matches key.
                        
        finally:
            hdf.close()
            
        return md
    
    def _putLocMetadata(self, atom):
        """Writes localization metadata into the database.
        
        Parameters
        ----------
        atom   : DatabaseAtom
            
        """
        mdFlag = config.__HDF_Metadata_Prefix__
        
        assert atom.datasetType == 'locMetadata', \
            'Error: atom\'s datasetType is not \'locMetadata\''
        dataset = self._genKey(atom)
        
        try:
            hdf = h5py.File(self._dbName, mode = 'a')
                
            # Loop through metadata and write each attribute to the key
            for currKey in atom.data.keys():
                attrKey = '{0:s}{1:s}'.format(mdFlag, currKey)
                attrVal = json.dumps(atom.data[currKey])
                hdf[dataset].attrs[attrKey] = attrVal
        except KeyError:
            # Raised when the hdf5 key does not exist in the database.
            raise LocResultsDoNotExist(('Error: Cannot not append metadata. '
                                        'No localization results exist with '
                                        'these atomic IDs.'))
        finally:
            hdf.close()
            
    def _putWidefieldImage(self, atom):
        """Writes a widefield image into the database.
        
        Parameters
        ----------
        atom   : DatabaseAtom
        """
        assert atom.datasetType == 'widefieldImage', \
            'Error: atom\'s datasetType is not \'widefieldImage\''
        dataset = self._genKey(atom) + '/widefield_' + atom.channelID
        
        try:
            hdf = h5py.File(self._dbName, mode = 'a')
            
            hdf.create_dataset(dataset,
                               atom.data.shape,
                               data = atom.data)
        finally:
            hdf.close()
        
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
                       'The following keys may be incorrect:'))
                print(e.args)
                raise
        else:
            acqID, channelID, posID, prefix, sliceID, datasetType = \
                                                                 dsID.getInfo()
            
        # Use returnDS to get the key pointing to the dataset
        returnDS = Dataset(acqID, channelID, None, posID,
                           prefix, sliceID, datasetType)
        hdfKey   = self._genKey(returnDS)

        # Ensure that the key exists        
        try:
            self._checkKeyExistence(returnDS)
        except HDF5KeyExists:
            pass
        
        if datasetType == 'locResults':
            returnDS.data = read_hdf(self._dbName, key = hdfKey)
        if datasetType == 'locMetadata':
            returnDS.data = self._getLocMetadata(hdfKey)
        if datasetType == 'widefieldImage':
            raise NotImplementedError
            
        return returnDS
        
    def put(self, atom):
        """Writes a single database atom into the database.
        
        Parameters
        ----------
        atom   : DatabaseAtom
        
        """
        self._checkKeyExistence(atom)
        key = self._genKey(atom)
        
        # The put routine varies with atom's dataset type
        # TODO: Check the input DataFrame's columns for compatibility.
        if atom.datasetType == 'locResults':
            try:
                hdf = HDFStore(self._dbName)
                hdf.put(key, atom.data, format = 'table',
                        data_columns = True, index = False)
            finally:
                hdf.close()
                
            # Write the attributes to the dataset;
            # h5py can't convert None values natively
            # Reopening the file just to write attributes is awkward;
            # Can attributes be written through the HDFStore interface?
            try:
                atomPrefix = self.atomPrefix
                hdf        = h5py.File(self._dbName, mode = 'a')
                
                hdf[key].attrs[atomPrefix + 'acqID']       = atom.acqID
                hdf[key].attrs[atomPrefix + 'channelID']   = \
                    'None' if atom.channelID is None else atom.channelID
                hdf[key].attrs[atomPrefix + 'posID']       = \
                    'None' if atom.posID is None else atom.posID
                hdf[key].attrs[atomPrefix + 'prefix']      = atom.prefix
                hdf[key].attrs[atomPrefix + 'sliceID']     = \
                    'None' if atom.sliceID is None else atom.sliceID
                hdf[key].attrs[atomPrefix + 'datasetType'] = atom.datasetType
                
                # Current version of this software
                hdf[key].attrs[atomPrefix +'Version'] = \
                                                   config.__DataSTORM_Version__
            finally:
                hdf.close()
        elif atom.datasetType == 'locMetadata':
            self._putLocMetadata(atom)
        elif atom.datasetType == 'widefieldImage':
            self._putWidefieldImage(atom)
            
class LocResultsDoNotExist(Exception):
    """Attempting to attach locMetadata to non-existing locResults.
    
    """
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)
        
class HDF5KeyExists(Exception):
    """Attempting to write to an existing key in the database.
    
    """
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)