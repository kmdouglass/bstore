# © All rights reserved. ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Switzerland, Laboratory of Experimental Biophysics, 2016
# See the LICENSE.txt file for more details.

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
from dateutil.parser import parse
from tifffile import TiffFile
import importlib
from collections import namedtuple

__version__ = config.__bstore_Version__

pp = pprint.PrettyPrinter(indent=4)  

typesOfAtoms = config.__Types_Of_Atoms__

def _checkType(typeString):
    if typeString not in typesOfAtoms:
        raise DatasetError('Invalid datasetType; \'{:s}\' provided.'.format(
                                                                   typeString))

"""Decorators
-------------------------------------------------------------------------------
"""          
def putWidefieldImageWithMicroscopyTiffTags(writeImageData):
    """Decorator for writing OME-XML and Micro-Manager metadata + image data.
    
    This effectively serves as a patch to the original code (versions <= 0.1.1)
    where widefieldImages were represented merely as NumPy arrays. No image
    metadata was included in these versions.
    
    This decorator allows the Database to work with both NumPy arrays and
    TiffFile objects, the latter of which holds the Tiff metadata as well as
    image data. It wraps Database._putWidefieldImage().
    
    Parameters
    ----------
    writeImageData        : function       
        Used to write image data into the database.
        
    Returns
    -------
    writeImageDataAndTags : function
        Bound function for writing image data and Tiff tags.
        
    References
    ----------
    1. https://pypi.python.org/pypi/tifffile
       
    """
    def writeImageDataAndTags(self, atom):
        """Separates image data from Tiff tags and writes them separately.
        
        Parameters
        ----------
        atom : DatabaseAtom
            The atom (or Dataset) to write into the database. If it's a
            TiffFile, the image metadata will be saved as well.
        
        """
        MM_PixelSize = config.__MM_PixelSize__
        
        if isinstance(atom.data, TiffFile):
            # Write the TiffFile metadata to the HDF file; otherwise do nothing
            # First, get the Tiff tags; pages[0] assumes there is only one
            # image in the Tiff file.
            tags = dict(atom.data.pages[0].tags.items())
            
            with h5py.File(self._dbName, mode = 'a') as hdf:
                dt      = h5py.special_dtype(vlen=str)
                
                # Start by writing just the OME-XML
                # Note: omexml data is a byte string; the text is UTF-8 encoded
                # See http://docs.h5py.org/en/latest/strings.html for more info
                if 'image_description' in tags:
                    keyName = self._genKey(atom) + '/OME-XML'
                    omexml  = tags['image_description'].value
                
                    hdf.create_dataset(keyName, (1,), dtype = dt, data=omexml)
                    
                    try:
                        # Write the element_size_um tag if its present in the
                        # OME-XML metadata.
                        ome     = omexml.decode('utf-8', 'strict')
                        stringX = re.search('PhysicalSizeX="(\d*\.?\d*)"',
                                            ome).groups()[0]
                        stringY = re.search('PhysicalSizeY="(\d*\.?\d*)"',
                                            ome).groups()[0]
                        pxSizeX = float(stringX)
                        pxSizeY = float(stringY)
                        
                        # Ensure that the units is microns
                        pxUnitsX = re.search('PhysicalSizeXUnit="(\D\D?)"',
                                             ome).groups()[0].encode()
                        pxUnitsY = re.search('PhysicalSizeYUnit="(\D\D?)"',
                                             ome).groups()[0].encode()
                        assert pxUnitsX == b'\xc2\xb5m', 'OME-XML units not um'
                        assert pxUnitsY == b'\xc2\xb5m', 'OME-XML units not um'

                        self.widefieldPixelSize = (pxSizeX, pxSizeY)
                        
                    except (AttributeError, AssertionError):
                        # When no PhysicalSizeX,Y XML tags are found, or the
                        # the units are not microns, move on to looking inside
                        # the MM metadata.                       
                        pass
                
                # Micro-Manager device states metadata is a JSON string
                if 'micromanager_metadata' in tags:
                    keyName = self._genKey(atom) + '/MM_Metadata'
                    mmmd    = json.dumps(tags['micromanager_metadata'].value)
                    
                    hdf.create_dataset(keyName, (1,), dtype = dt, data = mmmd)
                
                # Micro-Manager summary metadata in JSON string
                if atom.data.is_micromanager:
                    keyName  = self._genKey(atom) + '/MM_Summary_Metadata'
                    metaDict = atom.data.micromanager_metadata
                    mmsmd    = json.dumps(metaDict)
                
                    hdf.create_dataset(keyName, (1,), dtype = dt, data = mmsmd)
                    
                    # Write the element_size_um tag if its present in the
                    # Micro-Manager metadata (this has priority over OME-XML
                    # due to its position here)
                    if MM_PixelSize in metaDict['summary'] \
                                           and self.widefieldPixelSize is None:
                        pxSize = metaDict['summary'][MM_PixelSize]
                        self.widefieldPixelSize = (pxSize, pxSize)
            
            # Convert atom.data to a NumPy array before writing image data
            atom.data = atom.data.asarray()
            
        writeImageData(self, atom)
        
    return writeImageDataAndTags

