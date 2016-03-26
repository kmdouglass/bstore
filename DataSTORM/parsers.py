class Parser:
    """Machine-readable data structure containing SMLM acquisition information.
    
    Attributes
    ----------
    acqID       : int
        The number identifying the Multi-D acquisition for a given prefix name.
    channelID   : str
        The color channel associated with the dataset.
    posID       : int, or (int, int)
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
        
        """
        # These are the essential pieces of information to identify a dataset.
        self.acqID       =       acqID
        self.channelID   =   channelID
        self.posID       =       posID
        self.prefix      =      prefix
        self.datasetType = datasetType
        
    def getBasicInfo(self):
        """Return a dictionary containing the basic dataset information.
        
        """
        

class MMFileParser(Parser):
    """Parses a filename to extract the dataset's acquisition information.
    
    """
    def __init__(self):
        """Initialize the Micro-Manager metadata.
        
        """
        """self.MM_Channels
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

class HDFParser(Parser):
    """Parses HDF groups and datasets to extract their acquisition information.
    
    """
    pass