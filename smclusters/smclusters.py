import numpy as np
from pathlib import Path
from sklearn.cluster import DBSCAN

"""TODOS
1. Routine to detect and generate the cluster data folder
2. Save cluster labels to separate folder
3. Compute cluster statistics and save to folder
"""

class smclusters:
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
                 folder = '.',
                 algorithm = 'DBSCAN',
                 options = {'min_samples': 50, 'eps': 20},
                 usecols = (0,1)):
        """Find the localization data and perform the clustering algorithm.
        
        Parameters
        ----------
        folder    : str  (optional, default: '.')
            The folder containing the localization data directories. Defaults
            to the current Python interpretor working directory.
        algorithm : str  (optional, default: 'DBSCAN')
            The clustering algorithm run on the data
        options   : dict (optional, default: {min_samples: 8, eps: 65})
            The input parameters used by the clustering algorithm. If the
            values of the dict are lists of values, then the clustering routine
            is run for each set of values in corresponding positions in the
            lists.
        usecols   : tuple of int (options, default: (0,1))
            The columns in the localization data files to use for clustering.
            Typically, these are the x-, y-, and possibly z-coordinates.
        """
        self._usecols   = usecols
        self._folder    = Path(folder)
        self._algorithm = algorithm
        self._options   = options
        self._locResultFiles = self._parseFolder()
        
        self.cData = None
        self.mData = None

                
    def _parseFolder(self, fileSuffix = '.dat'):
        """Finds all localization data files in a directory tree.
        
        Parameters
        ----------
        fileSuffix      : str (optional, default: '.dat')
            Suffix for localization result files. This must be unique to
            files containing localization data.
        
        Returns
        -------
        locResultFiles  : list of Path
            A list of all the localization data files in a directory tree
        """
        locResultFilesGen = self._folder.glob('**/*{:s}'.format(fileSuffix))
        locResultFiles    = sorted(locResultFilesGen)
        
        return locResultFiles

    def fit(self):
        """Run the clustering algorithm on the localization data
        
        fit runs the specified clustering algorithm on all localization
        datasets in the given directory tree. Statistics for each cluster are
        then computed after each clustering.
        """
        
        # Unpack the clustering algorithm parameters
        if self._algorithm is 'DBSCAN':
            cluster     = DBSCAN().fit
            min_samples = self._options['min_samples']
            eps         = self._options['eps']
        
        for currFile in self._locResultFiles:
            print('Currently processing {:s}...'.format(currFile.parts[-2]))            
            
            filePath = str(currFile.resolve())
            
            # Import the localization data into a NumPy array
            currData = np.loadtxt(filePath, delimiter = ',', skiprows = 1, usecols = self._usecols)
            
            # Perform clustering on the localization data
            db = cluster(currData)
            
            # Extract the cluster labels corresponding to each localization
            clusterLabels = db.labels_
            
            # Save the labels to a csv file
            savePath = str(currFile.parent) + '/clusterLabels.csv'
            np.savetxt(savePath, clusterLabels, delimiter = ',', fmt = '%i')
            
    def computeClusterStats(self):
        """Computes the statistics of each cluster.
        """
        pass
        
    def saveData(self):
        """Saves the cluster- and meta-data to the disk.
        
        """
        pass