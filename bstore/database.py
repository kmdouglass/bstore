from pathlib import PurePath, Path, PurePosixPath
from abc import ABCMeta, abstractmethod, abstractproperty
from pandas import HDFStore, read_hdf
import h5py
import json
import bstore.config as config
import sys
import pprint
import re
import pandas as pd

pp = pprint.PrettyPrinter(indent=4)  

typesOfAtoms = config.__Types_Of_Atoms__

def _checkType(typeString):
    if typeString not in typesOfAtoms:
        raise DatasetError('Invalid datasetType; \'{:s}\' provided.'.format(
                                                                   typeString))

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
               
    def getInfoDict(self):
        """Returns the dataset information (without the data) as a dict.
        
        """
        atomicIDs = {'acqID'       : self._acqID,
                     'channelID'   : self._channelID,
                     'posID'       : self._posID,
                     'prefix'      : self._prefix,
                     'sliceID'     : self._sliceID,
                     'datasetType' : self._datasetType}
        return atomicIDs
        
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
    
    @abstractmethod
    def query(self):
        """Return a list of atoms in the database.
        
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
    
    def build(self, parser, searchDirectory, dryRun = False,
              locResultsString     = 'locResults.dat',
              locMetadataString    = 'locMetadata.json',
              widefieldImageString = 'WF*.ome.tif'):
        """Builds a database by traversing a directory for experimental files.
        
        Parameters
        ----------
        parser               : Parser
            Instance of a parser for converting files to DatabaseAtoms.
        searchDirectory      : str or Path
            This directory and all subdirectories will be traversed.
        dryRun               : bool
            Test the database build without actually creating the database.
        locResultsString     : str
            String that identifies locResults files.
        locMetadataString    : str
            String that identifies locMetadata files.
        widefieldImageString : str
            Glob string that identifies widefield images.
            
        Returns
        -------
        buildResults : DataFrame
            A sorted DataFrame for investigating what files were actually
            added to the database.
            
        """       
        # Obtain a list of all the files to put into the database
        searchDirectory = Path(searchDirectory)
        FilesGen = {}
        FilesGen['locResults']     = searchDirectory.glob('**/*{:s}'.format(
                                                             locResultsString))
        FilesGen['locMetadata']    = searchDirectory.glob('**/*{:s}'.format(
                                                            locMetadataString))
        FilesGen['widefieldImage'] = searchDirectory.glob('**/*{:s}'.format(
                                                         widefieldImageString))
                                                         
        # Build the dictionary of files with keys describing
        # their dataset type
        files = {}                                                 
        for datasetType in typesOfAtoms:
            files[datasetType] = sorted(FilesGen[datasetType])
        
        # Keep a running record of what datasets were parsed
        datasets = []        
        
        # Ensure that locResults get put first so the metadata has
        # a place to go.
        try:
            for dataset in files['locResults']:
                parser.parseFilename(dataset, datasetType = 'locResults')
                
                if not dryRun:
                    self.put(parser.getDatabaseAtom())
                    
                datasets.append(parser.getBasicInfo())
            
            # Place all other data into the database
            del(files['locResults'])
            for currType in files.keys(): 
                
                for currFile in files[currType]:
                    parser.parseFilename(currFile, datasetType = currType)
                    
                    if not dryRun:
                        self.put(parser.getDatabaseAtom())
                        
                    datasets.append(parser.getBasicInfo())
        except:
            import sys
            print("Unexpected error:", sys.exc_info()[0])
        finally:
            # Report on all the datasets that were parsed
            buildResults = self._sortDatasets(datasets)
            
            if buildResults is not None:
                print('{0:d} files were successfully parsed.'.format(
                                                            len(buildResults)))
            else:
                print('0 files were successfully parsed.')
                
            return buildResults
    
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
        except IOError:
            pass
            
    def _genAtomicID(self, key):
        """Generates an atomic ID from a HDF key. The inverse of _genKey.
        
        Parameters
        ----------
        key : str
            A key pointing to a dataset in the HDF file.
            
        Returns
        -------
        returnDS : Dataset
            The ID's of one database atom. No data is returned or read,
            just the ID information.
            
        """
        
        # Parse key for atomic IDs
        splitStr    = key.split(sep = '/')
        prefix      = splitStr[0]
        acqID       = int(splitStr[1].split(sep = '_')[-1])
        
        otherIDs    = splitStr[2]
        datasetType = otherIDs.split('_')[0]
        data        = None
        
        channelID = [channel
                     for channel in config.__Channel_Identifier__.keys()
                     if channel in otherIDs]
        assert (len(channelID) <= 1), channelID
        try:
            channelID       = channelID[0]
        except IndexError:
            # When there is no channel identifier found, set it to None
            channelID = None
        
        # Obtain the position ID using regular expressions
        # First, extract strings like 'Pos0' or 'Pos_003_002
        positionRaw = re.search(r'Pos\_\d{1,3}\_\d{1,3}|Pos\d{1,}', otherIDs)
        if positionRaw == None:
            posID = None
        else:
            # Next, extract the digits and convert them to a tuple
            indexes = re.findall(r'\d{1,}', positionRaw.group(0))
            posID   = tuple([int(index) for index in indexes])
        
        # Obtain the slice ID if it exists
        sliceRaw = re.search(r'Slice\d+', otherIDs)
        if sliceRaw == None:
            sliceID = None
        else:
            index = re.findall(r'\d+', sliceRaw.group(0))
            sliceID = int(index[0])
        
        returnDS = Dataset(acqID, channelID, data, posID,
                           prefix, sliceID, datasetType)
        return returnDS

    def _genKey(self, atom):
        """Generate a key name for a dataset atom. The inverse of _genAtomicID.
        
        Parameters
        ----------
        atoms  : DatabaseAtom
        
        Returns
        -------
        str
        
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
        """Returns the primary dataset ID's used by bstore.
        
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
        
    def _getWidefieldImage(self, hdfKey):
        """Returns the widefield image at the specified key.
        
        Parameters
        ----------
        hdfKey : str
            The key in the hdf file containing the image.
        
        Returns
        -------
        img    : array of int
            The 2D image.
        
        """
        try:
            file = h5py.File(self._dbName, mode = 'r')
            img  = file[hdfKey].value
            return img
        finally:
            file.close()
    
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
            ids = json.dumps(atom.getInfoDict())
            raise LocResultsDoNotExist(('Error: Cannot not append metadata. '
                                        'No localization results exist with '
                                        'these atomic IDs: ' + ids))
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
        dsID       : dict or DatabaseAtom
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
            #TODO: Write test case for this
            hdfKey = hdfKey + '/widefield_' + channelID
            returnDS.data = self._getWidefieldImage(hdfKey)
            
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
        # TODO: Write test case for key collision when overwriting a widefield
        # image
        if atom.datasetType == 'locResults':
            try:
                hdf = HDFStore(self._dbName)
                hdf.put(key, atom.data, format = 'table',
                        data_columns = True, index = False)
            except:
                import sys
                print("Unexpected error:", sys.exc_info()[0])
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
                                                   config.__bstore_Version__
            except:
                import sys
                print("Unexpected error:", sys.exc_info()[0])
            finally:
                hdf.close()
        elif atom.datasetType == 'locMetadata':
            self._putLocMetadata(atom)
        elif atom.datasetType == 'widefieldImage':
            # TODO: widefield images should also have SMLM ID's attached
            # to their parent groups (not datasets)
            self._putWidefieldImage(atom)
            
    def query(self, datasetType = 'locResults'):
        """Returns a set of database atoms inside this database.

        Parameters
        ----------
        datasetType : str
            The type of data to search for.
        
        Returns
        -------
        atomicIDs   : list of Dataset
            All of the atomic ids matching the datasetType
        
        """
        _checkType(datasetType)
        assert 'Metadata' not in datasetType, \
            'Error: Queries cannot be made on metadata.'        
        searchString = datasetType
        
        # Open the hdf file
        f = h5py.File(self._dbName, 'r')
        try:
            # Extract all localization datasets from the HDF5 file by matching
            # each group to the search string.
            # ('table' not in name) excludes the subgroup inside every
            # processed_localization parent group.
            resultGroups = []
            def find_locs(name):
                """Finds localization files matching the name pattern."""
                if (searchString in name) and ('table' not in name):
                    resultGroups.append(name)
            f.visit(find_locs)
        finally:
            f.close()
        
        # Read attributes of each key in resultGroups for SMLM_*
        # and convert them to a datasetAtom ID.
        # Note: If you use Path and Not PurePosixPath, '/' will
        # become '\\' on Windows and you won't get the right keys.
        resultKeys = list(map(PurePosixPath, resultGroups))
        atomicIDs  = [self._genAtomicID(str(key)) for key in resultKeys]
        
        return atomicIDs
        
    def _sortDatasets(self, dsInfo):
        """Sorts and organizes all datasets before a Database build.
        
        _sortDatasets() accepts a list of dicts containing dataset
        information. It then sorts and organizes the information in a
        human-readable format, allowing both humans and computers to
        locate possible errors before and after the database is built.
        
        Parameters
        ----------
        dsInfo : list of dict
            Each element of dsInfo is a dictionary containing the IDs
            for a particular dataset.
            
        Returns
        -------
        df     : DataFrame
        
        """
        # If any datasets at all were correctly parsed, then dsInfo
        # will not be empty.
        if dsInfo:
            # Build the DataFrame with indexes prefix and acqID. These are
            # the primary identifiers for a dataset and are always required;
            df = pd.DataFrame(dsInfo).set_index(['prefix', 'acqID'])
            df.sort_index(inplace = True)
            
            return df
        else:
            return None
            
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