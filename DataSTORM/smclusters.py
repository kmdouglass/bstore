import numpy as np
from pathlib import Path
import os.path
from sklearn.cluster import DBSCAN
import pandas as pd

"""NOTES
You can choose to either just create the cluster labels, or make the labels and
compute the cluster statistics (in case labels were already generated).


TODO Save cluster statistics to folder
TODO Overlay clusters on widefield images
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
                 fileSuffix = '.dat',
                 delimiter  = ',',
                 algorithm = 'DBSCAN',
                 options = {'min_samples': 50, 'eps': 20},
                 usecols = (0,1)):
        """Find the localization data contained in the supplied directory tree.
        
        Parameters
        ----------
        folder     : str  (optional, default: '.')
            The folder containing the localization data directories. Defaults
            to the current Python interpretor working directory.
        fileSuffix : str  (optional, default: '.dat')
            The file type of the files containing the localization data.
        delimiter  : str  (optional, default: ',')
            The delimiter used in the localization files.
        algorithm  : str  (optional, default: 'DBSCAN')
            The clustering algorithm run on the data
        options    : dict (optional, default: {min_samples: 50, eps: 20})
            The input parameters used by the clustering algorithm. If the
            values of the dict are lists of values, then the clustering routine
            is run for each set of values in corresponding positions in the
            lists.
        usecols    : tuple of int (options, default: (0,1))
            The columns in the localization data files to use for clustering.
            Typically, these are the x-, y-, and possibly z-coordinates.
        """
        assert (len(usecols) == 2 or len(usecols) == 3), \
        'usecols must be a tuple with a length of 2 (2D data) or 3 (3D data).'
        
        
        
        if len(usecols) == 2:
            print('''Two columns detected for input data. 
                     Assuming data is two dimensional.''')
            self._numColsIs3 = False
        elif len(self._usecols) == 3:
            print('''Three columns detected for input data.
                     Assuming data is three dimensional.''')
            self._numColsIs3 = True        
        
        self._fileSuffix = fileSuffix
        self._delimiter  = delimiter
        self._usecols    = usecols
        self._folder     = Path(folder)
        self._algorithm  = algorithm
        self._options    = options
        self._locResultFiles = self._parseFolder(fileSuffix = self._fileSuffix)
        
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

    def fit(self, computeStats = True):
        """Run the clustering algorithm on the localization data
        
        fit runs the specified clustering algorithm on all localization
        datasets in the given directory tree. Statistics for each cluster are
        then computed after each clustering.
        
        Parameters
        ----------
        computeStats : bool (optional, default: True)
            Determines whether the statistics for each cluster should be
            caluclated after clustering.
        """
        
        # Unpack the clustering algorithm parameters
        if self._algorithm is 'DBSCAN':
            cluster     = DBSCAN(min_samples = self._options['min_samples'],
                                 eps         = self._options['eps']).fit
        
        for currFile in self._locResultFiles:
            print('Currently processing {:s}/{:s}...'.format(currFile.parts[-2], currFile.parts[-1]))            
            
            filePath = str(currFile.resolve())
            
            # Import the localization data into a NumPy array
            currData = np.loadtxt(filePath,
                                  delimiter = self._delimiter,
                                  skiprows  = 1,
                                  usecols   = self._usecols)          
            
            # Perform clustering on the localization data
            db = cluster(currData)
            
            # Extract the cluster labels corresponding to each localization
            clusterLabels = db.labels_
            
            # Save the labels to a csv file
            savePath = os.path.join(str(currFile.parent),
                                    str(currFile.stem) + '_clusterLabels.csv')
            np.savetxt(savePath,
                       clusterLabels,
                       delimiter = ',',
                       fmt = '%i')
                       
            # Compute the statistics for each cluster
            if computeStats: self._computeClusterStats(currData,
                                                       clusterLabels,
                                                       currFile)
            
    def _computeClusterStats(self, data, labels, p):
        """Computes the statistics of each cluster.
        
        computeClusterStats accepts an array containing localization data and
        another single-column array with the same number of rows containing
        the cluster labels. The statistics for every cluster are calculated and
        saved to the disk.
        
        Parameters
        ----------
        currData      : array of float
            [numLocalizations numProperties] sized array, where properties
            usually refers to the localizations' x- and y- (and possibly z-)
            positions.
        clusterLabels : array of int
            Cluster labels for each localization 
        currFile      : Path
            pathlib Path object to the file containing the localization data
        """
        
        # Noise is given its own label of -1, so remove it
        uniqueLabels = np.unique(labels)
        uniqueLabels = uniqueLabels[uniqueLabels != -1]
        numLabels    = uniqueLabels.size
        
        currFolder = str(p.parent)
        currFile   = str(p.stem)
        
        # Pre-allocate arrays
        # M1 and M2 are the first and second moments; Rg is the radius of gyration
        stats = {'M1x': np.zeros(numLabels),     'M1y': np.zeros(numLabels),
                 'M2x': np.zeros(numLabels),     'M2y': np.zeros(numLabels),
                 'numLocs': np.zeros(numLabels), 'Rg2D': np.zeros(numLabels)}
        
        if self._numColsIs3:
            stats['M1z']  = np.zeros(numLabels)
            stats['M2z']  = np.zeros(numLabels)
            stats['Rg3D'] = np.zeros(numLabels)
        
        # Compute stats for this cluster
        for ctr, labelCtr in enumerate(uniqueLabels):
            # Slice the data for localizations belonging to current cluster
            cluster = data[labels == labelCtr, :]
            
            # Compute statistics
            currM1 = np.mean(cluster, axis = 0)
            currM2 = np.var(cluster,  axis = 0)

            # Assign values to the temporary holding arrays                        
            stats['M1x'][ctr]     = currM1[0]; stats['M1y'][ctr] = currM1[1]
            stats['M2x'][ctr]     = currM2[0]; stats['M2y'][ctr] = currM2[1]
            stats['numLocs'][ctr] = cluster.shape[0]
            stats['Rg2D'][ctr]    =  np.sqrt(currM2[0] + currM2[1])          

            if self._numColsIs3:
                stats['M1z'][ctr] = currM1[2]; stats['M2z'][ctr] = currM2[2]
                stats['Rg3D']     = np.sqrt(currM2[0] + currM2[1] + currM2[3])
        
        stats['Folder'] = [currFolder] * numLabels
        stats['File']   = [currFile]   * numLabels     
        
        # Write data to a Pandas dataframe
        if self.cData is None:
            self.cData = pd.DataFrame(stats)
        else:
            self.cData = pd.concat([self.cData, pd.DataFrame(stats)])
        
    def saveData(self):
        """Saves the cluster- and meta-data to the disk.
        
        """
        pass