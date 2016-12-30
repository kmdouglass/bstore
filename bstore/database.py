# © All rights reserved. ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Switzerland, Laboratory of Experimental Biophysics, 2016
# See the LICENSE.txt file for more details.

from pathlib import PurePath, Path, PurePosixPath
from abc import ABCMeta, abstractmethod, abstractproperty
import numpy as np
import h5py
import bstore.config as config
import sys
import pprint
import re
import pandas as pd
from dateutil.parser import parse
import importlib
from collections import namedtuple, OrderedDict
import traceback
import pickle
import filelock

__version__ = config.__bstore_Version__

pp = pprint.PrettyPrinter(indent=4)  

"""Decorators
-------------------------------------------------------------------------------
"""
def hdfLockCheck(writeFunc):
    """Checks whether a HDF file is locked for writing; raises an error if not.
    
    Place this decorator before functions like build() and put() that require
    a file to be locked before writing data to the file. This prevents multiple
    HDFDatastore instances from writing to the same file at the same time.
    
    Parameters
    ----------
    writeFunc    : function
        The function call of the Datastore to be called.
    
    Returns
    -------
    lockCheck     : function

    """
    def lockCheck(self, *args, **kwargs):
        """
        Parameters
        ----------
        self : HDFDatastore instance
        
        """
        if not self._lock.is_locked:
            raise FileNotLocked('Error: File is not locked for writing. Use '
                                'this Datastore inside a with...as block.')
        
        writeFunc(self, *args, **kwargs)
        
    return lockCheck

"""Metaclasses
-------------------------------------------------------------------------------
"""
class Datastore(metaclass = ABCMeta):
    """Metaclass representing the datastore structure.
    
    Parameters
    ----------
    dsName : str or Path
        The name of the datastore file.
    
    """
    def __init__(self, dsName):
        # Convert Path objects to strings
        if isinstance(dsName, PurePath):
            dsName = str(dsName)
            
        self._dsName = dsName
    
    @abstractmethod
    def build(self):
        """Create new datastore from a list of datasets.
        
        """
        pass
    
    @abstractmethod
    def get(self):
        """Retrieve dataset from the datastore.
        
        """
        pass    
    
    @abstractmethod
    def put(self):
        """Place a dataset into the datastore.
        
        """
        pass
    
    @abstractmethod
    def query(self):
        """Return a list of datasets in the datastore.
        
        """
        pass
        
class Dataset(metaclass = ABCMeta):
    """Metaclass for a Dataset. Use this to create new Datasets.
    
    Parameters
    ----------
    data
        The actual data held by the dataset.
    datasetIDs : dict
        The ID fields and their values that identify the datset inside the
        datastore.
        
        
    Attributes
    ----------
    data
        The actual data held by the dataset.
    datasetIDs : dict
        The ID fields and their values that identify the datset inside the
        datastore.
    
    """
    def __init__(self, datasetIDs = {}):
        self._data       = None        
        self._datasetIDs = datasetIDs
        
    @abstractmethod
    def __repr__(self):
        pass

    @abstractproperty
    def attributeOf():    
        pass
    
    @property
    def data(self):
        return self._data
        
    @data.setter
    def data(self, value):
        self._data = value
    
    @property
    def datasetIDs(self):
        return self._datasetIDs
        
    @datasetIDs.setter
    def datasetIDs(self, ids):
        """Assigns datastore IDs to this dataset.
        
        Parameters
        ----------
        ids : dict
            Key-value pairs that specify the IDs and their values. Keys must
            be strings.
            
        """
        if isinstance(ids, dict):
            self._datasetIDs = ids
        else:
            raise TypeError('datasetIDs must be a dict.')
    
    @abstractproperty
    def datasetType():
        pass
    
    @abstractmethod
    def get():
        pass
    
    @abstractmethod
    def put():
        pass

    @abstractmethod
    def readFromFile():
        pass

