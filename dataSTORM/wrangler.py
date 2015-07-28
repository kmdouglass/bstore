import pandas as pd
from pathlib import Path

class ConvertHeader:
    """Converts the column names in a localization file to a different format.
    
    Attributes
    ----------
    overwrite : bool (default: False)
        Flag for whether a separate file with the new headers will be created
        or the headers will be simply overwritten.
    
    """
    def __init__(self, file, fileFormat, overwrite = False, suffix = '.dat'):
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
        self.overwrite  = overwrite        
        self.fileFormat = fileFormat
        self.file       = Path(file)
        
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
        
        """
        
        
        for file in self._fileList:
            locData = pd.read_csv(str(file),
                                  sep     = self.fileFormat.delimiter,
                                  comment = self.fileFormat.comment)
        
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
        ts2leb[',']                  = '\t'
        self.ts2leb                  = ts2leb

class FormatThunderSTORM(FormatSTORM):
    """Definition for the ThunderSTORM localization file format.
    
    """
    delimiter = ','
    comment   = None

class FormatLEB(FormatSTORM):
    """Definition for the ThunderSTORM localization file format.
    
    """
    delimiter = '\t'
    comment   = '#'
        
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

    outputFormat = FormatLEB()
    converter    = ConvertHeader(p, outputFormat)
    
    converter.convert()