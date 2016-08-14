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

# Import the registered generic types
#for genericType in config.__Registered_Generics__:


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

class DatabaseAtom(metaclass = ABCMeta):
    """Metaclass representing one organizational unit in the database.
    
    Parameters
    ----------
    prefix      : str
        The descriptive name given to the dataset by the user.
    acqID       : int
        The number identifying the Multi-D acquisition for a given prefix
        name.
    datasetType : str
        The type of data contained in the dataset. Can be one of
        'locResults', 'locMetadata', or 'widefieldImage'.
    data        : mixed
        The actual microscopy data.
    channelID   : str
        The color channel associated with the dataset.
    dateID      : str
        The date of the acquistion in the format YYYY-mm-dd.
    posID       : int, or (int, int)
        The position identifier. It is a single element tuple if positions
        were manually set; otherwise, it's a 2-tuple indicating the x and y
        identifiers.
    sliceID     : int
        The number identifying the z-axis slice of the dataset.
    
    """
    def __init__(self, prefix, acqID, datasetType, data,
                 channelID = None, dateID = None,
                 posID = None, sliceID = None):
        if acqID is None:
            raise ValueError('acqID cannot be \'None\'.')
                
        if datasetType is None:
            raise ValueError('datasetType cannot be \'None\'.')
            
        # dateID should follow the format YYYY-MM-DD
        # Note that Python's 'and' short circuits, so the order here
        # is important. pattern.match(None) will raise a TypeError
        pattern = re.compile('\d{4}-\d{2}-\d{2}')
        if dateID and not pattern.match(dateID):
            raise ValueError(('Error: The date is not of the format '
                              'YYYY-MM-DD.'))

        _checkType(datasetType)
            
        self._acqID       = acqID
        self._channelID   = channelID
        self._data        = data
        self._posID       = posID
        self._prefix      = prefix
        self._sliceID     = sliceID
        self._datasetType = datasetType
        self._dateID      = dateID
        
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
    def datasetType(self):
        pass
    
    @abstractproperty
    def dateID(self):
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
        
    def getInfo(self):
        """Returns the dataset information (without the data) as a tuple.
        
        Returns
        -------
        prefix          : str
        acqID           : int
        datasetType     : str
        data            : mixed
        channelID       : str
        dateID          : str
        posID           : int, or (int, int)
        genericTypeName : string (optional)
        
        """
        if self._datasetType == 'generic':
            return self._prefix, self._acqID, self._datasetType, \
                   self._channelID, self._dateID, self._posID, self._sliceID, \
                   self.genericTypeName
        else:
            return self._prefix, self._acqID, self._datasetType, \
                   self._channelID, self._dateID, self._posID, self._sliceID
               
    def getInfoDict(self):
        """Returns the dataset information (without the data) as a dict.
        
        Returns
        -------
        dsIDs : dict
            Key-value pairs representing the datasetIDs.
        
        """
        dsIDs = {'acqID'       : self._acqID,
                 'channelID'   : self._channelID,
                 'posID'       : self._posID,
                 'prefix'      : self._prefix,
                 'sliceID'     : self._sliceID,
                 'datasetType' : self._datasetType,
                 'dateID'      : self._dateID}
                 
        if self._datasetType == 'generic':
            dsIDs['genericTypeName'] = self.genericTypeName
            
        return dsIDs
        
class GenericDatasetType(metaclass = ABCMeta):
    """Metaclass for a generic datasetType. Use this to add new datasetTypes.
    
    """
    @abstractproperty
    def genericTypeName():
        pass
    
    @abstractmethod
    def get():
        pass
    
    @abstractmethod
    def put():
        pass