"""Metaclasses
-------------------------------------------------------------------------------
"""
class Database(metaclass = ABCMeta):
    """Metaclass representing the database structure.
    
    Parameters
    ----------
    dbName : str or Path
        The name of the database file.
    
    """
    def __init__(self, dbName):
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
        
class Dataset(metaclass = ABCMeta):
    """Metaclass for a Dataset. Use this to create new Datasets.
    
    Parameters
    ----------
    data
        The actual data held by the dataset.
    datasetIDs : dict
        The ID fields and their values that identify the datset inside the
        database.
        
        
    Attributes
    ----------
    data
        The actual data held by the dataset.
    datasetIDs : dict
        The ID fields and their values that identify the datset inside the
        database.
    
    """
    def __init__(self, datasetIDs = {}):
        self._data       = None        
        self._datasetIDs = datasetIDs

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
        """Assigns database IDs to this dataset.
        
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
    def datasetTypeName():
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
class HDFDatabase(Database):
    """A HDFDatabase structure for managing SMLM data.
    
    Parameters
    ----------
    dbName : str or Path
        The name of the database file.
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
    The only HDF attribute currently written directly to the image data is::
    
    element_size_um
    
    which is required for opening images directly from the HDF file by the
    HDF5 Plugin for ImageJ and FIJI[1]_.
    
    References
    ----------
    .. [1] http://lmb.informatik.uni-freiburg.de/resources/opensource/imagej_plugins/hdf5.html
        
    """
    def __init__(self, dbName, widefieldPixelSize = None):
        self.widefieldPixelSize = widefieldPixelSize
        super(HDFDatabase, self).__init__(dbName)
        
    def __repr__(self):
        if self.widefieldPixelSize is None:
            pxSizeStr = 'None'
        else:
            x, y = self.widefieldPixelSize[0], self.widefieldPixelSize[1]
            pxSizeStr = '({0:.4f}, {1:.4f})'.format(x,y)
        
        return 'HDFDatabase(\'{0:s}\', widefieldPixelSize = {1:s})'.format(
                                                                  self._dbName,
                                                                  pxSizeStr)
    
    @property
    def attrPrefix(self):
        return config.__HDF_AtomID_Prefix__
        
    dsID = namedtuple('datasetID', ['prefix', 'acqID', 'datasetType',
                                    'attributeOf', 'channelID', 'dateID',
                                    'posID', 'sliceID'])
    """Dataset IDs used by this database.
    
    Notes
    -----
    Fields' __doc__ attributes must contain the string "(optional)" if they
    are not required.
        
    """
    dsID.prefix.__doc__      = ('The descriptive name given to '
                                'the dataset by the user.')
    dsID.acqID.__doc__       = 'Acquisition ID number; an integer.'
    dsID.datasetType.__doc__ = 'The type specified by datasetTypeName'
    dsID.attributeOf.__doc__ = 'The type of dataset that this one describes.'
    dsID.channelID.__doc__   = '(optional) String for the channel (color).'
    dsID.dateID.__doc__      = '(optional) The date the dataset was acquired.'
    dsID.posID.__doc__       = '(optional) One or two-tuple of integers.'
    dsID.sliceID.__doc__     = '(optional) Single integer of the axial slice.'
    
    def build(self, parser, searchDirectory, filenameStrings, dryRun = False):
        """Builds a database by traversing a directory for experimental files.
        
        Parameters
        ----------
        parser               : Parser
            Instance of a parser for converting files to DatabaseAtoms.
        searchDirectory      : str or Path
            This directory and all subdirectories will be traversed.
        filenameStrings      : dict
            Dictionary of key-value pairs, where each key is the name of a
            DataType and each value is a string contained by the end of the
            files corresponding to that DataType.
        dryRun               : bool
            Test the database build without actually creating the database.
            
        Returns
        -------
        buildResults : DataFrame
            A sorted DataFrame for investigating what files were actually
            added to the database.
            
        """ 
        searchDirectory = Path(searchDirectory)
            
        # Check that all generic types are registered
        self._checkForRegisteredTypes(list(filenameStrings.keys()))
            
        # Obtain a list of all the files
        files = self._buildFileList(searchDirectory, filenameStrings)
        
        # Keep a running record of what datasets were parsed
        datasets = []        
        
        # First put types that are not attributes because attributes depend
        # on the presence of their corresponding types in the database.
        for currType in files.keys():
            # files[currType] returns a list of string
            for currFile in files[currType]:
                try:
                    parser.parseFilename(currFile, datasetType = 'generic',
                                         datasetTypeName = currType)
                                         
                    dbAtom = parser.getDatabaseAtom()
                    # Move to the next type if it's an attribute
                    if dbAtom.attributeOf is not None:
                        continue
                    elif not dryRun:
                        self.put(dbAtom)
                    
                    datasets.append(parser.getBasicInfo())
                
                except Exception as err:
                    print(("Unexpected error in build() while "
                           "building generics:"),
                    sys.exc_info()[0])
                    print(err)
                
        # Now place the datasets that are attributes
        for currType in files.keys():
            # files[currType] returns a list of string
            for currFile in files[currType]:
                try:
                    parser.parseFilename(currFile, datasetType = 'generic',
                                         datasetTypeName = currType)
                    
                    dbAtom = parser.getDatabaseAtom()
                    # Move to the next type if it's not an attribute
                    if dbAtom.attributeOf is None:
                        continue                         
                    if not dryRun:
                        self.put(dbAtom)
                    
                    datasets.append(parser.getBasicInfo())
                
                except Exception as err:
                    print(("Unexpected error in build() while "
                           "building generics:"),
                    sys.exc_info()[0])
                    print(err)            

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
        searchDirectory : str or Path
            This directory and all subdirectories will be traversed.
        filenameStrings : dict
            Dictionary of key-value pairs, where each key is the name of a
            DatasetType and each value is a string contained by the end of
            the files corresponding to that data type.
            
        Returns
        -------
        files : dict of list of str
            Dictionary whose keys are the DatasetType names and whose values
            are lists of strings containing the path to files that satisfy the
            globbed search.
        
        """
        if not filenameStrings:
            return {}
            
        FilesGen = {}
        files    = {}
        for filename, fileID in filenameStrings.items():
            # Do not process any generic type unless its currently registered
            # with B-Store
            if filename not in config.__Registered_DatasetTypes__:
                continue
            else:
                FilesGen[filename] = searchDirectory.glob('**/*{:s}'.format(
                                                                       fileID))
        # Build the dictionary of files with keys describing
        # their generic dataset type                                                               
        for filename in FilesGen.keys():
            files[filename] = sorted(FilesGen[filename])
            
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
    
    def _checkKeyExistence(self, ds):
        """Checks for the existence of a key.
        
        Parameters
        ----------
        ds : Dataset
        
        Returns
        -------
        key : str
            The HDF key pointing to the dataset.
        
        """
        key = self._genKey(ds)        
        
        # If Database file doesn't exist, return without checking
        try:
            with h5py.File(self._dbName, mode = 'r') as dbFile:
                # First check atoms that are not attributes
                if key in dbFile and ds.attributeOf is None:
                    raise HDF5KeyExists(('Error: '
                                         '{0:s} already exists.'.format(key)))
                
                # Next search for *any* occurence of the attribute flag
                # in the attribute names of dataset that key points to.
                elif key in dbFile and ds.attributeOf is not None:
                    attrID = config.__HDF_Metadata_Prefix__                 
                    mdKeys = dbFile[key].attrs.keys()
                    for currKey in mdKeys:
                        if attrID in currKey:
                            raise HDF5KeyExists(('Error: Attributes for'
                                                 '{0:s} already '
                                                 'exist.'.format(key)))                    
        except IOError:
            pass
        
        return key
           
    def _genAtomicID(self, key):
        """Generates an atomic ID from a HDF key. The inverse of _genKey.
        
        Note that the data property is set to 'None.' Only the IDs are
        retrieved.
        
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
        
        # Build the return dataset
        mod   = importlib.import_module('bstore.datasetTypes.{0:s}'.format(
                                                                  datasetType))
        dType = getattr(mod, datasetType)
            
        returnDS = dType(prefix, acqID, datasetType, data,
                         channelID = channelID, dateID = dateID,
                         posID = posID, sliceID = sliceID)
                               
        return returnDS

    def _genKey(self, ds):
        """Generate a key name for a dataset. The inverse of _genAtomicID.
        
        Parameters
        ----------
        ds : Dataset or datasetID
        
        Returns
        -------
        str
        
        """
        # Account for whether a Dataset or a datasetIDs namedtuple was given.
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
            otherIDs += '_' + ids.channelID
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
            return acqKey + '/' + ds.attributeOf + otherIDs
        else:
            return acqKey + '/' + ds.datasetTypeName + otherIDs
            
    def get(self, dsID):
        """Returns a Dataset from the database.
        
        Parameters
        ----------
        dsID : datasetID
            A namedtuple belonging to the HDFDatabase class.
            
        Returns
        -------
        dataset : Dataset
            A complete dataset.
        
        """
        assert dsID.datasetType in config.__Registered_DatasetTypes__
        hdfKey = self._genKey(dsID)

        # Ensure that the key exists        
        try:
            self._checkKeyExistence(dsID)
        except HDF5KeyExists:
            pass
        
        # TODO: Pick up here and create the dataset from the ID
        if not dsID.attributeOf:
            data = dataset.get(self._dbName, hdfKey)
        elif dataset.attributeOf:
            # Recreate the hdf key to point towards the attributeOf dataset
            mod = importlib.import_module('bstore.datasetTypes.{0:s}'.format(
                                                             dataset.attributeOf))
            dsType = getattr(mod, dataset.attributeOf)
            tempID = dsType(ids['prefix'], ids['acqID'], 'generic', None,
                                channelID = ids['channelID'],
                                dateID = ids['dateID'], posID = ids['posID'],
                                sliceID = ids['sliceID'])
            
            hdfKey    = self._genKey(tempID)
            dataset.data = dataset.get(self._dbName, hdfKey)
            
        return dataset
            
    def put(self, dataset, **kwargs):
        """Writes data from a single dataset into the database.
        
        Parameters
        ----------
        dataset : Dataset
        
        """
        assert dataset.datasetTypeName in config.__Registered_DatasetTypes__,\
            'Type {0} is unregistered.'.format(dataset.datasetTypeName)
        if dataset.attributeOf:
            assert dataset.attributeOf in config.__Registered_DatasetTypes__,\
                'Type {0} is unregistered.'.format(dataset.attributeOf)
        
        # Key generation automatically handles datasets that are attributes
        key = self._checkKeyExistence(dataset)
            
        dataset.put(self._dbName, key, **kwargs)
            
        # Don't write IDs for attributes
        if not dataset.attributeOf:            
            self._writeDatasetIDs(dataset)
            
    def query(self, datasetType = 'locResults', datasetTypeName = None):
        """Returns a set of database atoms inside this database.

        Parameters
        ----------
        datasetType     : str
            The type of data to search for.
        datasetTypeName : str
            The dataset type to search for. This only matters when
            datasetType is 'generic'.
        
        Returns
        -------
        atomicIDs   : list of Dataset
            All of the atomic ids matching the datasetType
        
        """
        _checkType(datasetType)       
        searchString = datasetType
        ap           = config.__HDF_AtomID_Prefix__
        mp           = config.__HDF_Metadata_Prefix__
        
        if datasetTypeName is not None:
            # Used to determine whether the datasetTypeName is an attribute
            assert datasetTypeName in config.__Registered_DatasetTypes__, (''
            'Error: {:s} not in __Registered_DatasetTypes__.'.format(
                                                              datasetTypeName))
            mod = importlib.import_module('bstore.datasetTypes.{0:s}'.format(
                                                              datasetTypeName))
            inputType = getattr(mod, datasetTypeName)
            tempDS = inputType('temp', 1, 'generic', None)                
        
        # Open the hdf file
        with h5py.File(self._dbName, 'r') as f:
            # Extract all localization datasets from the HDF5 file by matching
            # each group to the search string.
            # ('table' not in name) excludes the subgroup inside every
            # processed_localization parent group.
            resultGroups = []
            def find_datasets(name):
                """Finds datasets matching the name pattern."""
                # Finds only datasets with the SMLM_datasetType attribute.
                if (ap + 'datasetType' in f[name].attrs) \
                    and (f[name].attrs[ap + 'datasetType'] == searchString) \
                    and searchString != 'generic':
                        resultGroups.append(name)
                               
                # If 'generic' is the datasetType, check that the specific
                # datasetTypeName matches
                if (searchString == 'generic') \
                    and (ap + 'datasetTypeName' in f[name].attrs) \
                    and (f[name].attrs[ap + 'datasetTypeName'] \
                         == datasetTypeName):
                        resultGroups.append(name)
                        
                # Read generics that are attributes here.
                if (searchString == 'generic') \
                    and (ap + 'datasetTypeName' in f[name].attrs) \
                    and (tempDS.attributeOf is not None) \
                    and (f[name].attrs[ap + 'datasetTypeName'] \
                        == tempDS.attributeOf) \
                    and (mp + ap + 'datasetType') in f[name].attrs:
                        resultGroups.append(name)
                
            f.visit(find_datasets)
        
        # Read attributes of each key in resultGroups for SMLM_*
        # and convert them to a dataset ID.
        # Note: If you use Path and Not PurePosixPath, '/' will
        # become '\\' on Windows and you won't get the right keys.
        resultKeys = list(map(PurePosixPath, resultGroups))
        atomicIDs  = [self._genAtomicID(str(key)) for key in resultKeys]
                                           
        # Convert datasetType for attributes special case
        if searchString == 'generic' and tempDS.attributeOf:
            for (index, atom) in enumerate(atomicIDs):
                # Can't set atom attributes directly, so make new ones
                ids = atom.getDatasetIDs()
                ids['datasetType']     = 'generic'
                ids['datasetTypeName'] = tempDS.datasetTypeName
                atomicIDs[index] = inputType(ids['prefix'], ids['acqID'],
                                             'generic', None,
                                             ids['channelID'], ids['dateID'],
                                             ids['posID'], ids['sliceID'])
        
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
            
    def _unpackDatasetIDs(self, ds):
        """Unpack the dataset IDs into a format usable by this database.
        
        Parameters
        ----------
        ds  : Dataset
        
        Returns
        -------
        ids : datasetID
            The ids for the dataset; a namedtuple of the HDFDatabase class.
        
        """
        idDict = ds.datasetIDs.copy()
        print(idDict)
        
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
        if 'dateID' in idDict and not pattern.match(idDict['dateID']):
            raise ValueError(('Error: The date is not of the format '
                              'YYYY-MM-DD.'))               
        
        # Fill in missing optional id fields
        optional = [field for field in self.dsID._fields
                          if '(optional)' in getattr(self.dsID, field).__doc__]
        for field in optional:
            if field not in idDict:            
                idDict[field] = None
        
        # Create the datasetID        
        ids = self.dsID(prefix      = idDict['prefix'],
                        acqID       = idDict['acqID'],
                        datasetType = ds.datasetTypeName,
                        attributeOf = ds.attributeOf,
                        channelID   = idDict['channelID'],
                        dateID      = idDict['dateID'],
                        posID       = idDict['posID'],
                        sliceID     = idDict['sliceID'])
                        
        return ids
    
    def _writeDatasetIDs(self, ds):
        """Writes B-Store dataset IDs as attributes of the dataset.
        
        Parameters
        ----------
        ds : Dataset
        
        """
        key        = self._genKey(ds)
        attrPrefix = self.attrPrefix
        ids        = self._unpackDatasetIDs(ds)
        with  h5py.File(self._dbName, mode = 'a') as hdf:
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
            hdf[key].attrs[attrPrefix + 'datasetType'] = ds.datasetTypeName
            
            # Current version of this software
            hdf[key].attrs[attrPrefix +'Version'] = \
                                               config.__bstore_Version__

"""Exceptions
-------------------------------------------------------------------------------
"""
class DatasetError(Exception):
    """Error raised when a bad datasetType is passed.
    
    """
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)
        
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