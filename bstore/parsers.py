# © All rights reserved. ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Switzerland, Laboratory of Experimental Biophysics, 2016
# See the LICENSE.txt file for more details.

import json
import pathlib
import re
import warnings
from bstore import database, config
import pandas as pd
from abc import ABCMeta, abstractmethod, abstractproperty
from matplotlib.pyplot import imread
from os.path import splitext
from tifffile import TiffFile
import importlib
import sys

"""Metaclasses
-------------------------------------------------------------------------------
"""
class Parser(metaclass = ABCMeta):
    """Translates SMLM files to machine-readable data structures.
    
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
    channelID   : str
        The color channel associated with the dataset.
    dateID      : str
        The date of the acquistion in the format YYYY-mm-dd.
    genericTypeName : str
        The specfic type of generic dataset currently held by the parser.
    posID       : int, or (int, int)
        The position identifier. It is a single element tuple if positions
        were manually set; otherwise, it's a 2-tuple indicating the x and y
        identifiers.
    sliceID     : int
        The number identifying the z-axis slice of the dataset.
    
    Attributes
    ----------
    acqID       : int
        The number identifying the Multi-D acquisition for a given prefix name.
    channelID   : str
        The color channel associated with the dataset.
    dateID      : str
        The date of the acquistion in the format YYYY-mm-dd.
    genericTypeName : str
        The specfic type of generic dataset currently held by the parser.
    posID       : (int,) or (int, int)
        The position identifier. It is a single element tuple if positions were
        manually set; otherwise, it's a 2-tuple indicating the x and y
        identifiers.
    prefix      : str
        The descriptive name given to the dataset by the user.
    sliceID     : int
        The number identifying the z-axis slice of the dataset.
    datasetType : str
        The type of data contained in the dataset. Can be one of 'locResults',
        'locMetadata', or 'widefieldImage'.
       
    """
    def __init__(self, prefix, acqID, datasetType,
                 channelID = None, dateID = None, genericTypeName = None,
                 posID = None, sliceID = None,):

        if datasetType not in config.__Types_Of_Atoms__:
            raise DatasetError(datasetType)
            
        if (genericTypeName is not None) \
            and (genericTypeName not in config.__Registered_Generics__):
            raise GenericTypeError(genericTypeName)
        
        
        # These are the essential pieces of information to identify a dataset.
        self.acqID           =           acqID
        self.channelID       =       channelID
        self.dateID          =          dateID
        self.genericTypeName = genericTypeName
        self.posID           =           posID
        self.prefix          =          prefix
        self.sliceID         =         sliceID
        self.datasetType     =     datasetType
    
    @abstractproperty
    def data(self):
        """Loads the data into memory and maps it to the correct format.
        
        """
        pass
    
    @property
    def prefix(self):
        return self._prefix
        
    @prefix.setter
    def prefix(self, value):
        if value:
            # Replaces spaces with '_' in prefix.
            # This avoids problems with spaces in PyTables
            self._prefix = value.replace(' ', '_')
    
    def getBasicInfo(self):
        """Return a dictionary containing the basic dataset information.
        
        """
        basicInfo = {
                     'acqID'           : self.acqID,
                     'channelID'       : self.channelID,
                     'dateID'          : self.dateID,
                     'posID'           : self.posID,
                     'prefix'          : self.prefix,
                     'sliceID'         : self.sliceID,
                     'datasetType'     : self.datasetType,
                     'genericTypeName' : self.genericTypeName
                     }
                     
        return basicInfo

    @abstractmethod
    def getDatabaseAtom(self):
        """Returns one atomic unit for insertion into the Database.
        
        """
        pass
    
    @abstractmethod
    def parseFilename(self):
        """Parses a file for conversion to a DatabaseAtom.
        
        """
        pass
  
"""
Concrete classes
-------------------------------------------------------------------------------
"""
class FormatMap(dict):
    """Two-way map for mapping one localization file format to another.
    
    FormatMap subclasses dict and acts like a two-way mapping between
    key-value pairs, unlike dict which provides only a one-way relationship.
    In the case where a key is missing, the dict returns the input key.
    This functionality greatly assists in converting header files for which
    no translation between column names is defined.
    
    To use this class, simply pass a dict to the FormatMap's constructor.
    Alternatively, create a FormatMap, which creates an empty dict. Then add
    fields as you wish.
    
    Parameters
    ----------
    init_dict : dict
        The dictionary to convert to a two-way mapping.
    
    References
    ----------
    [1] http://stackoverflow.com/questions/1456373/two-way-reverse-map
    
    """
    def __init__(self, init_dict = None):
        super(dict, self).__init__()
        
        # Populate the two-way dict if supplied
        if init_dict:
            for key, value in init_dict.items():
                self.__setitem__(key, value)
    
    def __setitem__(self, key, value):
        if key   in self: del self[key]
        if value in self: del self[value]
        dict.__setitem__(self, key, value)
        dict.__setitem__(self, value, key)
    
    def __getitem__(self, key):
        try:
            val = dict.__getitem__(self, key)
        except KeyError:
            # If the key doesn't exist, then return the key. This
            # allows the use for pre-defined mappings between
            # header columns even when not all possible mappings
            # are defined.
            val = key
        
        return  val
        
    def __delitem__(self, key):
        dict.__delitem__(self, self[key])
        dict.__delitem__(self, key)
        
    def __len__(self):
        return dict.__len__(self) // 2