"""Concrete classes
-------------------------------------------------------------------------------
"""
class Dataset(DatabaseAtom):
    """A concrete realization of a DatabaseAtom.
    
    Parameters
    ----------
    prefix      : str
        The descriptive name given to the dataset by the user.
    acqID       : int
        The number identifying the Multi-D acquisition for a given prefix
        name.
    datasetType : str
        The type of data contained in the dataset. Can be one of
        'locResults', 'locMetadata', or 'widefieldImage'.
    data        : mixed
        The actual microscopy data.
    channelID   : str
        The color channel associated with the dataset.
    dateID      : str
        The date of the acquistion in the format YYYY-mm-dd.
    posID       : int, or (int, int)
        The position identifier. It is a single element tuple if positions
        were manually set; otherwise, it's a 2-tuple indicating the x and y
        identifiers.
    sliceID     : int
        The number identifying the z-axis slice of the dataset.
    
    Attributes
    ----------
    prefix      : str
        The descriptive name given to the dataset by the user.
    acqID       : int
        The number identifying the Multi-D acquisition for a given prefix
        name.
    datasetType : str
        The type of data contained in the dataset. Can be one of
        'locResults', 'locMetadata', or 'widefieldImage'.
    data        : mixed
        The actual microscopy data.
    channelID   : str
        The color channel associated with the dataset.
    dateID      : str
        The date of the acquistion in the format YYYY-mm-dd.
    posID       : int, or (int, int)
        The position identifier. It is a single element tuple if positions
        were manually set; otherwise, it's a 2-tuple indicating the x and y
        identifiers.
    sliceID     : int
        The number identifying the z-axis slice of the dataset.
    
    """
    def __init__(self, prefix, acqID, datasetType, data,
                 channelID = None, dateID = None,
                 posID = None, sliceID = None):
        super(Dataset, self).__init__(prefix, acqID, datasetType, data,
                                      channelID = channelID,
                                      dateID    = dateID,
                                      posID     = posID,
                                      sliceID   = sliceID)
                                                
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
    def datasetType(self):
        return self._datasetType
        
    @property
    def dateID(self):
        return self._dateID
    
    @property
    def posID(self):
        return self._posID

    @property
    def prefix(self):
        return self._prefix
    
    @property
    def sliceID(self):
        return self._sliceID

