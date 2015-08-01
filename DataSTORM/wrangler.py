import pandas as pd
from pathlib import Path

class Wrangler:
    """Base class for loading and saving single-molecule microscopy data.
    
    Attributes
    ----------
    df       : DataFrame    (default: None)
        Pandas DataFrame object currently in memory.
    fileList : list of Path (default: None)
        List of Path objects pointing to all the identified localization files
        in a directory or a directory tree.    
    
    """
    
    def __init__(self, inputDirectory = None, suffix = '.dat'):
        """Parse the input data.
        
        The Wrangler constructor parses the input directory and creates a list
        of Path objects all pointing to data files.
        
        Parameters
        ----------
        inputDirectory : str or Path
            A string to a directory containg SMLM data files, or a pathlib Path
            instance to a directory.
        suffix         : str (default: '.dat')
            The suffix identifying SMLM data files.
        
        """
        # inputDirectory is not None, add check that there MUST be localization files in the directory        
        
        if inputDirectory is not None:
            self.fileList = self._parseDirectory(str(inputDirectory), suffix)
            # Load first file into DataFrame here       
    
    def _parseDirectory(self, inputDirectory, suffix = '.dat'):
        """Finds all localization data files in a directory or directory tree.
        
        Parameters
        ----------
        inputDirectory : str
            String of the directory tree containing SMLM data files.
        suffix         : str (optional, default: '.dat')
            Suffix for localization result files. This must be unique to
            files containing localization data.
        
        Returns
        -------
        locResultFiles : list of Path
            A list of all the localization data files in a directory tree.
        """
        inputDirectory = Path(inputDirectory)
        locResultFilesGen = inputDirectory.glob('**/*{:s}'.format(suffix))
        locResultFiles    = sorted(locResultFilesGen)
        
        return locResultFiles

class ConvertHeader:
    """Converts the column names in a localization file to a different format.
    
    Attributes
    ----------
    overwrite : bool (default: False)
        Flag for whether a separate file with the new headers will be created
        or the headers will be simply overwritten.
    
    """
    def __init__(self, file, inputFormat, outputFormat, overwrite = False, suffix = '.dat'):
        """Determines whether the file is a single file or a directory tree.
        
        Parameters
        ----------
        file       : Path or str
            A str (or pathlib Path object) to the (relative) path of either a
            single localization file or a directory tree containing
            localization files.
        fileFormat : FormatSTORM  (default: 'FormatLEB')
            Identifier for the new header format.
        overwrite  : bool (default: False)
            Flag for whether a separate file with the new headers will be
            created or the headers will be simply overwritten.
        suffix     : str (default: '.dat')
            The suffix for identifying the input localization files when a
            directory tree is input for the file parameter.
        """        
        self.outputFormat = outputFormat
        self.file         = Path(file)
        self.mapping      = self._parseMapping(inputFormat, outputFormat)
        self.suffix       = suffix
        
        self.overwrite    = overwrite 
        if self.overwrite:
            # Open the existing file and overwrite all data
            self._fileMode    = 'w'
            self._newFormatID = ''
        else:
            # Safeguard to ensure creation of a new file
            self._fileMode    = 'x'
            self._newFormatID = self.outputFormat.identifier
        
        if self.file.is_dir():
            print('Input file is a directory tree. Will search for files.')
            self._fileList = self._parseFolder(suffix)
        elif self.file.is_file():
            print('Input file is a single file. No search will be performed.')
        else:
            err = 'Input file is neither a localization file nor a directory.'
            raise ValueError(err)
            
        
    def convert(self):
        """Convert the files to the new header format.
        
        convert() reads the data into a Pandas DataFrame, maps the column names
        using the input and output formats, then saves a (possibly new) csv
        file in the new format and the same directory.
        
        """
        delimiter = self.outputFormat.delimiter        
        
        for file in self._fileList:
            # Read the localization file into memory
            locData = pd.read_csv(str(file))          
            
            # Change the column names
            colNames = [self.mapping[oldName] for oldName in locData.columns]
            locData.columns = colNames
            
            # Save the data to the new format
            fileName = str(file.parent.resolve() / file.stem) + \
                       self._newFormatID + self.suffix
            
            with open(fileName, self._fileMode) as saveFile:
                locData.to_csv(saveFile, sep = delimiter, header = True)
            
    def _parseFolder(self, suffix = '.dat'):
        """Finds all localization data files in a directory tree.
        
        Parameters
        ----------
        suffix         : str (optional, default: '.dat')
            Suffix for localization result files. This must be unique to
            files containing localization data.
        
        Returns
        -------
        locResultFiles : list of Path
            A list of all the localization data files in a directory tree
        """
        locResultFilesGen = self.file.glob('**/*{:s}'.format(suffix))
        locResultFiles    = sorted(locResultFilesGen)
        
        return locResultFiles
        
    def _parseMapping(self, inputFormat, outputFormat):
        """Determine which mapping between files to use.
        
        _parseMapping will use the identifier field of each FormatSTORM data 
        type to search which mapping between formats to use when changing the
        header names.
        
        Parameters
        ----------
        inputFormat  : FormatSTORM
        outputFormat : FormatSTORM
        
        Returns
        -------
        mapping : FormatMap
            The mapping between column names.
        
        """
        ids = [inputFormat.identifier, outputFormat.identifier]
        
        # Search fields of outputFormat until the correct identifier is found
        fields = outputFormat.__dict__
        
        for checkForID in fields:
            try:
                currentID = getattr(outputFormat, checkForID)
                
                # Correct identifier is any permutation of the two format ID's
                if (ids[0] + ids[1] == currentID['identifier']) \
                or (ids[1] + ids[0] == currentID['identifier']):
                    mapping = currentID
            except TypeError:
                pass
            
        return mapping