class MMParser(Parser):
    """Parses a LEB Micro-Manager-based file for the acquisition info.
    
    Parameters
    ----------
    dataGetter : func
        The function defining how to read the various datasetTypes. Should be
        similar to _getDataDefault().
    readTiffTags : bool
        Determines whether Tiff tags are read in addition to the image data.
        This may cause problems if set to true and the image is not a Tiff file
        whose format is supported by tifffile.
        
    References
    ----------
    1. https://pypi.python.org/pypi/tifffile
    
    Attributes
    ----------
    channelIdentifier   : dict
        All of the channel identifiers that the MMParser recognizes.
    dataGetter          : func
        Optional function for customized reading of data.
    readTiffTags        : bool
        Determines whether Tiff tags are read in addition to the image data.
        This may cause problems if set to true and the image is not a Tiff
        whose format is supported by tifffile.
    uninitialized       : bool
        Indicates whether the Parser currently possesses parsed information.
    widefieldIdentifier : str
        The string identifying the widefield image number.
    
    """
    # This dictionary contains all the channel identifiers MMParser
    # knows natively.
    channelIdentifier = config.__Channel_Identifier__ 
    
                         
    # All identifiers of a widefield image in a file name.
    widefieldIdentifier = ['WF']
    
    def __init__(self, dataGetter = None, readTiffTags = False):
        # Start uninitialized because parseFilename has not yet been called
        self.uninitialized = True
        
        self.readTiffTags  = readTiffTags
        
        # Allows for customized reading of datasets, such as converting
        # DataFrame column names or for reading non-csv files.
        if dataGetter:        
            self._dataGetter = dataGetter
        else:
            self._dataGetter = self._getDataDefault
    
    @property
    def data(self):
        # The if statement is required because _getDataDefault is a bound
        # method. This means it will always receive an instance of the
        # calling parser as an argument. If a custom dataGetter is set,
        # the self argument must be passed explicitly.
        if self._dataGetter == self._getDataDefault:
            return self._dataGetter()
        else:
            return self._dataGetter(self)
            
    @property
    def uninitialized(self):
        return self._uninitialized
        
    @uninitialized.setter
    def uninitialized(self, value):
        """Resets the Parser to an uninitialized state if True is provided.
        
        Parameters
        ----------
        value : bool
        """
        if isinstance(value, bool):
            self._uninitialized = value
            
            if value:
                self._fullPath       = None
                self._filename       = None
                self._metadata       = None
                self.acqID           = None
                self.channelID       = None
                self.dateID          = None
                self.genericTypeName = None
                self.posID           = None
                self.prefix          = None
                self.sliceID         = None
                self.datasetType     = None
        else:
            raise ValueError('Error: _uninitialized must be a bool.')
            
    def getDatabaseAtom(self):
        """Returns an object capable of insertion into a SMLM database.
        
        Returns 
        -------
        dba : DatabaseAtom
            One atomic unit for insertion into the database.
        
        """
        if self._uninitialized:
            raise ParserNotInitializedError(('Error: Parser has not yet '
                                             'been initialized.'))
        
        ids = self.getBasicInfo()
        if ids['datasetType'] != 'generic':
            dba = database.Dataset(ids['prefix'], ids['acqID'],
                                   ids['datasetType'], self.data,
                                   channelID = ids['channelID'],
                                   dateID = ids['dateID'],
                                   posID = ids['posID'], 
                                   sliceID = ids['sliceID'])
        elif ids['datasetType'] == 'generic':
            mod = importlib.import_module('bstore.generic_types.{0:s}'.format(
                                                       ids['genericTypeName']))
            genericType = getattr(mod, ids['genericTypeName'])
            
            dba = genericType(ids['prefix'], ids['acqID'], ids['datasetType'],
                              self.data, channelID = ids['channelID'],
                              dateID = ids['dateID'], posID = ids['posID'], 
                              sliceID = ids['sliceID'])
            
        return dba
        
    def _getDataDefault(self):
        """Default function used for reading the data in a database atom.
        
        This function defines the default behaviors for reading data.
        It may be overriden by this Parser's constructor to allow for
        more specialized reading, such as converting DataFrame column
        names upon import.
        
        Only one of many possible returns is actually returned by this
        function, depending on the datasetType.
        
        Returns
        -------
        df       : Pandas DataFrame
            The localizations if datasetType == 'locResults'.
        metadata : dict
            Dictionary of JSON strings containing the localization metadata.
        img      : NumPy array
            2D NumPy array containing the image.
        
        """
        if self._uninitialized:
            raise ParserNotInitializedError(('Error: this parser has not yet'
                                             ' been initialized.'))
        
        if self.datasetType == 'locResults':
            # Loading the csv file when data() is called reduces the
            # chance that large DataFrames do not needlessly
            # remain in memory.
            with open(str(self._fullPath), 'r') as file:            
                df = pd.read_csv(file)
                return df
                
        elif self.datasetType == 'locMetadata':
            # self._metadata is set by self._parseLocMetadata
            metadata = self._metadata
            return metadata
            
        elif self.datasetType == 'widefieldImage':
            # Load the image data only when called
            if self.readTiffTags:
                with TiffFile(str(self._fullPath)) as tif:
                    return tif
            else:
                # Read image data as a NumPy array
                img = imread(str(self._fullPath))
                return img
        elif self.datasetType == 'generic':
            # Don't return anything; generics know how to get their own data.
            return None
    
    def parseFilename(self, filename, datasetType = 'locResults',
                      genericTypeName = None):
        """Parse the filename to extract the acquisition information.
        
        Running this method will reset the parser to an uninitialized state
        before initializing it with the new data.
        
        Parameters
        ----------
        filename        : str or Path
            A string or pathlib Path object containing the dataset's filename.
        datasetType     : str
            One of the allowable datasetTypes.
        genericTypeName : str or None
            The generic dataset type to parse.
            
        """
        # Reset the parser
        self.uninitialized = True   
        
        if datasetType not in config.__Types_Of_Atoms__:
            raise DatasetError(datasetType)   
        if (genericTypeName is not None) \
                   and (genericTypeName not in config.__Registered_Generics__):
            raise GenericTypeError(genericTypeName)
        
        # Convert Path objects to strings
        if isinstance(filename, pathlib.PurePath):
            fullPath = filename
            filename = str(filename.name)
        elif isinstance(filename, str):
            fullPath = pathlib.Path(filename)
            filename = str(fullPath.name)
        else:
            raise TypeError('Unrecognized type for filename.')
        
        # Used to access data
        self._filename = filename
        self._fullPath = fullPath
            
        if datasetType == 'locResults':
            parsedData = self._parseLocResults(filename)
            (prefix, acqID, channelID, dateID, posID, sliceID) = parsedData

            # Assign ID's to the class fields            
            super(MMParser, self).__init__(prefix, acqID, datasetType,
                                           channelID = channelID,
                                           dateID = dateID, posID = posID,
                                           sliceID = sliceID)
        elif datasetType == 'locMetadata':
            parsedData = self._parseLocMetadata(fullPath)
            (prefix, acqID, channelID, dateID, posID, sliceID, metadata) = \
                                                                     parsedData
                                                                     
            # Assign ID's to the class fields  
            super(MMParser, self).__init__(prefix, acqID, datasetType,
                                           channelID = channelID,
                                           dateID = dateID, posID = posID,
                                           sliceID = sliceID)
            self._metadata = metadata
        elif datasetType == 'widefieldImage':
            parsedData = self._parseWidefieldImage(filename)
            (prefix, acqID, channelID, dateID, posID, sliceID) = parsedData            
            
            # Assign ID's to the class fields
            super(MMParser, self).__init__(prefix, acqID, datasetType,
                                           channelID = channelID,
                                           dateID = dateID, posID = posID,
                                           sliceID = sliceID)
                                           
        elif datasetType == 'generic':
            parsedData = self._parseLocResults(filename)
            (prefix, acqID, channelID, dateID, posID, sliceID) = parsedData
          
            super(MMParser, self).__init__(prefix, acqID, datasetType,
                                           channelID = channelID,
                                           dateID = dateID, posID = posID,
                                           sliceID = sliceID,
                                           genericTypeName = genericTypeName)            
            
        # Parser is now set and initialized.
        self._uninitialized = False
        
    def _parseLocMetadata(self, fullPath):
        """Parse a localization metadata file.
        
        Parameters
        ----------
        fullPath : Path
            pathlib Path object to the metadata file.
            
        Returns
        -------
        prefix    : str
        acqID     : int
        channelID : str
        dateID    : str
        posID     : (int,) or (int, int)
        sliceID   : int
        metadata  : dict
            A dictionary containing the metadata for this acquisition.
        
        """       
        with open(str(fullPath), 'r') as file:
            metadata = json.load(file)
        
        filename = str(fullPath.name)
            
        prefix, acqID, channelID, dateID, posID, sliceID = \
                                            self._parseLocResults(filename)
        
        # Remove non-matching position information from the metadata
        try:
            if len(posID) == 2:
                pos = 'Pos_{0:0>3d}_{1:0>3d}'.format(posID[0], posID[1])
            else:
                pos = 'Pos{0:d}'.format(posID[0])
            
            newPosList= [currPos \
                         for currPos in metadata['InitialPositionList'] \
                         if pos in currPos['Label']]
            assert len(newPosList) <= 1,\
                'Multiple positions found in metadata.'
            metadata['InitialPositionList'] = newPosList[0]
        except TypeError:
            # When no position information is in the filename
            metadata['InitialPositionList'] = None
            
        # TODO: FUTURE IMPLEMENTATION
        # Isolate slice position from and change metadata accordingly

        return prefix, acqID, channelID, dateID, posID, sliceID, metadata
        
    def _parseLocResults(self, filename, extractAcqID = True):
        """Parse a localization results file.
        
        Parameters
        ----------
        filename     : str
            The filename for the current file to parse.
        extractAcqID : bool
            Should an acquisition ID be extracted from the filename? This
            is useful for widefield images because they will not contain
            an acquisition ID that is automatically inserted into the
            filename.
            
        Returns
        -------
        prefix    : str
        acqID     : int
        channelID : str
        dateID    : str
        posID     : (int,) or (int, int)
        sliceID   : int
        
        """
        # Remove any leading underscores
        filename = filename.lstrip('_')        
        
        # Split the string at 'MMStack'
        prefixRaw, suffixRaw = filename.split('_MMStack_')         
            
        # Obtain the acquisition ID
        prefixRawParts = prefixRaw.split('_')
        if extractAcqID:
            acqID          = int(prefixRawParts[-1])
            prefix    = '_'.join(prefixRawParts[:-1])
        else:
            # This must be set elsewhere, such as by a widefield image
            # tag. Not setting it results in an error when instantiating
            # a Dataset instance.
            acqID  = None
            
            # Cannot simply use prefixRaw because spurious underscores
            # will survive through into prefix
            prefix = '_'.join(prefixRawParts)
        
        # Obtain the channel ID and prefix
        # Extract any channel identifiers if present using
        # channelIdentifer dict
        prefix    = re.sub(r'\_\_+', '_', prefix) # Remove repeats of '_'
        channelID = [channel for channel in self.channelIdentifier.keys()
                     if channel in prefix]
        assert (len(channelID) <= 1), channelID
        try:
            channelID       = channelID[0]
            channelIDString = re.search(r'((\_' + channelID +              \
                                            ')\_?$)|((^\_)?' + channelID + \
                                            '(\_)?)',
                                        prefix)
            prefix = prefix.replace(channelIDString.group(), '')
        except IndexError:
            # When there is no channel identifier found, set it to None
            channelID = None
    
        # Obtain the position ID using regular expressions
        # First, extract strings like 'Pos0' or 'Pos_003_002
        positionRaw = re.search(r'Pos\_\d{1,3}\_\d{1,3}|Pos\d{1,}', suffixRaw)
        if positionRaw == None:
            posID = None
        else:
            # Next, extract the digits and convert them to a tuple
            indexes = re.findall(r'\d{1,}', positionRaw.group(0))
            posID   = tuple([int(index) for index in indexes])
             
        # These are not currently implemented by the MMParser
        sliceID = None
        dateID  = None
        
        return prefix, acqID, channelID, dateID, posID, sliceID
        
    def _parseWidefieldImage(self, filename):
        """Parse a widefield image for the Dataset interface.
        
        Parameters
        ----------
        filename : str
            The filename for the current file to parse.
            
        Returns
        -------
        prefix    : str
        acqID     : int
        channelID : str
        dateID    : str
        posID     : (int,) or (int, int)
        sliceID   : int
            
        """
        prefix, acqID, channelID, dateID, posID, sliceID = \
                        self._parseLocResults(filename, extractAcqID = False)
                        
        # Extract the widefield image identifier from prefix and use it
        # to set the acquisition ID. See the widefieldIdentifier dict.
        wfID = [wfFlag for wfFlag in self.widefieldIdentifier
                if wfFlag in prefix]
        assert (len(wfID) <= 1), wfID
        try:
            wfID       = wfID[0]
            wfIDString = re.search(r'((\_' + wfID +                \
                                   '\_?\d+)\_?$)|((^\_)?' + wfID + \
                                   '\_*\d+(\_?))', prefix)
            prefix = prefix.replace(wfIDString.group(), '')
        except IndexError:
            # When there is no widefield identifier found, set
            # acqID to None
            warnings.warn(
                'Warning: No widefield ID detected in {0:s}.'.format(prefix)
                )
            acqID = None
        else:
            acqID = re.findall(r'\d+', wfIDString.group())
            assert len(acqID) == 1, 'Error: found multiple acqID\'s.'
            acqID = int(acqID[0])
            
        return prefix, acqID, channelID, dateID, posID, sliceID
        