class HDFDatabase(Database):
    """A HDFDatabase structure for managing SMLM data.
    
    Parameters
    ----------
    dbName : str or Path
        The name of the database file.
    widefieldPixelSize   : 2-tuple of float or None
        The x- and y-size of a widefield pixel in microns. This
        informationis used to write attributes to the widefield image for
        opening with other software libraries, such as the HDF5 Plugin for
        ImageJ and FIJI.
    
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
    def __init__(self, dbName, *args, widefieldPixelSize = None, **kwargs):
        self.widefieldPixelSize = widefieldPixelSize
        super(HDFDatabase, self).__init__(dbName)
    
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
        FilesGen['generic']        = []
                                                         
        # Build the dictionary of files with keys describing
        # their dataset type
        files = {}                                                 
        for datasetType in typesOfAtoms:
            files[datasetType] = sorted(FilesGen[datasetType])
        
        # Keep a running record of what datasets were parsed
        datasets = []        
        
        # Ensure that locResults get put first so the metadata has
        # a place to go.
        for dataset in files['locResults']:
            try:
                parser.parseFilename(dataset, datasetType = 'locResults')
                
                if not dryRun:
                    self.put(parser.getDatabaseAtom())
                    
                datasets.append(parser.getBasicInfo())
            except Exception as err:
                print("Unexpected error in build() while building locResults:",
                      sys.exc_info()[0])
                print(err)
        
        # Place all other data into the database
        del(files['locResults'])
        for currType in files.keys(): 
            
            for currFile in files[currType]:
                try:
                    parser.parseFilename(currFile, datasetType = currType)
                
                    if not dryRun:
                        self.put(parser.getDatabaseAtom())
                    
                    datasets.append(parser.getBasicInfo())
                except LocResultsDoNotExist:
                    # Do not fail the build if metadata cannot be put.
                    continue
                except Exception as err:
                    print("Unexpected error in build():",
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
        # TODO: Modify this to work with generic types
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
        
        returnDS = Dataset(prefix, acqID, datasetType, data,
                           channelID = channelID,
                           dateID    = dateID,
                           posID     = posID,
                           sliceID   = sliceID)
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
        # 'd' and underscores are needed for PyTables naming conventions
        if atom.dateID is not None:
            acqKey = '/'.join([atom.prefix,
                               'd' + atom.dateID.replace('-','_'),
                               atom.prefix]) + \
                     '_' + str(atom.acqID)
        else:
            acqKey = '/'.join([atom.prefix, atom.prefix]) + \
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
        # generic datasetTypes should be named after their genericTypeName
        if atom.datasetType != 'locMetadata' and atom.datasetType != 'generic':        
            return acqKey + '/' + atom.datasetType + otherIDs
        elif atom.datasetType == 'locMetadata':
            return acqKey + '/locResults' + otherIDs
        elif atom.datasetType == 'generic':
            return acqKey + '/' + atom.genericTypeName + otherIDs
            
    def get(self, dsID):
        """Returns an atomic dataset matching dsID from the database.
        
        Parameters
        ----------
        dsID     : Dataset
            A Dataset with a possibly empty 'data' field that may be used to
            identify the dataset.
            
        Returns
        -------
        dsID : Dataset
            The same Dataset but with a filled/modified data field.
        
        """
        ids = dsID.getInfoDict()             
        datasetType = ids['datasetType']
        
        if 'genericTypeName' in ids:
            assert ids['genericTypeName'] in config.__Registered_Generics__
            
        hdfKey   = self._genKey(dsID)

        # Ensure that the key exists        
        try:
            self._checkKeyExistence(dsID)
        except HDF5KeyExists:
            pass
        
        if datasetType == 'locResults':
            dsID.data = read_hdf(self._dbName, key = hdfKey)
        if datasetType == 'locMetadata':
            dsID.data = self._getLocMetadata(hdfKey)
        if datasetType == 'widefieldImage':
            hdfKey = hdfKey + '/image_data'
            dsID.data = self._getWidefieldImage(hdfKey)
        if datasetType == 'generic':
            dsID.data = dsID.get(self._dbName, hdfKey)
            
        return dsID
            
    def _getLocMetadata(self, hdfKey):
        """Returns the metadata associated with a localization dataset.
        
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
        with h5py.File(self._dbName, mode = 'r') as hdf:
            # Open the HDF file and get the dataset's attributes
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
                        md[currAttr[len(attrID):]] = \
                                        json.loads(hdf[hdfKey].attrs[currAttr])
                except IOError:
                    # Ignore attirbutes that are empty.
                    # See above comment.
                    pass
                
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
            
    def put(self, atom):
        """Writes a single database atom into the database.
        
        Parameters
        ----------
        atom   : DatabaseAtom or Dataset
        
        """
        self._checkKeyExistence(atom)
        key = self._genKey(atom)
        
        # The put routine varies with atom's dataset type.
        if atom.datasetType == 'locResults':
            try:
                hdf = HDFStore(self._dbName)
                hdf.put(key, atom.data, format = 'table',
                        data_columns = True, index = False)
            except:
                print("Unexpected error in put():", sys.exc_info()[0])
            finally:
                hdf.close()
                
            # Write the attributes to the dataset;
            self._writeDatasetIDs(atom)

        elif atom.datasetType == 'locMetadata':
            self._putLocMetadata(atom)
        elif atom.datasetType == 'widefieldImage':
            self._putWidefieldImage(atom)
            self._writeDatasetIDs(atom)
        elif atom.datasetType == 'generic':
            assert atom.genericTypeName in config.__Registered_Generics__, \
                   'Type {0} is unregistered.'.format(atom.genericTypeName)
            
            atom.put(self._dbName, key)
            self._writeDatasetIDs(atom)
    
    def _putLocMetadata(self, atom):
        """Writes localization metadata into the database.
        
        Parameters
        ----------
        atom   : DatabaseAtom
            
        """
        attrFlag = config.__HDF_AtomID_Prefix__
        mdFlag   = config.__HDF_Metadata_Prefix__
        
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
                
            # Used for identification during database queries
            attrKey = ('{0:s}{1:s}datasetType').format(mdFlag, attrFlag)
            attrVal = json.dumps('locMetadata')
            hdf[dataset].attrs[attrKey] = attrVal
            
        except KeyError:
            # Raised when the hdf5 key does not exist in the database.
            ids = json.dumps(atom.getInfoDict())
            raise LocResultsDoNotExist(('Error: Cannot not append metadata. '
                                        'No localization results exist with '
                                        'these atomic IDs: ' + ids))
        finally:
            hdf.close()
    
    @putWidefieldImageWithMicroscopyTiffTags        
    def _putWidefieldImage(self, atom):
        """Writes a widefield image into the database.
        
        Parameters
        ----------
        atom   : Dataset
            Dataset containing the widefield image to insert into the database.
        
        """
        assert atom.datasetType == 'widefieldImage', \
            'Error: atom\'s datasetType is not \'widefieldImage\''
        dataset = self._genKey(atom) + '/image_data'
        
        try:
            hdf = h5py.File(self._dbName, mode = 'a')
            
            hdf.create_dataset(dataset,
                               atom.data.shape,
                               data = atom.data)
                               
            if self.widefieldPixelSize is not None:
                # Write element_size_um attribute for HDF5 Plugin for ImageJ
                # Note that this takes pixel sizes in the format zyx
                elementSize = (1,
                               self.widefieldPixelSize[1],
                               self.widefieldPixelSize[0])
                hdf[dataset].attrs['element_size_um'] = elementSize
                
        finally:
            hdf.close()
            
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
        # TODO: Update this to work with generics
        _checkType(datasetType)       
        searchString = datasetType
        ap           = config.__HDF_AtomID_Prefix__
        mp           = config.__HDF_Metadata_Prefix__
        
        # Open the hdf file
        with h5py.File(self._dbName, 'r') as f:
            # Extract all localization datasets from the HDF5 file by matching
            # each group to the search string.
            # ('table' not in name) excludes the subgroup inside every
            # processed_localization parent group.
            resultGroups = []
            def find_locs(name):
                """Finds localization files matching the name pattern."""
                # Finds only datasets with the SMLM_datasetType attribute.
                if (ap + 'datasetType' in f[name].attrs) \
                       and (f[name].attrs[ap + 'datasetType'] == searchString):
                               resultGroups.append(name)
                               
                # locMetadata is not explicitly saved as a dataset,
                # so handle this case here
                if (searchString == 'locMetadata') \
                    and (ap + 'datasetType' in f[name].attrs) \
                    and (f[name].attrs[ap + 'datasetType'] == 'locResults') \
                    and (mp + ap + 'datasetType') in f[name].attrs:
                        resultGroups.append(name)
                
            f.visit(find_locs)
        
        # Read attributes of each key in resultGroups for SMLM_*
        # and convert them to a dataset ID.
        # Note: If you use Path and Not PurePosixPath, '/' will
        # become '\\' on Windows and you won't get the right keys.
        resultKeys = list(map(PurePosixPath, resultGroups))
        atomicIDs  = [self._genAtomicID(str(key)) for key in resultKeys]
        
        # Convert datasetType for locMetadata special case
        if searchString == 'locMetadata':
            for (index, atom) in enumerate(atomicIDs):
                # Can't set atom attributes directly, so make new ones
                ids = atom.getInfoDict()
                ids['datasetType'] = 'locMetadata'
                atomicIDs[index] = Dataset(ids['prefix'], ids['acqID'],
                                           'locMetadata', None,
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
    
    def _writeDatasetIDs(self, atom):
        """Writes B-Store dataset IDs as attributes of the dataset.
        
        Parameters
        ----------
        atom : Dataset
        
        """
        key        = self._genKey(atom)
        atomPrefix = self.atomPrefix
        with  h5py.File(self._dbName, mode = 'a') as hdf:
            hdf[key].attrs[atomPrefix + 'acqID']       = atom.acqID
            hdf[key].attrs[atomPrefix + 'channelID']   = \
                'None' if atom.channelID is None else atom.channelID
            hdf[key].attrs[atomPrefix + 'dateID']      = \
                'None' if atom.dateID is None else atom.dateID
            hdf[key].attrs[atomPrefix + 'posID']       = \
                'None' if atom.posID is None else atom.posID
            hdf[key].attrs[atomPrefix + 'prefix']      = atom.prefix
            hdf[key].attrs[atomPrefix + 'sliceID']     = \
                'None' if atom.sliceID is None else atom.sliceID
            hdf[key].attrs[atomPrefix + 'datasetType'] = atom.datasetType
            
            # Current version of this software
            hdf[key].attrs[atomPrefix +'Version'] = \
                                               config.__bstore_Version__
                                               
            # Write the generic type name if this is a generic type
            if atom.datasetType == 'generic':
                hdf[key].attrs[atomPrefix + 'genericTypeName'] = \
                                                           atom.genericTypeName
            
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