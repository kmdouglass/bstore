class sm-clusters:
    """Class for analysis and recording of single-molecule clustering data.
    
    sm-clusters contains data types and functions that allow for easy
    generation, analysis, and recording of clustered data from single-molecule
    localization microscopy experiments. Its two main data types are a Pandas
    data frame (containing the numerical data) and a JSON object containing the
    relevant metadata for an experiment.
    
    ...
    
    Attributes
    ----------
    cData : Pandas DataFrame
        Contains statistics and location information on all clusters
    mData : JSON (TODO)
        JSON data type with relevant experimental and processing parameters

    """
    def __init__(self,
                 folder = None,
                 algorithm = 'DBSCAN',
                 options = {k: 8, eps: 65}):
        """Find the localization data and perform the clustering algorithm.
        
        Parameters
        ----------
        folder    : str (default: None)
            The folder containing the localization data files
        algorithm : str (default: 'DBSCAN')
            The clustering algorithm run on the data
        options   : dict (default: {k: 8, eps: 65})
            The input parameters used by the clustering algorithm. If the
            values of the dict are lists of values, then the clustering routine
            is run for each set of values in corresponding positions in the
            lists.
        """
        pass
    
    def parseFolder(self):
        """Finds all localization data files in a directory
        
        Returns
        -------
        dataFiles : list of str
            A list of all the localization data files in a directory
        """
        pass
    
    def doClustering(self):
        """Run the clustering algorithm on the localization data
        
        """