class SimpleParser(Parser):
    """A simple parser for extracting acquisition information.
    
    The SimpleParser converts files of the format prefix_acqID.* into
    DatabaseAtoms for insertion into a database. * may represent .csv files
    (for locResults), .json (for locMetadata), and .tif (for widefieldImages).
    
    """
    def __init__(self):
        self._initialized = False

    @property
    def data(self):
        """Returns the data stored in the current file.
        
        Only one of many possible returns is actually returned by this
        function, depending on the datasetType.
        
        Returns
        -------
        df       : Pandas DataFrame
            The localizations if datasetType == 'locResults'.
        metadata : dict
            Dictionary of JSON strings containing the localization metadata.
        img      : NumPy array
            2D NumPy array containing the image.
            
        """
        if self.datasetType == 'locResults':
            # Loading the csv file when data() is called reduces the
            # chance that large DataFrames do not needlessly
            # remain in memory.
            with open(str(self._fullPath), 'r') as file:            
                df = pd.read_csv(file)
                return df
                
        elif self.datasetType == 'locMetadata':
            # Read the txt file and convert it to a JSON string.
            with open(str(self._fullPath), 'r') as file:
                metadata = json.load(file)
                return metadata
            
        elif self.datasetType == 'widefieldImage':
            # Load the image data only when called
            return imread(str(self._fullPath))
    
    def getDatabaseAtom(self):
        """Returns an object capable of insertion into a SMLM database.
        
        Returns 
        -------
        dba : Dataset
            One atomic dataset for insertion into the database.
        
        """
        if not self._initialized:
            raise ParserNotInitializedError('Parser not initialized.')
        
        ids = self.getBasicInfo()
        dba = database.Dataset(ids['prefix'], ids['acqID'], ids['datasetType'],
                               self.data, channelID = ids['channelID'],
                               dateID = ids['dateID'], posID = ids['posID'], 
                               sliceID = ids['sliceID'])
        return dba    
    
    def parseFilename(self, filename, datasetType = 'locResults'):
        """Converts a filename into a DatabaseAtom.
        
        Parameters
        ----------
        filename      : str or Path
            A string or pathlib Path object containing the dataset's filename.
        datasetType   : str
            The type of the dataset being parsed. This tells the Parser
            how to interpret the data.
            
        """
        # Check for a valid datasetType
        if datasetType not in database.typesOfAtoms:
            raise DatasetError(datasetType)        
        
        try:
            # Save the full path to the file for later.
            # If filename is already a Path object, this does nothing.
            self._fullPath = pathlib.Path(filename)        
            
            # Convert Path objects to strings if Path is supplied
            if isinstance(filename, pathlib.PurePath):
                filename = str(filename.name)
    
            # Remove file type ending and any parent folders
            # Example: 'path/to/HeLa_Control_7.csv' becomes 'HeLa_Control_7'
            rootName = splitext(filename)[0].split('/')[-1]
            
            # Extract the prefix and acqID
            prefix, acqID = rootName.rsplit('_', 1)
            acqID = int(acqID)
            
            # Initialize the Parser
            super(SimpleParser, self).__init__(prefix, acqID, datasetType)
            self._initialized = True
        except:
            self._initialized = False
            print('Error: File could not be parsed.', sys.exc_info()[0])
            raise

"""
Exceptions
-------------------------------------------------------------------------------
"""    
class DatasetError(Exception):
    """Error raised when a bad datasetType is passed to Parser.
    
    """
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)
        
class GenericTypeError(Exception):
    """Error raised when a bad genericTypeName is passed to Parser.
    
    """
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)
        
class ParserNotInitializedError(Exception):
    """ Raised when Parser is requested to return data but is not initialized.
    
    """
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)