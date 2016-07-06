import pandas            as pd
import trackpy           as tp
import numpy             as np
import matplotlib.pyplot as plt
import re
from abc                import ABCMeta, abstractmethod, abstractproperty
from pathlib            import Path
from sklearn.cluster    import DBSCAN
from operator           import *
from scipy.signal       import gaussian
from scipy.ndimage      import filters
from scipy.interpolate  import UnivariateSpline
from matplotlib.widgets import RectangleSelector
from bstore             import config
from bstore.parsers     import FormatMap
import warnings

"""Metaclasses
-------------------------------------------------------------------------------
"""
class DriftCorrect(metaclass = ABCMeta):
    """Basic functionality for a drift correction processor.
    
    """
    @abstractproperty
    def driftTrajectory(self):
        """A list of x,y pairs with each possessing a unique frame number.
        
        """
        pass
    
    @abstractproperty
    def correctorType(self):
        """Identifies the type of drift corrector for a specific class.
        
        """
        pass
    
    @abstractmethod
    def correctLocalizations(self):
        """Corrects a DataFrame of localizations for drift.
        
        """
        pass
    
    @abstractmethod
    def readSettings(self):
        """Sets the state of the drift corrector.
        
        """
        pass
    
    @abstractmethod
    def writeSettings(self):
        """Writes the state of the drift corrector to a file.
        
        """
        pass

class ComputeTrajectories(metaclass = ABCMeta):
    """Basic functionality for computing drift trajectories from fiducials.
    
    """
    def __init__(self):
        """Initializes the trajectory computer.
        
        """
        self._fiducialData = None
        
    def clearFiducialLocs(self):
        """Clears any currently held localization data.
        
        """
        self._fiducialData = None
    
    @property
    def fiducialLocs(self):
        """DataFrame holding the localizations for individual fiducials.
        
        """
        return self._fiducialData
    
    @fiducialLocs.setter
    def fiducialLocs(self, fiducialData):
        """Checks that the fiducial localizations are formatted correctly.
        
        """
        assert 'region_id' in fiducialData.index.names, \
                      'fiducialLocs DataFrame requires index named "region_id"'
        
        self._fiducialData = fiducialData
        
    @abstractmethod
    def computeDriftTrajectory(self):
        """Computes the drift trajectory.
        
        """
        pass  
    
class MergeStats(metaclass = ABCMeta):
    """Basic functionality for computing statistics from merged localizations.
    
    """
    @abstractmethod
    def computeStatistics(self):
        """Computes the merged molecule statistics.
        
        """
        pass
    
    def _wAvg(self, group, coordinate, photonsCol = 'photons'):
        """Perform a photon-weighted average over positions.
        
        This helper function computes the average of all numbers in the
        'coordinate' column when applied to a Pandas GroupBy object.
        
        Parameters
        ----------
        group : Pandas GroupBy
            The merged localizations.
        coordinate : str
            Column label for the coordinate over which to compute the weighted
            average for a particular group.
        photonsCol : str
            Column label for the photons column.
        
        Returns
        -------
        wAvg : float
            The weighted average over the grouped data in 'coordinate',
            weighted by the square root of values in the 'photons' column.
        """
        positions = group[coordinate]
        photons   = group[photonsCol]
        
        wAvg = (positions * photons.apply(np.sqrt)).sum() \
               / photons.apply(np.sqrt).sum()
               
        return wAvg


"""
Concrete classes
-------------------------------------------------------------------------------
"""
class AddColumn:
    """Adds a column to a DataFrame.
    
    AddColumn adds a column to a DataFrame and initializes every row to the
    same value.
    
    """
    def __init__(self, columnName, defaultValue = True):
        self.columnName   = columnName
        self.defaultValue = defaultValue
    
    def __call__(self, df):
        """Clean up the data.
        
        Parameters
        ----------
        df : DataFrame
            A Pandas DataFrame object.
            
        Returns
        -------
        procdf : DataFrame
            A DataFrame object with a new column.
        
        """
        procdf = df.copy()
        del(df)
        
        numRows, _              = procdf.shape
        procdf[self.columnName] = pd.Series([self.defaultValue]*numRows,
                                             index = procdf.index)
        
        return procdf

class CleanUp:
    """Performs regular clean up routines on imported data.
    
    The cleanup processor encapsulates a few common steps that are performed on
    imported datasets. Currently, these steps are:
    
    1) Convert rows containing strings to numeric data types
    2) Drop rows containing strings that cannot be parsed to numeric types
    3) Drop rows with Inf's and NaN's
    
    """
    def __call__(self, df):
        """Clean up the data.
        
        Parameters
        ----------
        df : DataFrame
            A Pandas DataFrame object.
            
        Returns
        -------
        procdf : DataFrame
            A DataFrame object with the same information but new column names.
        
        """
        procdf = df.copy()
        del(df)

        for column in procdf:        
            # 'coerce' means anything unable to be parsed becomes a NaN
            procdf[column] = pd.to_numeric(procdf[column], errors = 'coerce')
            
        procdf.replace([np.inf, -np.inf], np.nan, inplace = True)
        procdf.dropna(inplace = True)
        
        # DO NOT USE procdf.reindex() because it will not
        # automatically reorder an index correctly. It is
        # used for other purposes.
        procdf.index = np.arange(procdf.shape[0])
        
        return procdf

