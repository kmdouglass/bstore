import pathlib
import re

# This dictionary contains all the channel identifiers DataSTORM knows natively
channelIdentifier = {'A647' : 'AlexaFluor 647',
                     'A750' : 'AlexaFluor 750',
                     'DAPI' : 'DAPI',
                     'Cy5'  : 'Cy5'}

class Parser:
    """Machine-readable data structure containing SMLM acquisition information.
    
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
    datasetType : str
        The type of data contained in the dataset. Can be one of 'locResults',
        'locMetadata', or 'widefieldImage'.
       
    """
    def __init__(self, acqID, channelID, posID, prefix, datasetType):
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
        datasetType : str
            The type of data contained in the dataset. Can be one of
            'locResults', 'locMetadata', or 'widefieldImage'.
        
        """
        if datasetType not in ['locResults','locMetadata','widefieldImage']:
            raise DatasetError(datasetType)
        
        # These are the essential pieces of information to identify a dataset.
        self.acqID       =       acqID
        self.channelID   =   channelID
        self.posID       =       posID
        self.prefix      =      prefix
        self.datasetType = datasetType
        
    def getBasicInfo(self):
        """Return a dictionary containing the basic dataset information.
        
        """
        basicInfo = {'acquisition_id' :       self.acqID,
                     'channel_id'     :   self.channelID,
                     'position_id'    :       self.posID,
                     'prefix'         :      self.prefix,
                     'dataset_type'   : self.datasetType}
                     
        return basicInfo

class MMParser(Parser):
    """Parses a Micro-Manger-based filename for the dataset's acquisition info.
    
    """
    def __init__(self):
        # Overload the parent's __init__ to prevent automatically calling it.
        pass
    
    def parseFilename(self, filename, datasetType = 'locResults'):
        """Parse the filename to extract the acquisition information.
        
        Parameters
        ----------
        filename    : str or Path
            A string or pathlib Path object containing the dataset's filename.
        datasetType : str
            One of 'locResults', 'locMetadata', or 'widefieldImage'.
            
        Returns
        -------
        self        : MMParser
            The parsed acquisition information.
            
        """
        if datasetType not in ['locResults','locMetadata','widefieldImage']:
            raise DatasetError(datasetType)        
        
        # Convert Path objects to strings
        if isinstance(filename, pathlib.PurePath):
            filename = str(filename.name)
            
        if datasetType == 'locResults':
            parsedData = self._parseLocResults(filename)
            super(MMParser, self).__init__(*parsedData, datasetType)
        
    def _parseLocResults(self, filename):
        """Parse a localization results file.
        
        Parameters
        ----------
        filename : str
            The filename for the current file to parse.
        
        """
        # Split the string at 'MMStack'
        prefixRaw, suffixRaw = filename.split('_MMStack_')
        
        # Obtain the acquisition ID
        prefixRawParts = prefixRaw.split('_')
        acqID          = int(prefixRawParts[-1])
        
        # Obtain the channel ID and prefix
        # Extract any channel identifiers if present. See channelIdentifer dict
        prefix    = '_'.join(prefixRawParts[:-1])
        channelID = [channel for channel in channelIdentifier.keys() if channel in prefix]
        assert (len(channelID) <= 1), channelID
        try:
            channelID = channelID[0]
            prefix = prefix.replace('_' + channelID, '')
        except IndexError:
            # When there is no channel identifier found, set it to None
            channelID = None
        
        # Obtain the position ID using regular expressions
        # First, extract strings like 'Pos0' or 'Pos_003_002
        positionRaw = re.search(r'Pos\_\d{1,3}\_\d{1,3}|Pos\d{1,}', suffixRaw)
        # Next, extract the digits and convert them to a tuple
        indexes = re.findall(r'\d{1,}', positionRaw.group(0))
        posID   = tuple([int(index) for index in indexes])
        
        return  acqID, channelID, posID, prefix

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
        
"""PROTOTYPE
self.MM_Channels
self.MM_ChColors
self.MM_ChContrastMax
self.MM_ChContrastMin
self.MM_ChNames
self.MM_Comment
self.MM_ComputerName
self.MM_Date
self.MM_Depth
self.MM_Directory
self.MM_Frames
self.MM_GridColumn
self.MM_GridRow
self.MM_Height
self.MM_IJType
self.MM_Interval
self.MM_KeepShutterOpenChannels
self.MM_KeepShutterOpenSlices
self.MM_MetadataVersion
self.MM_PixelAspect
self.MM_PixelSize_um
self.MM_PixelType
self.MM_PositionIndex
self.MM_Positions
self.MM_Prefix
self.MM_Slices
self.MM_SlicesFirst
self.MM_Source
self.MM_Time
self.MM_TimeFirst
self.MM_UserName
self.MM_UUID
self.MM_Width
self.MM_z-step_um
"""