from pathlib import Path
from sklearn.cluster import DBSCAN
import pandas as pd

class Cluster:
    """Clusters the localizations into spatial clusters.
    
    """
    def __init__(self, minSamples = 50, eps = 20, coordCols = ['x', 'y', 'z']):
        """Set the DBSCAN parameters and list the columns in the data denotig
        the localizations' spatial coordinates.
        
        Parameters
        ----------
        minSamples : int
            Minimum number of samples within one neighborhood radius.
        eps        : float
            The neighborhood radius defining a cluster.
        coordCols  : list of str
            The columns of the data to be clustered.
        """
        self._minSamples = minSamples
        self._eps        = eps
        self._coordCols  = coordCols
    
    def __call__(self, df):
        """Group the localizations into spatial clusters.
        
        When this class is called, it performs density-based spatial clustering
        on the positional coordinates of each localization. Cluster labels are
        added as an additional column to the DataFrame.
        
        Parameters
        ----------
        df : DataFrame
            A Pandas DataFrame object.
            
        Returns
        -------
        procdf : DataFrame
            A DataFrame object with the same information but new column names.
        
        """
        columnsToCluster = self._coordCols
        
        # Setup and perform the clustering
        db = DBSCAN(min_samples = self._minSamples, eps = self._eps)
        db.fit(df[columnsToCluster])
        
        # Get the cluster labels and make it a Pandas Series
        clusterLabels = pd.Series(db.labels_, name = 'cluster id')
        
        # Append the labels to the DataFrame
        procdf = pd.concat([df, clusterLabels], axis = 1)
        
        return procdf

class ConvertHeader:
    """Converts the column names in a localization file to a different format.
    
    Attributes
    ----------
    inputFormat  : FormatSTORM
    outputFormat : FormatSTORM
    mapping      : FormatMap
    
    """
    def __init__(self, inputFormat, outputFormat):
        """Determines whether the file is a single file or a directory tree.
        
        Parameters
        ----------
        inputFormat  : FormatSTORM  (default: 'FormatThunderSTORM')
            Identifier for the input header format.
        outputFormat : FormatSTORM  (default: 'FormatLEB')
            Identifier for the output header format.
       
        """        
        self.outputFormat = outputFormat
        self.mapping      = self._parseMapping(inputFormat, outputFormat)
        
    def __call__(self, df):
        """Convert the files to the new header format.
        
        When this class is called, it maps the column names from the input
        format to the output format. Formats are defined independently of this
        class.
        
        Parameters
        ----------
        df : DataFrame
            A Pandas DataFrame object.
            
        Returns
        -------
        procdf : DataFrame
            A DataFrame object with the same information but new column names.
        
        """
        procdf = df        
        
        # Change the column names
        colNames = [self.mapping[oldName] for oldName in df.columns]
        procdf.columns = colNames
            
        return procdf
        
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
        
        Notes
        -----
        Any new mapping defined here must have a string identifier comprised of
        either permutation of the identifiers for the two Formats that form the
        mapping. For example, FormatThunderSTORM has the identifier 'TS' and
        FormatLEB has 'LEB'. The identifier for their mapping is 'TSLEB'.
        
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
    example = 'cluster'    
    
    if example == 'convert':
        from pathlib import Path
        
        p  = Path('../test-data/pSuper_1/pSuper_1_locResults.dat')
        df = pd.read_csv(str(p))
    
        inputFormat  = FormatThunderSTORM()
        outputFormat = FormatLEB()
        converter    = ConvertHeader(inputFormat, outputFormat)
        
        convertedDF  = converter(df)
    
    elif example == 'cluster':
        from pathlib import Path
        
        p  = Path('../test-data/pSuper_1/pSuper_1_locResults.dat')
        df = pd.read_csv(str(p))
    
        minSamples = 50
        eps        = 20
        coordCols  = ['x [nm]', 'y [nm]']
        
        clusterMaker = Cluster(minSamples, eps, coordCols)
        
        clusteredDF  = clusterMaker(df)