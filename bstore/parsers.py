import json
import pathlib
import re
import warnings
from bstore import database, config
import pandas as pd
from abc import ABCMeta, abstractmethod, abstractproperty
from matplotlib.pyplot import imread

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

class Parser(metaclass = ABCMeta):
    """Creates machine-readable data structures with acquisition info.
    
    Attributes
    ----------
    acqID       : int
        The number identifying the Multi-D acquisition for a given prefix name.
    channelID   : str
        The color channel associated with the dataset.
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
    def __init__(self, acqID, channelID, posID, prefix, sliceID, datasetType):
        """Initialize the parser's metadata information.
        
        Parameters
        ----------
        acqID       : int
            The number identifying the Multi-D acquisition for a given prefix
            name.
        channelID   : str
            The color channel associated with the dataset.
        posID       : int, or (int, int)
            The position identifier. It is a single element tuple if positions
            were manually set; otherwise, it's a 2-tuple indicating the x and y
            identifiers.
        prefix      : str
            The descriptive name given to the dataset by the user.
        sliceID     : int
            The number identifying the z-axis slice of the dataset.
        datasetType : str
            The type of data contained in the dataset. Can be one of
            'locResults', 'locMetadata', or 'widefieldImage'.
        
        """
        if datasetType not in database.typesOfAtoms:
            raise DatasetError(datasetType)
        
        # These are the essential pieces of information to identify a dataset.
        self.acqID       =       acqID
        self.channelID   =   channelID
        self.posID       =       posID
        self.prefix      =      prefix
        self.sliceID     =     sliceID
        self.datasetType = datasetType
        
    def getBasicInfo(self):
        """Return a dictionary containing the basic dataset information.
        
        """
        basicInfo = {
                     'acqID'         :       self.acqID,
                     'channelID'     :   self.channelID,
                     'posID'         :       self.posID,
                     'prefix'        :      self.prefix,
                     'sliceID'       :     self.sliceID,
                     'datasetType'   : self.datasetType
                     }
                     
        return basicInfo
        
    @abstractproperty
    def data(self):
        """Loads the data into memory and maps it to the correct format.
        
        """
        pass
    
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
    
    @abstractproperty
    def uninitialized(self):
        """Indicates that all dataset information has been removed.
        
        This property helps ensure that a Parser never holds onto partial
        information about a Dataset.
        """
        pass

class MMParser(Parser):
    """Parses a Micro-Manager-based file for the acquisition info.
    
    Attributes
    ----------
    channelIdentifier : dict
        All of the channel identifiers that the MMParser recognizes.
    dataGetter        : func
        Optional function for customized reading of data.
    
    """
    # This dictionary contains all the channel identifiers MMParser
    # knows natively.
    channelIdentifier = config.__Channel_Identifier__ 
                         
    # All identifiers of a widefield image in a file name.
    widefieldIdentifier = ['WF']
    
    def __init__(self, dataGetter = None):
        # Start uninitialized because parseFilename has not yet been called
        self.uninitialized = True
        
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
        
    def _getDataDefault(self):
        """Default function used for reading the data in a database atom.
        
        This function defines the default behaviors for reading data.
        It may be overriden by this Parser's constructor to allow for
        more specialized reading, such as converting DataFrame column
        names upon import.
        
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
            return self._metadata
            
        elif self.datasetType == 'widefieldImage':
            # Load the image data only when called
            return imread(str(self._fullPath))
            
    @property
    def uninitialized(self):
        return self._uninitialized
        
    @uninitialized.setter
    def uninitialized(self, value):
        """Resets the Parser an uninitialized state if True is provided.
        
        Parameters
        ----------
        value : bool
        """
        if isinstance(value, bool):
            self._uninitialized = value
            
            if value:
                self._fullPath      = None
                self._filename      = None
                self._metadata      = None
                self.acqID          = None
                self.channelID      = None
                self.posID          = None
                self.prefix         = None
                self.sliceID        = None
                self.datasetType    = None
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
        dba = database.Dataset(ids['acqID'], ids['channelID'],
                                   self.data, ids['posID'], ids['prefix'],
                                   ids['sliceID'], ids['datasetType'])
        return dba
    
    def parseFilename(self, filename, datasetType = 'locResults'):
        """Parse the filename to extract the acquisition information.
        
        Running this method will reset the parser to an uninitialized state
        before initializing it with the new data.
        
        Parameters
        ----------
        filename    : str or Path
            A string or pathlib Path object containing the dataset's filename.
        datasetType : str
            One of 'locResults', 'locMetadata', or 'widefieldImage'.
            
        """
        # Reset the parser
        self.uninitialized = True   
        
        if datasetType not in database.typesOfAtoms:
            raise DatasetError(datasetType)           
        
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
            super(MMParser, self).__init__(*parsedData, datasetType)
        elif datasetType == 'locMetadata':
            parsedData = self._parseLocMetadata(fullPath)
            (acqID, channelID, posID, prefix, sliceID, metadata) = parsedData
            super(MMParser, self).__init__(acqID, channelID, posID,
                                           prefix, sliceID, datasetType)           
            self._metadata = metadata
        elif datasetType == 'widefieldImage':
            parsedData = self._parseWidefieldImage(filename)
            super(MMParser, self).__init__(*parsedData, datasetType)
            
        # Parser is now set and initialized.
        self._uninitialized = False
        
    def _parseLocResults(self, filename, extractAcqID = True):
        """Parse a localization results file.
        
        Parameters
        ----------
        filename : str
            The filename for the current file to parse.
        extractAcqID : bool
            Should an acquisition ID be extracted from the filename? This
            is useful for widefield images because they will not contain
            an acquisition ID that is automatically inserted into the
            filename.
            
        Returns
        -------
        acqID     : int
        channelID : str
        posID     : (int,) or (int, int)
        prefix    : str
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
        
        # TODO: Copy this part from database._genAtomicID and write tests       
        sliceID = None
        
        return acqID, channelID, posID, prefix, sliceID
        
    def _parseLocMetadata(self, fullPath):
        """Parse a localization metadata file.
        
        Parameters
        ----------
        fullPath : Path
            pathlib Path object to the metadata file.
            
        Returns
        -------
        acqID     : int
        channelID : str
        posID     : (int,) or (int, int)
        prefix    : str
        sliceID   : int
        metadata  : dict
            A dictionary containing the metadata for this acquisition.
        
        """       
        with open(str(fullPath), 'r') as file:
            metadata = json.load(file)
        
        filename = str(fullPath.name)
            
        acqID, channelID, posID, prefix, sliceID = \
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

        return acqID, channelID, posID, prefix, sliceID, metadata
        
    def _parseWidefieldImage(self, filename):
        """Parse a widefield image for the Dataset interface.
        
        Parameters
        ----------
        filename : str
            The filename for the current file to parse.
            
        Returns
        -------
        acqID     : int
        channelID : str
        posID     : (int,) or (int, int)
        prefix    : str
        sliceID   : int
            
        """
        acqID, channelID, posID, prefix, sliceID = \
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
            
        return acqID, channelID, posID, prefix, sliceID
        
class HDFParser(Parser):
    """Parses HDF groups and datasets to extract their acquisition information.
    
    """
    pass

class DatasetError(Exception):
    """Error raised when a bad datasetType is passed to Parser.
    
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