class FormatSTORM:
    """A datatype representing localization file formatting.
    
    Attributes
    ----------
    ts2leb : FormatMap
        Mapping between ThunderSTORM and LEB formats.
    """
    def __init__(self):
        """Initialize mappings from one header format to another.
        
        """
        # ThunderSTORM to the LEB format
        ts2leb                       = FormatMap()
        ts2leb['x [nm]']             = 'x'
        ts2leb['y [nm]']             = 'y'
        ts2leb['z [nm]']             = 'z'
        ts2leb['frame']              = 'frame'
        ts2leb['uncertainty [nm]']   = 'precision'
        ts2leb['intensity [photon]'] = 'photons'
        ts2leb['offset [photon]']    = 'bg'
        ts2leb['loglikelihood']      = 'loglikelihood'
        ts2leb['identifier']         = 'TSLEB'
        self.ts2leb                  = ts2leb

class FormatThunderSTORM(FormatSTORM):
    """Definition for the ThunderSTORM localization file format.
    
    """
    delimiter  = ','
    comment    = None
    identifier = 'TS'
    
    def __init__(self):
        FormatSTORM.__init__(self)

class FormatLEB(FormatSTORM):
    """Definition for the ThunderSTORM localization file format.
    
    """
    delimiter  = '\t'
    comment    = '#'
    identifier = 'LEB'
    
    def __init__(self):
        FormatSTORM.__init__(self)
        
class FormatMap(dict):
    """Two-way map for mapping one localization file format to another.
    
    _formatMap subclasses dict and acts like a two-way mapping between
    key-value pairs, unlike dict which provides only a one-way relationship.
    
    References
    ----------
    [1] http://stackoverflow.com/questions/1456373/two-way-reverse-map
    
    """
    def __setitem__(self, key, value):
        if key   in self: del self[key]
        if value in self: del self[value]
        dict.__setitem__(self, key, value)
        dict.__setitem__(self, value, key)
        
    def __delitem__(self, key):
        dict.__delitem__(self, self[key])
        dict.__delitem__(self, key)
        
    def __len__(self):
        return dict.__len__(self) // 2
        
if __name__ == '__main__':
    from pathlib import Path
    
    p = Path('../test-data')    

    inputFormat  = FormatThunderSTORM()
    outputFormat = FormatLEB()
    converter    = ConvertHeader(p, inputFormat, outputFormat)
    
    converter.convert()