class Cluster:
    """Clusters the localizations into spatial clusters.
    
    """
    def __init__(self, minSamples = 50, eps = 20, coordCols = ['x', 'y']):
        """Set the DBSCAN parameters and list the columns in the data denoting
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
        clusterLabels = pd.Series(db.labels_, name = 'cluster_id')
        
        # Append the labels to the DataFrame
        procdf = pd.concat([df, clusterLabels], axis = 1)
        
        return procdf

class ComputeClusterStats:
    """Computes statistics for clusters of localizations.
    
    """
    
    # The name to append to the center coordinate column names
    centerName = '_center'
    
    def __init__(self, idLabel    = 'cluster_id',
                 coordCols        = ['x', 'y'],
                 statsFunctions   = None):
        """Set the column name for the cluster ID numbers.
        
        Parameters
        ----------
        idLabel          : str
            The column name containing cluster ID's.
        coordCols        : list of string
            A list containing the column names containing the localization
            coordinates.
        statsFunctions   : dict of name/function pairs
            A dictionary containing column names and functions for computing
            custom statistics from the clustered localizations. The keys in
            dictionary determine the name of the customized column and the
            value contains a function that computes a number from the
            coordinates of the localizations in each cluster.
        
        """
        self._idLabel   = idLabel
        self._statsFunctions = {'radius_of_gyration' : self._radiusOfGyration,
                                'eccentricity'       : self._eccentricity,
                                'convex_hull'        : self._convexHull}
                                
        self.coordCols = coordCols
        
        # Add the input functions to the defaults if they were supplied
        if statsFunctions:                      
            for name, func in statsFunctions.items():
                self._statsFunctions[name] = func
    
    def __call__(self, df):
        """Compute the statistics for each cluster of localizations.
        
        This function takes a DataFrame, groups the data by the column idLabel,
        then computes the cluster statistics for each cluster. A new DataFrame
        for the statistics are returned.
        
        Parameters
        ----------
        df : DataFrame
            A Pandas DataFrame object.
            
        Returns
        -------
        procdf : DataFrame
            A DataFrame object containing cluster statistics.
        
        """  
        # Group localizations by their ID
        groups = df.groupby(self._idLabel)
        
        # Computes the default statistics for each cluster
        tempResultsCoM    = groups[self.coordCols].agg(np.mean)
        tempResultsLength = pd.Series(groups.size())
        
        # Compute the custom statistics for each cluster and set
        # the column name to the dictionary key
        tempResultsCustom = []
        for name, func in self._statsFunctions.items():        
            temp      = groups.apply(func, self.coordCols)
            temp.name = name # The name of the column is now the dictionary key
            tempResultsCustom.append(temp)

        # Appends '_center' to the names of the coordinate columns
        # and renames the series
        newCoordCols = [col + self.centerName for col in self.coordCols]
        nameMapping  = dict(zip(self.coordCols, newCoordCols))
        
        tempResultsCoM.rename(columns = nameMapping,
                              inplace = True)
        tempResultsLength.name = 'number_of_localizations'
        
        # Create the merged DataFrame
        dataToJoin = [tempResultsCoM,
                      tempResultsLength]
        dataToJoin = dataToJoin + tempResultsCustom
                      
        procdf = pd.concat(dataToJoin, axis = 1)
        
        # Convert the cluster_id index to a column
        procdf.reset_index(level = ['cluster_id'], inplace = True)
                                                     
        return procdf
    
    def _radiusOfGyration(self, group, coordinates):
        """Computes the radius of gyration of a grouped cluster.
        
        Parameters
        ----------
        group : Pandas GroupBy
            The clustered localizations.   
            
        Returns
        -------
        Rg    : float
            The radius of gyration of the group of localizations.
        
        """
        variances = group[coordinates].var(ddof = 0)
        
        # sqrt(3/2) makes the radius of gyration comparable to a 3D cluster        
        Rg = np.sqrt(variances.sum())
        return Rg
        
        
    def _eccentricity(self, group, coordinates):
        """ Computes the eccentricity of a grouped cluster.
        
        Parameters
        ----------
        group : Pandas GroupBy
            The clustered localizations.   
            
        Returns
        -------
        ecc   : float
            The eccentricity of the group of localizations.
        """
        # Compute the covariance matrix  and its eigevalues
        Mcov = np.cov(group[coordinates].as_matrix(),
                      rowvar = 0,
                      bias   = 1)
                      
        eigs = np.linalg.eigvals(Mcov)
        
        ecc = np.max(eigs) / min(eigs)
        return ecc
        
    def _convexHull(self, group, coordinates):
        """Computes the volume of the cluster's complex hull.
        
        Parameters
        ----------
        group : Pandas GroupBy
            The clustered localizations. 
        
        Returns
        -------
        volume : float or np.nan
        
        """
        # Compute CHull only if pyhull is installed
        # pyhull is only available in Linux
        try:        
            from pyhull import qconvex
        except ImportError:
            print (('Warning: pyhull is not installed. ' 
                    'Cannot compute convex hull. Returning NaN instead.'))
            return np.nan
        
        points = group[coordinates].as_matrix()
        output = qconvex('FA', points)
    
        # Find output volume
        try:
            volume = [vol for vol in output if 'Total volume:' in vol][0]
            volume = float(re.findall(r'[-+]?[0-9]*\.?[0-9]+', volume)[0])
        except:
            volume = np.nan
            
        return volume

class ConvertHeader:
    """Converts the column names in a localization file to a different format.
    
    Attributes
    ----------
    mapping      : FormatMap
    
    """
    def __init__(self, mapping = FormatMap(config.__Format_Default__)):
        """Determines whether the file is a single file or a directory tree.
        
        Parameters
        ----------
        mapping : FormatMap
            A dict-like object for converting between column names in
            different data formats.
       
        """        
        self.mapping = mapping
        
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
        
class DefaultDriftComputer(ComputeTrajectories):
    """The default algorithm for computing a drift trajectory.
    
    Attributes
    ----------
    avgSpline           : Pandas DataFrame
        DataFrame with 'frame' index column and 'xS' and 'yS' position
        coordinate columns representing the drift of the sample during the
        acquisition.
    fiducialData        : Pandas DataFrame
        DataFrame with a 'region_id' column denoting localizations from
        different regions of the original dataset. This is created by the
        parent ComputeTrajectories class.
    smoothingWindowSize : float
        Moving average window size in frames for spline fitting.
    smoothingFilterSize : float
        Moving average Gaussian kernel width in frames for spline fitting.
    splines             : list of dict of 2x UnivariateSpline, 2x int
        Individual splines fit to the fiducial trajectories. Key names are
        'xS', 'yS', 'minFrame', and 'maxFrame'.
    useTrajectories : list of int or None
        List of integers corresponding to the fiducial trajectories to use
        when computing the average trajectory. If None, all trajectories
        are used.
    zeroFrame       : int
        Frame where all individual drift trajectories are equal to zero.
        This may be adjusted to help correct fiducial trajectories that
        don't overlap well near the beginning.
        
    """
    # TODO: Explain this algorithm in the docstring above.
    
    def __init__(self, coordCols = ['x', 'y'], frameCol = 'frame',
                 smoothingWindowSize = 600, smoothingFilterSize = 400,
                 useTrajectories = [], zeroFrame = 0):
        """Initialize the default drift computer.
        
        Parameters
        ----------
        coordCols           : list str
            List of strings identifying the x- and y-coordinate column names
            in that order.
        frameCol            : str
            Name of the column identifying the column containing the frames.
        smoothingWindowSize   : float
            Moving average window size in frames for spline fitting.
        smoothingFilterSize   : float
            Moving average Gaussian kernel width in frames for spline fitting.
        useTrajectories : list of int
            List of integers corresponding to the fiducial trajectories to use
            when computing the average trajectory. If empty, all trajectories
            are used.
        zeroFrame       : int
            Frame where all individual drift trajectories are equal to zero.
            This may be adjusted to help correct fiducial trajectories that
            don't overlap well near the beginning.
        """
        self.coordCols = coordCols
        self.frameCol  = frameCol
        self.smoothingWindowSize = smoothingWindowSize
        self.smoothingFilterSize = smoothingFilterSize
        self.useTrajectories     = useTrajectories
        self.zeroFrame           = zeroFrame
        super(ComputeTrajectories, self).__init__()
        
    def _movingAverage(self, series, windowSize = 100, sigma = 3):
        """Estimate the weights for the smoothing spline.
        
        Parameters
        ----------
        series     : array of int
            Discrete samples from a time series.
        windowSize : int
            Size of the moving average window in frames (or time).
        sigma      : int
            Size of the Gaussian averaging kernel in frames (or time).
            
        Returns
        -------
        average : float
            The moving window average.
        var     : float
            The variance of the data within the sumoving window.
        
        References
        ----------
        http://www.nehalemlabs.net/prototype/blog/2014/04/12/how-to-fix-scipys-interpolating-spline-default-behavior/
        
        """
        b       = gaussian(windowSize, sigma)
        average = filters.convolve1d(series, b/b.sum())
        var     = filters.convolve1d(np.power(series-average,2), b/b.sum())
        return average, var
        
    def combineCurves(self, startFrame, stopFrame):
        """Average the splines from different fiducials together.
        
        combineSplines(self, framesdf) relies on the assumption that fiducial
        trajectories span a significant portion of the full number of frames in
        the acquisition. Under this assumption, it uses the splines found in
        fitSplines() to extrapolate values outside of their tracks using the
        boundary value. It next evaluates the splines at each frame spanning
        the input DataFrame, shifts the evaluated splines to zero at the first
        frame, and then computes the average across different fiducials.
        
        Parameters
        ----------
        startFrame : int
            Minimum frame number in full dataset
        stopFrame  : int
            Maximum frame number in full dataset
            
        """
        
        # Build list of evaluated splines between the absolute max and 
        # min frames.
        if self.zeroFrame > stopFrame:
            warnings.warn(('Warning: zeroFrame ({0:d}) is greater than the '
                           'maximum frame number in this dataset ({1:d})'
                           'Setting zeroFrame to zero.'
                           ''.format(self.zeroFrame, stopFrame)))
            self.zeroFrame = 0
                           
        frames     = np.arange(startFrame, stopFrame + 1, 1)
        numSplines = len(self.splines)
        
        # Evalute each x and y spline at every frame position
        fullRangeSplines = {'xS' : np.array([self.splines[i]['xS'](frames)
                                                 for i in range(numSplines)]),
                            'yS' : np.array([self.splines[i]['yS'](frames)
                                                 for i in range(numSplines)])}
        
        # Shift each spline at zeroFrame to (x = 0, y = 0) by subtracting its
        # value at frame number zeroFrame
        for key in fullRangeSplines.keys():
            for ctr, spline in enumerate(fullRangeSplines[key]):
                firstFrameValue = spline[self.zeroFrame]
                fullRangeSplines[key][ctr] = fullRangeSplines[key][ctr] - \
                                                                firstFrameValue  
        
        # Create the mask area if only certain fiducials are to be averaged
        if not self.useTrajectories:
            mask = np.arange(numSplines)
        else:
            mask = self.useTrajectories        
        
        # Compute the average over spline values
        avgSpline = {'xS' : [], 'yS' : []}
        
        try:
            for key in avgSpline.keys():
                avgSpline[key] = np.mean(fullRangeSplines[key][mask], axis = 0)
        except IndexError:
            raise UseTrajectoryError('At least one of the indexes inside '
                             'useTrajectories does not match a known fiducial '
                             'index. The maximum fiducial index is {0:d}.'
                             ''.format(numSplines - 1))
        
        # Append frames to avgSpline
        avgSpline['frame'] = frames
        
        self.avgSpline = pd.DataFrame(avgSpline)
        self.avgSpline.set_index('frame', inplace = True)
        
    def computeDriftTrajectory(self, fiducialLocs, startFrame, stopFrame):
        """Computes the final drift trajectory from fiducial localizations.
        
        Parameters
        ----------
        fiducialLocs    : Pandas DataFrame
            DataFrame containing the localizations belonging to fiducials.
        startFrame      : int
            The minimum frame number in the full dataset.
        stopFrame       : int
            The maximum frame number in the full dataset.
            
        Returns
        -------
        self.avgSpline : Pandas DataFrame
            DataFrame with 'frame' index column and 'xS' and 'yS' position
            coordinate columns representing the drift of the sample during the
            acquisition.
            
        Notes
        -----
        computeDriftTrajectory() requires the start and stop frames
        because the fiducial localizations may not span the full range
        of frames in the dataset.
        
        """
        self.clearFiducialLocs()
        self.fiducialLocs = fiducialLocs       
        self.fitCurves()
        self.combineCurves(startFrame, stopFrame)

        return self.avgSpline
        
    def fitCurves(self):
        """Fits individual splines to each fiducial.
               
        """
        print('Performing spline fits...')
        # Check whether fiducial trajectories already exist
        if self.fiducialLocs is None:
            raise ZeroFiducials('Zero fiducials are currently saved '
                                'with this processor.')
            
        self.splines = []
        regionIDIndex = self.fiducialLocs.index.names.index('region_id')
        x = self.coordCols[0]
        y = self.coordCols[1]        
        frameID = self.frameCol
        
        # fid is an integer
        for fid in self.fiducialLocs.index.levels[regionIDIndex]:
            # Get localizations from inside the current region matching fid
            currRegionLocs  = self.fiducialLocs.xs(fid, level='region_id',
                                                    drop_level=False)            
            
            maxFrame        = currRegionLocs[frameID].max()
            minFrame        = currRegionLocs[frameID].min()
            
            windowSize      = self.smoothingWindowSize
            sigma           = self.smoothingFilterSize
            
            # Determine the appropriate weighting factors
            _, varx = self._movingAverage(currRegionLocs[x],
                                          windowSize = windowSize,
                                          sigma      = sigma)
            _, vary = self._movingAverage(currRegionLocs[y],
                                          windowSize = windowSize,
                                          sigma      = sigma)
            
            # Perform spline fits. Extrapolate using boundary values (const)
            extrapMethod = 'const'
            xSpline = UnivariateSpline(currRegionLocs[frameID].as_matrix(),
                                       currRegionLocs[x].as_matrix(),
                                       w   = 1/np.sqrt(varx),
                                       ext = extrapMethod)
            ySpline = UnivariateSpline(currRegionLocs[frameID].as_matrix(),
                                       currRegionLocs[y].as_matrix(),
                                       w   = 1/np.sqrt(vary),
                                       ext = extrapMethod)
            
            # Append results to class field splines
            self.splines.append({'xS'       : xSpline,
                                 'yS'       : ySpline,
                                 'minFrame' : minFrame,
                                 'maxFrame' : maxFrame})
                                 
    def plotFiducials(self, splineNumber = None):
        """Make a plot of each fiducial track and the average spline fit.
        
        plotFiducials(splineNumber = None) allows the user to check the
        individual fiducial tracks against the average spline fit.
                
        Parameters
        ----------
        splineNumber : int
            Index of the spline to plot. (0-index)
        
        """
        if self.fiducialLocs is None:
            raise ZeroFiducials(
                'Zero fiducials are currently saved with this processor.')
        
        x = self.coordCols[0]
        y = self.coordCols[1]        
        
        if splineNumber is None:
            # Plot all trajectories and splines
            startIndex = 0
            stopIndex  = len(self.splines)
        else:
            # Plot only the input trajectory and spline
            startIndex = splineNumber
            stopIndex  = splineNumber + 1
        
        
        for fid in range(startIndex, stopIndex):
            fig, (axx, axy) = plt.subplots(nrows = 2, ncols = 1, sharex = True)
            locs = self.fiducialLocs.xs(fid, level = 'region_id',
                                         drop_level = False)
            
            # Shift fiducial trajectories to zero at their start
            frame0 = locs['frame'].iloc[[self.zeroFrame]].as_matrix()
            x0 = self.splines[fid]['xS'](frame0)
            y0 = self.splines[fid]['yS'](frame0)            
            
            if (fid in self.useTrajectories) or (not self.useTrajectories):
                markerColor = 'blue'
            else:
                markerColor = '#999999' # gray
            
            axx.plot(locs['frame'],
                     locs[x] - x0,
                     '.',
                     color = markerColor,
                     alpha = 0.5)
            axx.plot(self.avgSpline.index,
                     self.avgSpline['xS'],
                     linewidth = 3,
                     color = 'red')
            axx.set_ylabel('x-position')
            axx.set_title('Avg. spline and fiducial number: {0:d}'.format(fid))
                     
            axy.plot(locs['frame'],
                     locs[y] - y0,
                     '.',
                     color = markerColor,
                     alpha = 0.5)
            axy.plot(self.avgSpline.index,
                     self.avgSpline['yS'],
                     linewidth = 3,
                     color = 'red')
            axy.set_xlabel('Frame number')
            axy.set_ylabel('y-position')
            plt.show()
        
class FiducialDriftCorrect(DriftCorrect):
    """Correct localizations for lateral drift using fiducials.
    
    """
    _correctorType = 'FiducialDriftCorrect'    
    
    def __init__(self, interactiveSearch = True, coordCols = ['x', 'y'],
                 frameCol = 'frame', removeFiducials = True,
                 driftComputer = None):
        """Initialize the processor.
        
        Parameters
        ----------
        interactiveSearch : bool
            Determines whether the user will interactively find fiducials.
            Setting this to False means that fiducials are found automatically,
            although this is not always reliable.
        coordCols         : list str
            List of strings identifying the x- and y-coordinate column names
            in that order.
        frameCol          : str
            Name of the column identifying the column containing the frames.
        removeFiducials   : bool
            Determines whether localizations belonging to fiducials are
            dropped from the input DataFrame when the processor is called.
            This is ignored if interactiveSearch is False.
        driftComputer     : instance of ComputeTrajectories
            Function for computing the drift trajectory from fiducial
            localizations. If 'None', the default function utilizing
            smoothing splines is used.
        
        """
        # Assign class properties based on input arguments
        self.interactiveSearch = interactiveSearch
        self._coordCols        = coordCols
        self._frameCol         = frameCol
        self._removeFiducials  = removeFiducials
        
        if driftComputer:        
            self.driftComputer = driftComputer
        else:
            self.driftComputer = DefaultDriftComputer(coordCols = coordCols,
                                                      frameCol = frameCol)
        
        # Setup the class fields
        self._fidRegions = [{'xMin' : None,
                             'xMax' : None,
                             'yMin' : None,
                             'yMax' : None}]
    
    def __call__(self, df):
        """Find the localizations and perform the drift correction.
        
        Parameters
        ----------
        df : DataFrame
            A Pandas DataFrame object.
            
        Returns
        -------
        procdf : DataFrame
            A DataFrame object with drift-corrected x- and y-coordinates.
        
        """
        if self.interactiveSearch:        
            self.doInteractiveSearch(df)
        
            # Extract the localizations inside the regions just identified
            try:
                fiducialLocs = self._extractLocsFromRegions(df)
            except ZeroFiducialRegions:
                print('No regions with fiducials identified. '
                      'Returning original DataFrame.')
                # Ensure any localizations are cleared from the drift computer
                self.driftComputer.clearFiducialLocs()
                return df
        else:
            # If the interactive search was set to false, then the drift
            # corrector has already been called and the regions saved in the
            # drift computer. Read them back from the computer instead of 
            # looking for them again in the raw localizations.
            fiducialLocs = self.driftComputer.fiducialLocs
        
        # Cluster here localizations if desired
        
        # Remove localizations inside the search regions from the DataFrame
        if self._removeFiducials:
            # Removes rows from the df DataFrame that have the same index rows
            # in fiducialLocs. This relies on all functions preceding this
            # line to not modify the index column of the input df.
            procdf = df[~df.index.isin(fiducialLocs.index.levels[0])]
        
        # Compute the final drift trajectory
        frames     = self._frameCol
        startFrame = procdf[frames].min()
        stopFrame  = procdf[frames].max()
        self.driftTrajectory = \
            self.driftComputer.computeDriftTrajectory(fiducialLocs,
                                                      startFrame,
                                                      stopFrame)
        
        procdf = self.correctLocalizations(procdf)
        
        return procdf
            
    def _extractLocsFromRegions(self, df):
        """Reduce the size of the search area for automatic fiducial detection.
        
        Parameters
        ----------
        df           : Pandas DataFrame
            DataFrame that will be spatially filtered.
        
        Returns
        -------
        locsInRegions : Pandas DataFrame
            DataFrame containing localizations only within the select regions.
        
        """
        # If search regions are not defined, raise an error
        if not self._fidRegions[0]['xMin']:
            raise ZeroFiducialRegions('Error: Identified no fiducial regions.')
        
        locsInRegions = []
        numRegions    = len(self._fidRegions)
        for regionNumber in range(numRegions):
            xMin = self._fidRegions[regionNumber]['xMin']
            xMax = self._fidRegions[regionNumber]['xMax']
            yMin = self._fidRegions[regionNumber]['yMin']
            yMax = self._fidRegions[regionNumber]['yMax']
        
            # Isolate the localizations within the current region
            locsInCurrRegion = df[(df[self._coordCols[0]] > xMin) &
                                  (df[self._coordCols[0]] < xMax) &
                                  (df[self._coordCols[1]] > yMin) &
                                  (df[self._coordCols[1]] < yMax)].copy()
                                  
            # Add a multi-index identifying the region number
            locsInCurrRegion['region_id'] = regionNumber
            locsInCurrRegion.set_index(['region_id'], append = True,
                                       inplace = True)
            
            locsInRegions.append(locsInCurrRegion)
        
        return pd.concat(locsInRegions)
    
    @property
    def driftTrajectory(self):
        return self._driftTrajectory
    
    @driftTrajectory.setter
    def driftTrajectory(self, value):
        """Sets the computed the drift trajectory of the processor.
        
        Parameters
        ----------
        value : Pandas DataFrame
            A DataFrame with x, y, and frame columns and unique, sequential
            values for entries in the frame column defining a drift
            trajectory.
        """
        self._driftTrajectory = value
        
    @property
    def correctorType(self):
        return self._correctorType
        
    def correctLocalizations(self, df):
        """Correct the localizations using the spline fits to fiducial tracks.
        
        WARNING: To keep memory usage efficient, the input DataFrame is deleted
        immediately after it's copied.
        
        Parameters
        ----------
        df     : Pandas DataFrame
            The input DataFrame for processing.
            
        Returns
        -------
        corrdf : Pandas DataFrame
            The corrected DataFrame.
        
        """
        corrdf = df.copy()
        del(df)        
        
        x = self._coordCols[0]
        y = self._coordCols[1]        
        
        xc = self.driftComputer.avgSpline.lookup(corrdf.frame,
                                                 ['xS'] * corrdf.frame.size)
        yc = self.driftComputer.avgSpline.lookup(corrdf.frame,
                                                 ['yS'] * corrdf.frame.size)
        
        corrdf['dx'] = xc
        corrdf['dy'] = yc
        corrdf[x]  = corrdf[x] - xc
        corrdf[y]  = corrdf[y] - yc
        
        return corrdf
    
    def doInteractiveSearch(self, df, gridSize = 100, unitConvFactor = 1./1000,
                          unitLabel = 'microns'):
        """Interactively find fiducials in the histogram images.
        
        Allows the user to select regions in which to search for fiducials.
        
        Parameters
        ----------
        df             : Pandas DataFrame
            Data to visualize and search for fiducials.
        gridSize       : float
            The size of the hexagonal grid in the 2D histogram.
        unitConvFactor : float
            Conversion factor for plotting the 2D histogram in different units
            than the data. Most commonly used to convert nanometers to microns.
            In this case, there are unitConvFactor = 1/1000 nm/micron.
        unitLabel      : str
            Unit label for the histogram. This is only used for labeling the
            axes of the 2D histogram; users may change this depending on the
            units of their data and unitConvFactor.
            
        """
        # Reset the fiducial regions
        self._fidRegions = [{'xMin' : None, 'xMax' : None,
                             'yMin' : None, 'yMax' : None}]     
        
        def onClose(event):
            """Run when the figure closes.
            
            """
            fig.canvas.stop_event_loop()
            
        def onSelect(eclick, erelease):
            pass
        
        def toggleSelector(event, processor):
            """Handles user input.
            
            """
            if event.key in [' ']:
                # Clear fiducial regions list if they are not empty
                #(Important for when multiple search regions are selected.)
                if not self._fidRegions[0]['xMin']:                
                    # Convert _fidRegions to empty list ready for appending
                    self._fidRegions = []
                
                xMin, xMax, yMin, yMax = toggleSelector.RS.extents
                processor._fidRegions.append({'xMin' : xMin/unitConvFactor,
                                              'xMax' : xMax/unitConvFactor,
                                              'yMin' : yMin/unitConvFactor,
                                              'yMax' : yMax/unitConvFactor})
    
        fig, ax = plt.subplots()
        fig.canvas.mpl_connect('close_event', onClose)        
        
        im      = ax.hexbin(df[self._coordCols[0]] * unitConvFactor,
                            df[self._coordCols[1]] * unitConvFactor,
                            gridsize = gridSize, cmap = plt.cm.YlOrRd_r)
        ax.set_xlabel(r'x-position, ' + unitLabel)
        ax.set_ylabel(r'y-position, ' + unitLabel)
        ax.invert_yaxis()
    
        cb = plt.colorbar(im)
        cb.set_label('Counts')

        toggleSelector.RS = RectangleSelector(ax,
                                              onSelect,
                                              drawtype    = 'box',
                                              useblit     = True,
                                              button      = [1, 3], #l/r only
                                              spancoords  = 'data',
                                              interactive = True)
        plt.connect('key_press_event',
                    lambda event: toggleSelector(event, self))
        
        # Make figure full screen
        figManager = plt.get_current_fig_manager()
        figManager.window.showMaximized()
        plt.show()
        
        # Suppress the MatplotlibDeprecationWarning
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            fig.canvas.start_event_loop_default()
    
    def readSettings(self):
        pass
    
    def writeSettings(self):
        pass
            
class Filter:
    """Processor for filtering DataFrames containing localizations.
    
    A filter processor works by selecting a dolumn of the input DataFrame and
    creating a logical mask by applying the operator and parameter to each
    value in the column. Rows that correspond to a value for 'False' in the
    mask are removed from the DataFrame.
    
    """   
    
    _operatorMap = {'<'  : lt,
                    '<=' : le,
                    '==' : eq,
                    '!=' : ne,
                    '>=' : ge,
                    '>'  : gt}    
    
    def __init__(self, columnName, operator, filterParameter, resetIndex = True):
        """Define the data column and filter operation to perform.
        
        Parameters
        ----------
        columnName      : str
        operator        : str
            A string matching an operator defined in the _operatorMap dict.
            Examples include '+', '<=' and '>'.
        filterParameter : float
        resetIndex      : bool
            Should the returned index be reset?
        
        """
        try:
            self._operator    = self._operatorMap[operator]
        except KeyError:
            print('Error: {:s} is not a recognized operator.'.format(operator))
            raise KeyError
        
        self._columnName      = columnName
        self._filterParameter = filterParameter
        self._resetIndex      = resetIndex
    
    def __call__(self, df):
        """Filter out rows of the DataFrame.
        
        When this class is called, it filters out rows from the DataFrame by
        removing rows containing values in 'columnName' that do not satisfy the
        filter predicate.
        
        Parameters
        ----------
        df : DataFrame
            A Pandas DataFrame object.
            
        Returns
        -------
        procdf : DataFrame
            A filtered DataFrame.
        
        """
        if self._resetIndex:
            # The index must be reset for some processors to work.
            procdf = df[self._operator(df[self._columnName],
                        self._filterParameter)].reset_index(drop = True)
        else:
            procdf = df[self._operator(df[self._columnName],
                        self._filterParameter)]
                                      
        return procdf
        
class Merge:
    """Merges nearby localizations in subsequent frames into one localization.
    
    """
    def __init__(self,
                 tOff                = 1,
                 mergeRadius         = 50,
                 autoFindMergeRadius = False,
                 statsComputer       = None,
                 precisionColumn     = 'precision'):
        """Set or calculate the merge radius and set the off time.
        
        The merge radius is the distance around a localization that another
        localization must be in space for the two to become merged. The off
        time is the maximum number of frames that a localization can be absent
        from before the its track in time is terminated.
        
        Parameters
        ----------
        autoFindMergeRadius : bool (default: False)
            If True, this will set the merge radius to three times the mean
            localization precision in the dataset.
        tOff                : int
            The maximum time that a localization can vanish. Units are frames.
        mergeRadius         : float (default: 50)
            The maximum distance between localizations in space for them to be
            considered as one. Units are the same as x, y, and z. This is
            ignored if autoFindMergeRadius is True.
        statsComputer       : MergeStats
            Instance of a concrete MergeStats class for computing the
            merged localization statistics. statsComputer is None by default,
            which means that only particle ID's will be appended to the
            DataFrame and merged statistics will not be calculated. This
            allows handling of custom DataFrame columns and statistics.
        precisionColumn     : str (default: 'precision')
            The name of the column containing the localization precision. This
            is ignored if autoFindMergeRadius is False.
        """
        self._autoFindMergeRadius = autoFindMergeRadius
        self._tOff                = tOff
        self._mergeRadius         = mergeRadius
        self._statsComputer       = statsComputer
        self._precisionColumn     = precisionColumn
    
    def __call__(self, df):
        """Merge nearby localizations into one.
        
        When this class is called, it searches for localizations that are close
        to one another in space and in time. These localizations are merged
        into one and new information about their columns is updated.
        
        Parameters
        ----------
        df : DataFrame
            A Pandas DataFrame object.
            
        Returns
        -------
        procdf : DataFrame
            A DataFrame object with the merged localizations.
        
        """
        if self._autoFindMergeRadius:
            mergeRadius = 3 * df[self._precisionColumn].mean()
        else:
            mergeRadius = self._mergeRadius
        
        # Track individual localization trajectories
        dfTracked = tp.link_df(df, mergeRadius, memory = self._tOff)
        
        # Compute the statistics for each group of localizations
        if self._statsComputer:
            # Return a DataFrame containing merged statistics
            procdf = self._statsComputer.computeStatistics(dfTracked)
        else:
            # Return the original DataFrame with a new particle id column
            procdf = dfTracked
        
        return procdf
        
class MergeFang(MergeStats):
    """Merger for localizations computed from Fang's sCMOS MLE software.
    
    """
    def computeStatistics(self, df, particleCol = 'particle'):
        """Calculates the statistics of the linked trajectories.
        
        Parameters
        ----------
        df          : Pandas DataFrame
            DataFrame containing linked localizations.
        particleCol : str
            The name of column containing the merged partice ID's.
            
        Returns
        -------
        procdf : Pandas DataFrame
            DataFrame containing the fully merged localizations.
            
        """
        particleGroups         = df.groupby(particleCol)        
        
        tempResultsX           = particleGroups.apply(self._wAvg, 'x')
        tempResultsY           = particleGroups.apply(self._wAvg, 'y')
        tempResultsZ           = particleGroups.apply(self._wAvg, 'z')
        tempResultsMisc        = particleGroups.agg({'loglikelihood' : 'mean',
                                                     'frame'         : 'min',
                                                     'photons'       : 'sum',
                                                     'background'    : 'sum',
                                                     'sigma'         : 'mean'})
        tempResultsLength      = pd.Series(particleGroups.size())
    
        # Rename the series
        tempResultsX.name      = 'x'
        tempResultsY.name      = 'y'
        tempResultsZ.name      = 'z'
        tempResultsLength.name = 'length'
        
        # Create the merged DataFrame
        dataToJoin = (tempResultsX,
                      tempResultsY,
                      tempResultsZ,
                      tempResultsMisc,
                      tempResultsLength)
        procdf = pd.concat(dataToJoin, axis = 1)
        
        return procdf
        
"""Errors
-------------------------------------------------------------------------------
"""

class UseTrajectoryError(Exception):
    """Raised when drift computer has invalid indexes to fiducial trajectories.
    
    """
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)
        
class ZeroFiducials(Exception):
    """Raised when zero fiducials are present during drift correction.
    
    """
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)
        
class ZeroFiducialRegions(Exception):
    """Raised when zero fiducials are present during drift correction.
    
    """
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)
        
if __name__ == '__main__':
    example = 'merge'

    # Set the directory to the data file and load it into a DataFrame
    from pathlib import Path
    p  = Path('../test-data/Telomeres/pSuper_1/pSuper_1_locResults.dat')
    df = pd.read_csv(str(p))
    
    if example == 'convert':
        # Define the input and output formats for the localization file
        inputFormat  = FormatThunderSTORM()
        outputFormat = FormatLEB()
        converter    = ConvertHeader(inputFormat, outputFormat)
        
        # Convert the file into a new format
        convertedDF  = converter(df)
    
    elif example == 'cluster':        
        # Set the DBSCAN parameters and the columns for clustering
        minSamples = 50
        eps        = 20
        coordCols  = ['x [nm]', 'y [nm]']
        
        # Initialize the processor
        clusterMaker = Cluster(minSamples, eps, coordCols)
        
        # Perform the clustering and return a DataFrame as a result
        clusteredDF  = clusterMaker(df)
        
    elif example == 'fiducialDriftCorrect':
        # Load data with fiducials present
        fileName = Path('../test-data/acTub_COT_gain100_30ms/acTub_COT_gain100_30ms.csv')
        with open(str(fileName), 'r') as file:
            df = pd.read_csv(file)
            
        # Reduce number of columns (for debugging)
        #newdf = df[df['frame'] < 2000].copy()
        
        mergeRadius      = 90 # same units as x, y (typically nm)
        offTime          = 3  # units of frames
        minSegmentLength = 30 # units of frames
        
        # Initialize the drift corrector
        corrector = FiducialDriftCorrect(mergeRadius      = mergeRadius,
                                         offTime          = offTime,
                                         minSegmentLength = minSegmentLength)
                                         
        # Perform drift correction
        correctedDF = corrector(df)
        
    elif example == 'filter':
       # Initialize the filter
        myFilter = Filter('loglikelihood', '<', 250)
        
        # Filter the data by keeping rows with loglikelihood less than or equal
        # to 250
        filteredDF = myFilter(df)
        
    elif example == 'merge':
        # Convert test-data headers
        # (this is not neccessary if data is already in the LEB format)       
        inputFormat  = FormatThunderSTORM()
        outputFormat = FormatLEB()
        converter    = ConvertHeader(inputFormat, outputFormat)
        cdf          = converter(df)       
        
        # Intial filtering on the data
        cdf = cdf[cdf['loglikelihood'] <= 250]
        cdf = cdf[cdf['loglikelihood'] >= 0]
        cdf = cdf[(cdf['x'] >= 0) & (df['y'] >= 0)]
        
        # Set the off time for the data merging in units of frames
        tOff = 1
        
        # Initialize the processor
        merger = Merge(tOff = tOff)
        
        # Perform the merging
        mergedDF = merger(cdf)
        
        mergedDF.to_csv('temp.csv',sep = ',', index = False)
        