"""Concrete classes
-------------------------------------------------------------------------------
"""
DatasetID = namedtuple('DatasetID', ('prefix acqID datasetType attributeOf '
                                     'channelID dateID posID sliceID'))
"""Dataset IDs used by the HDFDatastore

prefix      = The descriptive name given to the dataset by the user.
acqID       = Acquisition ID number; an integer.
datasetType = The type specified by datasetType.
attributeOf = The type of dataset that this one describes.
channelID   = (optional) String for the channel (color).
dateID      = (optional) The date the dataset was acquired.
posID       = (optional) One or two-tuple of integers.
sliceID     = (optional) Single integer of the axial slice.

"""
_optionalIDs = ('channelID', 'dateID', 'posID', 'sliceID')

class HDFDatastore(Datastore):
    """A HDFDatastore structure for managing SMLM data.
    
    Parameters
    ----------
    dsName               : str or Path
        The name of the datastore file.
    widefieldPixelSize   : 2-tuple of float or None
        The x- and y-size of a widefield pixel in microns. This
        information is used to write attributes to the widefield image for
        opening with other software libraries, such as the HDF5 Plugin for
        ImageJ and FIJI. Setting it will override all metadata information.
    
    Attributes
    ----------
    widefieldPixelSize   : 2-tuple of float or None
        The x- and y-size of a widefield pixel in microns. This
        informationis used to write attributes to the widefield image for
        opening with other software libraries.
    
    Notes
    -----
    The only HDF attribute currently written directly to the image data, i.e.
    to the HDF dataset (not group) is::
    
    element_size_um
    
    which is required for opening images directly from the HDF file by the
    HDF5 Plugin for ImageJ and FIJI[1]_.
    
    References
    ----------
    .. [1] http://lmb.informatik.uni-freiburg.de/resources/opensource/imagej_plugins/hdf5.html
        
    """
    def __init__(self, dsName, widefieldPixelSize = None):
        self.widefieldPixelSize = widefieldPixelSize
        super(HDFDatastore, self).__init__(dsName)
        
        self._datasets = []
        
        # Used to store a persistent copy of an HDFDatastore instance
        # in the HDF file
        self._persistenceKey = config.__Persistence_Key__
        
        # Lock file to prevent concurrent writes
        self._lock = filelock.FileLock(str(dsName) + '.lock')
        
    def __enter__(self):
        """For context managers; updates self._datasets then locks HDF file.
        
        """
        self._loads()
        self._lock.acquire(timeout = 0) # timeout = 0 -> try acquire only once
        return self
    
    def __exit__(self, *args):
        """Releases the lock on the file.
        
        """
        self._lock.release()
        
    def __getitem__(self, key):
        return self._datasets[key]
        
    def __getstate__(self):
        """Returns the properties of the HDFDatastore to pickle.
        
        This returns the attributes of the HDFDatastore that should be saved
        in the persistent state inside the HDF file. Without this function,
        pickle would try to pickle the FileLock object, which would raise an
        exception.
        
        For this reason, '_lock' is not returned as part of the class's state.
        '_dsName' is not returned because it's a property of the file, not the
        class.
        
        """
        return {k:v for k, v in self.__dict__.items()
                if (k != '_lock') and (k != '_dsName')}
        
    def __iter__(self):
        return (x for x in self._datasets)
        
    def __len__(self):
        return len(self._datasets)
        
    def __repr__(self):
        if self.widefieldPixelSize is None:
            pxSizeStr = 'None'
        else:
            x, y = self.widefieldPixelSize[0], self.widefieldPixelSize[1]
            pxSizeStr = '({0:.4f}, {1:.4f})'.format(x,y)
        
        return 'HDFDatastore(\'{0:s}\', widefieldPixelSize = {1:s})'.format(
                   self._dsName,
                   pxSizeStr)
                   
    @property
    def attrPrefix(self):
        return config.__HDF_AtomID_Prefix__
    
    @hdfLockCheck
    def build(self, parser, searchDirectory, filenameStrings, dryRun = False,
              **kwargs):
        """Builds a datastore by traversing a directory for experimental files.
        
        Parameters
        ----------
        parser               : Parser
            Instance of a parser for converting files to Datasets.
        searchDirectory      : str or Path
            This directory and all subdirectories will be traversed.
        filenameStrings      : dict
            Dictionary of key-value pairs, where each key is the name of a
            DataType and each value is a string contained by the end of the
            files corresponding to that DataType.
        dryRun               : bool
            Test the datastore build without actually creating the datastore.
        **kwargs
            Keyword arguments to pass to the parser's readFromFile() method.
            
        Returns
        -------
        buildResults : DataFrame
            A sorted DataFrame for investigating what files were actually
            added to the datastore.
            
        """ 
        searchDirectory = Path(searchDirectory)
            
        self._checkForRegisteredTypes(list(filenameStrings.keys()))
            
        # Obtain a list of all the files, with non-attribute files first.
        # Sorting them like this prevents errors that would occur when writing
        # attributes to non-existent keys in the HDF file.
        files = self._buildFileList(searchDirectory, filenameStrings)
        
        # Keep a running record of what datasets were succesffully parsed
        datasets = []   
                
        # files is an OrderedDict. Non-attributes are built before attributes.
        for currType in files.keys():
            # files[currType] returns a list of string
            for currFile in files[currType]:
                try:
                    parser.parseFilename(
                        currFile, datasetType = currType, **kwargs)
                    
                    if not dryRun:
                        self.put(parser.dataset)
                    
                    datasets.append(self._unpackDatasetIDs(parser.dataset))
                except Exception as err:
                    print(("Unexpected error in build():"),
                    sys.exc_info()[0])
                    print(err)
                    
                    if config.__Verbose__:
                        print(traceback.format_exc())

        # Report on all the datasets that were parsed
        buildResults = self._sortDatasets(datasets)

        if buildResults is not None:
            print('{0:d} files were successfully parsed.'.format(
                                                        len(buildResults)))
        else:
            print('0 files were successfully parsed.')
                
        return buildResults
        
    def _buildFileList(self, searchDirectory, filenameStrings):
        """Builds a list of the files in a supplied folder for build().
        
        Parameters
        ----------
        searchDirectory : Path
            This directory and all subdirectories will be traversed.
        filenameStrings : dict
            Dictionary of key-value pairs, where each key is the name of a
            DatasetType and each value is a string contained by the end of
            the files corresponding to that data type.
            
        Returns
        -------
        files : OrderedDict of list of str
            Dictionary whose keys are the DatasetType names and whose values
            are lists of strings containing the path to files that satisfy the
            globbed search.
        
        """
        if not filenameStrings:
            return {}
            
        if not searchDirectory.exists():
            raise SearchDirectoryDoesNotExist(
                '%s does not exist.' % str(searchDirectory))
            
        files = {}
        for filename, fileID in filenameStrings.items():
            # Do not process any type unless its currently registered
            # with B-Store
            if filename not in config.__Registered_DatasetTypes__:
                continue
            else:
                files[filename] = sorted(searchDirectory.glob(
                                                    '**/*{:s}'.format(fileID)))
                                                    
        def sortKey(x):
            # Create instances of datasetType to place attribute types
            # after non-attributes
            dsTypeString = x[0]
            mod = importlib.import_module('bstore.datasetTypes.{0:s}'.format(
                      dsTypeString))
            ds  = getattr(mod, dsTypeString)() # Note () for instantiation
            if ds.attributeOf:
                return 1
            else:
                return 0
              
        files = OrderedDict(sorted(files.items(), key=sortKey))
        return files
    
    def _checkForRegisteredTypes(self, typeList):
        """Verifies that each type in typeList is registered.
        
        Parameters
        ----------
        typeList : list of str
        
        """
        for typeName in typeList:
            if typeName not in config.__Registered_DatasetTypes__:
                raise DatasetTypeError(typeName)
    
    def _checkKeyExistence(self, ds, raiseException = True):
        """Checks for the existence of a key.
        
        This is required for checking whether attributes are attached to a
        dataset. For example, a key to a dataset might exist, but it may not
        have B-Store attributes. In this case, a key *would not* exist for the
        Dataset's attributes.
        
        Parameters
        ----------
        ds             : Dataset
        raiseException : bool
            Should the function raise an exception or only return a bool
            that is True if the key exists?
        
        Returns
        -------
        keyExists : bool
        key       : str
            The HDF key pointing to the dataset.
        ids       : dsID
            The namedtuple of IDs extracted from the dataset.
        
        """
        key, ids  = self._genKey(ds)
        keyExists = False        
        
        # If Datastore file doesn't exist, return without checking
        try:
            with h5py.File(self._dsName, mode = 'r') as dbFile:
                # First check atoms that are not attributes
                if key in dbFile and ds.attributeOf is None:
                    raise HDF5KeyExists(
                        'Error: {0:s} already exists.'.format(key))
                
                # Next search for *any* occurence of the attribute flag
                # in the attribute names of dataset that key points to.
                elif key in dbFile and ds.attributeOf is not None:
                    attrID = config.__HDF_Metadata_Prefix__                 
                    mdKeys = dbFile[key].attrs.keys()
                    for currKey in mdKeys:
                        if attrID in currKey:
                            raise HDF5KeyExists(
                                'Error: {0:s} already exists.'.format(key))
                            
        except IOError:
            # File doesn't exist
            keyExists = False
        except HDF5KeyExists:
            keyExists = True
            if raiseException:
                raise HDF5KeyExists(
                    ('Error: Attributes for {0:s} already exist.'.format(key)))
                    
        return keyExists, key, ids
        
    def _dumps(self):
        """Writes the state of the HDFDatastore object to the HDF file.
        
        """
        with h5py.File(self._dsName, mode = 'a') as file:
            try:
                # Remove the old dataset containing the persistence information
                del(file[self._persistenceKey])
            except KeyError:
                pass # key doesn't exist yet
                
            # Pickle this instance and write the byte string to the HDF file
            # See https://docs.python.org/3/library/pickle.html#data-stream-format
            # for an explanation of the pickle format levels.
            # np.void is necessary for writing byte strings, see
            # http://docs.h5py.org/en/latest/strings.html#how-to-store-raw-binary-data
            picklestring = pickle.dumps(self, protocol = 3)
            file[self._persistenceKey] = np.void(picklestring)
        
    def _genDataset(self, dsID):
        """Generate a Dataset with an empty data attribute from a DatasetID.
        
        Parameters
        ----------
        dsID : DatasetID
            Namedtuple representing a dataset in the datastore.
            
        Returns
        -------
        : Dataset
            
        """
        idDict      = dict(dsID._asdict())
        datasetType = idDict['datasetType']
        
        # The following do not belong in the dict of ID's, so remove them.
        # They are attributes of the datasetType.
        del(idDict['datasetType']); del(idDict['attributeOf'])
        
        # Build the return dataset
        mod   = importlib.import_module('bstore.datasetTypes.{0:s}'.format(
                    datasetType))
        dType = getattr(mod, datasetType)
            
        return dType(datasetIDs = idDict)
           
    def _genDatasetID(self, key):
        """Generates an dataset ID (dsID) from a HDF key. Inverse of _genKey.
        
        Note that this will not return IDs for dataset types that are
        attributes because their HDF key is ambiguous.
        
        Parameters
        ----------
        key : str
            A key pointing to a dataset in the HDF file.
            
        Returns
        -------
        returnDS : dsID
            The ID's of one dataset. 
            
        """
        # Parse key for atomic IDs
        splitStr    = key.split(sep = '/')
        prefix      = splitStr[0]
        
        # Check for a date in the second part of splitStr
        try:
            # [1:] cuts off the 'd' part of the string, which
            # is needed for PyTables naming conventions. So are underscores.
            datetimeObject = parse(splitStr[1][1:].replace('_','-'))
            dateID = datetimeObject.strftime('%Y-%m-%d')
            
            # Remove this element so the remaining code
            # with fixed indexes will not need to be changed.            
            splitStr.pop(1)
            
        except ValueError:
            # No date detected; don't do anything
            dateID = None
        
        acqID       = int(splitStr[1].split(sep = '_')[-1])
        
        otherIDs    = splitStr[2]
        datasetType = otherIDs.split('_')[0]
        
        channelRaw = re.search(r'Channel(.*)', otherIDs)
        if channelRaw == None:
            channelID = None
        else:
            # 'Channel...' will always be the first item in the split, ergo [0]
            channelID = channelRaw.group(0).split('_')[0]
            channelID = channelID[len('Channel'):]
        
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
        
        # Build the return dataset
        returnDS = DatasetID(prefix, acqID, datasetType, None,
                             channelID, dateID, posID, sliceID)
        return returnDS

    def _genKey(self, ds):
        """Generate a key name for a dataset. The inverse of _genAtomicID.
        
        Parameters
        ----------
        ds : Dataset or DatasetID
        
        Returns
        -------
        key : str
        ids : dsID
            The namedtuple of IDs extracted from the dataset.
        
        """
        # Account for whether a Dataset or a DatasetID namedtuple was given.
        if isinstance(ds, Dataset):
            ids = self._unpackDatasetIDs(ds)
        else:
            ids = ds
        
        # 'd' and underscores are needed for PyTables naming conventions
        if ids.dateID is not None:
            acqKey = '/'.join([ids.prefix,
                               'd' + ids.dateID.replace('-','_'),
                               ids.prefix]) + \
                     '_' + str(ids.acqID)
        else:
            acqKey = '/'.join([ids.prefix, ids.prefix]) + \
                     '_' + str(ids.acqID)
                                 
        otherIDs = ''
        if ids.channelID is not None:
            otherIDs += '_Channel' + ids.channelID
        if ids.posID is not None:
            if len(ids.posID) == 1:
                posID = ids.posID[0]    
                otherIDs += '_Pos{:d}'.format(posID)
            else:
                otherIDs += '_Pos_{0:0>3d}_{1:0>3d}'.format(ids.posID[0], 
                                                            ids.posID[1])
        if ids.sliceID is not None:
            otherIDs += '_Slice{:d}'.format(ids.sliceID)
        
        # If an attribute, use the name of the DatasetType that this type is
        # an attribute of.
        if ids.attributeOf:
            key = acqKey + '/' + ds.attributeOf + otherIDs
        else:
            key = acqKey + '/' + ds.datasetType + otherIDs
            
        return key, ids
            
    def get(self, dsID):
        """Returns a Dataset from the datastore.
        
        Parameters
        ----------
        dsID : DatasetID
            A namedtuple belonging to the HDFDatastore class.
            
        Returns
        -------
        dataset : Dataset
            A complete dataset.
        
        """
        self._checkForRegisteredTypes(config.__Registered_DatasetTypes__)
        #assert dsID.datasetType in config.__Registered_DatasetTypes__

        # Ensure that the key exists        
        keyExists, hdfKey, _ = self._checkKeyExistence(
            dsID, raiseException = False)
            
        if not keyExists:
            raise HDF5KeyDoesNotExist(
                'Dataset does not exist: ' + dsID.__repr__())
        
        # Generate the dataset and retrieve the data
        dataset       = self._genDataset(dsID)
        dataset.data = dataset.get(self._dsName, hdfKey)
            
        return dataset
        
    def _loads(self):
        """Loads and updates the dataset ID information from the HDF file.
        
        """
        try:
            with h5py.File(str(self._dsName), mode = 'r') as file:
                serialObject   = file[self._persistenceKey]
                objFromHDF     = pickle.loads(serialObject.value)
                self.__dict__.update(objFromHDF.__dict__)
        except OSError:
            # File doesn't exist, so don't try to update
            pass
    
    @hdfLockCheck        
    def put(self, dataset, **kwargs):
        """Writes data from a single dataset into the datastore.
        
        Parameters
        ----------
        dataset : Dataset
        
        """
        assert dataset.datasetType in config.__Registered_DatasetTypes__,\
            'Type {0} is unregistered.'.format(dataset.datasetType)
        if dataset.attributeOf:
            assert dataset.attributeOf in config.__Registered_DatasetTypes__,\
                'Type {0} is unregistered.'.format(dataset.attributeOf)
        
        # Key generation automatically handles datasets that are attributes
        _, key, ids = self._checkKeyExistence(dataset)
            
        dataset.put(self._dsName, key, **kwargs)
        self._datasets.append(ids)
            
        # Don't write IDs for attributes
        if not dataset.attributeOf:            
            self._writeDatasetIDs(dataset, key = key, ids = ids)
            
        # Dump the serialized bytestring of the class to the HDF file
        self._dumps()
            
    def query(self, datasetType = 'Localizations'):
        """Returns a list of datasets inside this datastore.

        Parameters
        ----------
        datasetType     : str
            The type of data to search for..
        
        Returns
        -------
        dsIDs   : list of Dataset
            All of the dataset ids matching the datasetType
        
        """
        self._checkForRegisteredTypes([datasetType])       
        searchString = datasetType
        ap           = config.__HDF_AtomID_Prefix__
        mp           = config.__HDF_Metadata_Prefix__
        mod    = importlib.import_module('bstore.datasetTypes.{0:s}'.format(
                                                                  datasetType))
        tempDS = getattr(mod, datasetType)()

        # Open the hdf file
        with h5py.File(self._dsName, 'r') as f:
            # Extract all localization datasets from the HDF5 file by matching
            # each group to the search string.
            # ('table' not in name) excludes the subgroup inside every
            # processed_localization parent group.
            resultGroups = []
            def find_datasets(name):
                """Finds datasets matching the name pattern."""
                # Finds only datasets with the SMLM_datasetType attribute.
                if (ap + 'datasetType' in f[name].attrs) \
                    and (f[name].attrs[ap + 'datasetType'] == searchString):
                        resultGroups.append(name)
                        
                # Read datasets that are attributes here.
                if (ap + 'datasetType' in f[name].attrs) \
                    and (tempDS.attributeOf is not None) \
                    and (f[name].attrs[ap + 'datasetType'] \
                        == tempDS.attributeOf) \
                    and (mp + ap + 'datasetType') in f[name].attrs:
                        resultGroups.append(name)
                
            f.visit(find_datasets)
        
        # Read attributes of each key in resultGroups for SMLM_*
        # and convert them to a dataset ID.
        # Note: If you use Path and Not PurePosixPath, '/' will
        # become '\\' on Windows and you won't get the right keys.
        resultKeys = list(map(PurePosixPath, resultGroups))
        dsIDs      = [self._genDatasetID(str(key)) for key in resultKeys]
                                           
        # Convert datasetType for the attributes special case
        if tempDS.attributeOf:
            for (index, atom) in enumerate(dsIDs):
                # Can't set atom attributes directly, so make new ones
                dsIDs[index] = DatasetID(atom.prefix, atom.acqID,
                    tempDS.datasetType, tempDS.attributeOf, atom.channelID,
                    atom.dateID, atom.posID, atom.sliceID)
        
        return dsIDs
        
    def _sortDatasets(self, dsInfo):
        """Sorts and organizes all datasets before a Datastore build.
        
        _sortDatasets() accepts a list of dicts containing dataset
        information. It then sorts and organizes the information in a
        human-readable format, allowing both humans and computers to
        locate possible errors before and after the datastore is built.
        
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
            
    def _unpackDatasetIDs(self, ds):
        """Unpack the dataset IDs into a format usable by this datastore.
        
        Parameters
        ----------
        ds  : Dataset
        
        Returns
        -------
        ids : DatasetID
            The ids for the dataset; a namedtuple of the HDFDatastore class.
        
        """
        idDict = ds.datasetIDs.copy()
        
        # Preconditioning of the IDs
        # Require prefix and acqID to be specified
        if ('prefix' not in idDict) | ('acqID' not in idDict):
            raise DatasetIDError('DatasetID missing a \'key\' '
                                 'or \'acqID\' key')
        
        assert idDict['prefix'] and idDict['acqID'],('Error: \'prefix\' and '
                                                     '\'acqID\' cannot be '
                                                     'None.')
                                 
        # dateID should follow the format YYYY-MM-DD
        # Note that Python's 'and' short circuits, so the order here
        # is important. pattern.match(None) will raise a TypeError
        pattern = re.compile('\d{4}-\d{2}-\d{2}')
        if ('dateID' in idDict) and (idDict['dateID'] is not None) \
                           and not pattern.match(idDict['dateID']):
            raise ValueError(('Error: The date is not of the format '
                              'YYYY-MM-DD.'))               
        
        # Fill in missing optional id fields
        optional = [field for field in DatasetID._fields
                          if field in _optionalIDs]
        for field in optional:
            if field not in idDict:            
                idDict[field] = None
        
        # Create the DatasetID        
        ids = DatasetID(prefix      = idDict['prefix'],
                        acqID       = idDict['acqID'],
                        datasetType = ds.datasetType,
                        attributeOf = ds.attributeOf,
                        channelID   = idDict['channelID'],
                        dateID      = idDict['dateID'],
                        posID       = idDict['posID'],
                        sliceID     = idDict['sliceID'])
                        
        return ids
    
    def _writeDatasetIDs(self, ds, key = None, ids = None):
        """Writes B-Store dataset IDs as HDF attributes of the dataset.
        
        Parameters
        ----------
        ds  : Dataset
        key : str
        ids : dsID
        
        """
        if not key or not ids:
            key        = self._genKey(ds)
            ids        = self._unpackDatasetIDs(ds)
        
        attrPrefix = self.attrPrefix
        with  h5py.File(self._dsName, mode = 'a') as hdf:
            hdf[key].attrs[attrPrefix + 'acqID']       = ids.acqID
            hdf[key].attrs[attrPrefix + 'channelID']   = \
                'None' if ids.channelID is None else ids.channelID
            hdf[key].attrs[attrPrefix + 'dateID']      = \
                'None' if ids.dateID is None else ids.dateID
            hdf[key].attrs[attrPrefix + 'posID']       = \
                'None' if ids.posID is None else ids.posID
            hdf[key].attrs[attrPrefix + 'prefix']      = ids.prefix
            hdf[key].attrs[attrPrefix + 'sliceID']     = \
                'None' if ids.sliceID is None else ids.sliceID
            hdf[key].attrs[attrPrefix + 'datasetType'] = ds.datasetType
            
            # Current version of this software
            hdf[key].attrs[attrPrefix +'Version'] = \
                                               config.__bstore_Version__

"""Exceptions
-------------------------------------------------------------------------------
"""
class DatasetIDError(Exception):
    """Error raised when a bad or missing dataset IDs are supplied.
    
    """
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)
        
class DatasetTypeError(Exception):
    """Error raised when a bad or unregistered DatasetType is used.
    
    """
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)
          
class FileNotLocked(Exception):
    """Raised when trying to write to an unlocked file.
    
    """
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)
        
class LocResultsDoNotExist(Exception):
    """Attempting to attach locMetadata to non-existing locResults.
    
    """
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)
        
class HDF5KeyDoesNotExist(Exception):
    """Attempting to get a dataset that doesn't exist.
    
    """
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)
        
class HDF5KeyExists(Exception):
    """Attempting to write to an existing key in the datastore.
    
    """
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)
        
class SearchDirectoryDoesNotExist(Exception):
    """The search directory for a datastore build does not exist.
    
    """
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)