# © All rights reserved. ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Switzerland, Laboratory of Experimental Biophysics, 2016
# See the LICENSE.txt file for more details.

import pathlib
import re
import warnings
from bstore import config
from abc import ABCMeta, abstractmethod
from os.path import splitext
import importlib
import sys

__version__ = config.__bstore_Version__

"""Metaclasses
-------------------------------------------------------------------------------
"""
class Parser(metaclass = ABCMeta):
    """Translates SMLM files to machine-readable data structures.
    
    Parameters
    ----------
    datasetIDs : dict
        The ID fields and their values that identify the datset inside the
        database.
    
    Attributes
    ----------
    datasetIDs : dict
        The ID fields and their values that identify the datset inside the
        database.   
       
    """
    def __init__(self):
        # Holds a parsed dataset.
        self._dataset = None
    
    @property
    def dataset(self):
        if self._dataset:
            return self._dataset
        else:
            raise ParserNotInitializedError('Error: There is currently no'
                                            'parsed dataset to return.')
        
    @dataset.setter
    def dataset(self, ds):
        self._dataset = ds
    
    @abstractmethod
    def parseFilename(self):
        """Parses a file for conversion to a Dataset.
        
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
    initialized         : bool
        Indicates whether the Parser currently possesses parsed information.
    widefieldIdentifier : str
        The string identifying the widefield image number.
    
    """
    # This dictionary contains all the channel identifiers MMParser
    # knows natively.
    channelIdentifier = config.__Channel_Identifier__ 
    
                         
    # All identifiers of a widefield image in a file name.
    widefieldIdentifier = ['WF']
    
    def __init__(self):
        # Start uninitialized because parseFilename has not yet been called
        self.initialized   = False
    
    @property
    def dataset(self):
        if self.initialized:
            return self._dataset
        else:
            raise ParserNotInitializedError('Error: No dataset is parsed.')
    
    @dataset.setter
    def dataset(self, ds):
        self._dataset = ds
        
    @property
    def initialized(self):
        return self._initialized
        
    @initialized.setter
    def initialized(self, value):
        """Resets the Parser to an uninitialized state if True is provided.
        
        Parameters
        ----------
        value : bool
        """
        if isinstance(value, bool):
            self._initialized = value
            
            if value == False:
                self.dataset = None
        else:
            raise ValueError('Error: initialized must be a bool.')

    def parseFilename(self, filename, datasetType = 'LocResults'):
        """Parse the filename to extract the acquisition information.
        
        Running this method will reset the parser to an uninitialized state
        before initializing it with the new data.
        
        Parameters
        ----------
        filename        : str or Path
            A string or pathlib Path object containing the dataset's filename.
        datasetType     : str
            One of the registered datasetTypes.
            
        """
        # Reset the parser
        self.initialized = False   
        
        if datasetType not in config.__Registered_DatasetTypes__:
            raise DatasetTypeError(('{} is not a registered '
                                    'type.').format(datasetType)) 
        
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
        
        try:
            # Do parsing for particular types here
            if datasetType   == 'WidefieldImage':
                parsedData = self._parseWidefieldImage(filename)
            else:
                parsedData = self._parse(filename)
        except:
            raise ParseFilenameFailure(('Error: File could not be parsed.',
                                        sys.exc_info()[0]))
        
        # Build the return dataset
        prefix, acqID, channelID, dateID, posID, sliceID = parsedData
        idDict = {'prefix' : prefix, 'acqID' : acqID, 'channelID' : channelID,
                  'dateID' : dateID, 'posID' : posID, 'sliceID' : sliceID}
        
        mod   = importlib.import_module('bstore.datasetTypes.{0:s}'.format(
                                                                  datasetType))
        dType = getattr(mod, datasetType)
            
        self.dataset = dType(datasetIDs = idDict)           
            
        # Parser is now set and initialized.
        self.initialized = True
        
    def _parse(self, filename, extractAcqID = True):
        """Parse a generic file, i.e. one not requiring special treatment.
        
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
        
        # PyTables has problems with spaces in the name
        prefix = prefix.replace(' ', '_')        
        
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
                        self._parse(filename, extractAcqID = False)
                        
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
    DatabaseAtoms for insertion into a database. * represents filename
    extensions like .csv, .json, and .tif.
    
    """            
    def parseFilename(self, filename, datasetType = 'Localizations'):
        """Converts a filename into a DatabaseAtom.
        
        Parameters
        ----------
        filename      : str or Path
            A string or pathlib Path object containing the dataset's filename.
        datasetType   : str
            The type of the dataset being parsed. This tells the Parser
            how to interpret the data.
            
        """
        # Resets the parser
        self.dataset = None        
        
        # Check for a valid datasetType
        if datasetType not in config.__Registered_DatasetTypes__:
            raise DatasetTypeError(('{} is not a registered '
                                    'type.').format(datasetType))     
        
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
            
            # Build the return dataset
            idDict = {'prefix' : prefix, 'acqID' : acqID,
                      'channelID' : None, 'dateID' : None,
                      'posID' : None, 'sliceID' : None}
        
            mod   = importlib.import_module('bstore.datasetTypes.{0:s}'.format(
                                                                  datasetType))
            dType             = getattr(mod, datasetType)
            self.dataset      = dType(datasetIDs = idDict)
            self.dataset.data = self.dataset.readFromFile(self._fullPath)
        except:
            raise ParseFilenameFailure(('Error: File could not be parsed.',
                                        sys.exc_info()[0]))

"""
Exceptions
-------------------------------------------------------------------------------
"""    
class DatasetTypeError(Exception):
    """Error raised when a bad datasetTypeName is passed to Parser.
    
    """
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)
        
class ParseFilenameFailure(Exception):
    """Raised when Parser fails to parser a filename.
    
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