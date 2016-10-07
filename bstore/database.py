# © All rights reserved. ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Switzerland, Laboratory of Experimental Biophysics, 2016
# See the LICENSE.txt file for more details.

from pathlib import PurePath, Path, PurePosixPath
from abc import ABCMeta, abstractmethod, abstractproperty
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
from collections import namedtuple, OrderedDict
import traceback

__version__ = config.__bstore_Version__

pp = pprint.PrettyPrinter(indent=4)  

def _checkType(typeString):
    if typeString not in config.__Registered_DatasetTypes__:
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
    
    This decorator allows the Datastore to work with both NumPy arrays and
    TiffFile objects, the latter of which holds the Tiff metadata as well as
    image data.
    
    Parameters
    ----------
    writeImageData        : function       
        Used to write image data into the datastore.
        
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
        atom : Dataset
            The atom (or Dataset) to write into the datastore. If it's a
            TiffFile, the image metadata will be saved as well.
        
        """
        MM_PixelSize = config.__MM_PixelSize__
        
        if isinstance(atom.data, TiffFile):
            # Write the TiffFile metadata to the HDF file; otherwise do nothing
            # First, get the Tiff tags; pages[0] assumes there is only one
            # image in the Tiff file.
            tags = dict(atom.data.pages[0].tags.items())
            
            with h5py.File(self._dsName, mode = 'a') as hdf:
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
class HDFDatastore(Datastore):
    """A HDFDatastore structure for managing SMLM data.
    
    Parameters
    ----------
    dsName : str or Path
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
    The only HDF attribute currently written directly to the image data is::
    
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
        
    dsID = namedtuple('datasetID', ['prefix', 'acqID', 'datasetType',
                                    'attributeOf', 'channelID', 'dateID',
                                    'posID', 'sliceID'])
    """Dataset IDs used by this datastore.
    
    Notes
    -----
    Fields' __doc__ attributes must contain the string "(optional)" if they
    are not required.
        
    """
    dsID.prefix.__doc__      = ('The descriptive name given to '
                                'the dataset by the user.')
    dsID.acqID.__doc__       = 'Acquisition ID number; an integer.'
    dsID.datasetType.__doc__ = 'The type specified by datasetType'
    dsID.attributeOf.__doc__ = 'The type of dataset that this one describes.'
    dsID.channelID.__doc__   = '(optional) String for the channel (color).'
    dsID.dateID.__doc__      = '(optional) The date the dataset was acquired.'
    dsID.posID.__doc__       = '(optional) One or two-tuple of integers.'
    dsID.sliceID.__doc__     = '(optional) Single integer of the axial slice.'
    
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
            
        # Obtain a list of all the files
        files = self._buildFileList(searchDirectory, filenameStrings)
        
        # Keep a running record of what datasets were parsed
        datasets = []   
                
        # files is an OrderedDict. Non-attributes are built before attributes.
        for currType in files.keys():
            # files[currType] returns a list of string
            for currFile in files[currType]:
                try:
                    parser.parseFilename(currFile, datasetType = currType)
                    parser.dataset.data = parser.dataset.readFromFile(currFile,
                                                                      **kwargs)
                    
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
        searchDirectory : str or Path
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
        
        # If Datastore file doesn't exist, return without checking
        try:
            with h5py.File(self._dsName, mode = 'r') as dbFile:
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
        returnDS = self.dsID(prefix, acqID, datasetType, None,
                             channelID, dateID, posID, sliceID)
        return returnDS
        
    def _genDataset(self, dsID):
        """Generate a dataset with an empty data attribute from a datasetID.
        
        Parameters
        ----------
        dsID : datasetID
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
            return acqKey + '/' + ds.datasetType + otherIDs
            
    def get(self, dsID):
        """Returns a Dataset from the datastore.
        
        Parameters
        ----------
        dsID : datasetID
            A namedtuple belonging to the HDFDatastore class.
            
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
        
        # Generate the dataset and retrieve the data
        dataset       = self._genDataset(dsID)
        dataset.data = dataset.get(self._dsName, hdfKey)
            
        return dataset
            
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
        key = self._checkKeyExistence(dataset)
            
        dataset.put(self._dsName, key, **kwargs)
            
        # Don't write IDs for attributes
        if not dataset.attributeOf:            
            self._writeDatasetIDs(dataset)
            
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
        atomicIDs  = [self._genDatasetID(str(key)) for key in resultKeys]
                                           
        # Convert datasetType for the attributes special case
        if tempDS.attributeOf:
            for (index, atom) in enumerate(atomicIDs):
                # Can't set atom attributes directly, so make new ones
                atomicIDs[index]   = self.dsID(atom.prefix, atom.acqID,
                                               tempDS.datasetType,
                                               tempDS.attributeOf,
                                               atom.channelID, atom.dateID,
                                               atom.posID, atom.sliceID)
        
        return atomicIDs
        
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
        ids : datasetID
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
        optional = [field for field in self.dsID._fields
                          if '(optional)' in getattr(self.dsID, field).__doc__]
        for field in optional:
            if field not in idDict:            
                idDict[field] = None
        
        # Create the datasetID        
        ids = self.dsID(prefix      = idDict['prefix'],
                        acqID       = idDict['acqID'],
                        datasetType = ds.datasetType,
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
    """Attempting to write to an existing key in the datastore.
    
    """
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)