from pathlib import Path
from sklearn.cluster import DBSCAN
import pandas as pd
import trackpy as tp
import numpy as np
from operator import *
from scipy.signal      import gaussian
from scipy.ndimage     import filters
from scipy.interpolate import UnivariateSpline

class Cluster:
    """Clusters the localizations into spatial clusters.
    
    """
    def __init__(self, minSamples = 50, eps = 20, coordCols = ['x', 'y', 'z']):
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
        
class FiducialDriftCorrect:
    """Correct localizations for lateral drift using fiducials.
    
    The fiducial drift correction processor implements an algorithm for
    automatic fiducial detection and uses these localizations to correct the
    other localization positions in the dataset.
    
    Attributes
    ----------
    fiducialTrajectories : list of Pandas dataframe
    splines              : dict of UnivariateSpline, int, int POSSIBLY CHANGE DATATYPE AFTER IMPLEMENTATION
    avgSpline            : dict of UnivariateSpline, int, int
    
    """
    def __init__(self,
                 mergeRadius           = 90,
                 offTime               = 3,
                 minSegmentLength      = 30,
                 minFracFiducialLength = 0.75,
                 neighborRadius        = 100,
                 fracWindowSize        = 1./10,
                 fracFilterSize        = 1./25,
                 linker                = tp.link_df):
        """Set parameters for automatic fiducial detection and spline fitting.
        
        Parameters
        ----------
        mergeRadius           : float
            Maximum distance between successive localizations during merging.
        offTime               : int
            The number of frames for which a localization may disappear and
            still be merged with others within the mergeRadius.
        minSegmentLength      : int
            The minimum number of frames grouped segments must span to be
            considered a fiducial candidate.
        minFracFiducialLength : float
            The minimum fraction of the total number of frames a track must
            span to be a fiducial. Must lie between 0 and 1.
        neighborRadius        : float
            The neighborhood radius for DBSCAN when grouping localizations from
            candidate segments.
        fracWindowSize        : float
            Moving average window size as a fraction of the total fiducial
            track length.
        fracFilterSize        : float
            Moving average Gaussian kernel width as a fraction of the total
            fiducial track length
        linker                : function
            Specifies what linker function to use. The choices are tp.link_df
            for when the entire data frame is stored in memory and
            tp.link_df_iter for when streaming from an HDF5 file.
            
        """
        self.mergeRadius           = mergeRadius
        self.offTime               = offTime
        self.minSegmentLength      = minSegmentLength
        self.minFracFiducialLength = minFracFiducialLength
        self.neighborRadius        = neighborRadius
        self.fracWindowSize        = fracWindowSize
        self.fracFilterSize        = fracFilterSize
        self.linker                = linker
        self.fiducialTrajectories  = []        
        
        # Dict object holds the splines and their range
        self.splines   = {'xS'       : [],
                          'yS'       : [],
                          'minFrame' : [],
                          'maxFrame' : []}
                   
        self.avgSpline = {'xS'       : [],
                          'yS'       : [],
                          'minFrame' : [],
                          'maxFrame' : []}
        
    def __call__(self, df):
        """Automatically find fiducial localizations and do drift correction.
        
        ADD DOCS
        
        Parameters
        ----------
        df : DataFrame
            A Pandas DataFrame object.
            
        Returns
        -------
        procdf : DataFrame
            A DataFrame object with the same information but new column names.
        
        """
        # Reset the fiducial trajectories and find the fiducials
        self.fiducialTrajectories = []        
        self._detectFiducials(df.copy())
        
        # Check whether fiducial trajectories are empty
        if not self.fiducialTrajectories:
            return df
        
        # Perform spline fits on fiducial tracks
        self._fitSplines()
        
        # Average the splines together        
        self._combineSplines()
        
        # Correct the localizations with the average spline fit
        procdf = df
        
        return procdf
        
    def _combineSplines(self):
        """Average the splines from different fiducials together.
        
        """
        
        # Build list of evaluated splines between the absolute max and 
        # min frames. Assign NaNs to points where splines are evaluated outside
        # their range, which is denoted as 0.
        
        # Shift spline with earliest frame to (x = 0, y = 0) at that frame
        
        # Shift other splines to the value of the first spline evaluated at
        # their earliest frame
        
        # Compute the average over spline values, ignorning NaN's using isnan
        pass
        
    def _detectFiducials(self, df):
        """Automatically detect fiducials.
        
        Parameters
        ----------
        df : Pandas dataframe
        
        """
        # Rename 'x [nm]' and 'y [nm]' to 'x' and 'y' if necessary
        # This allows ThunderSTORM format to be used as well as the LEB format
        if ('x [nm]' in df.columns) and ('y [nm]' in df.columns):
            procdf      = df.rename(columns = {'x [nm]' : 'x', 'y [nm]' : 'y'})
            renamedCols = True
        else:
            procdf      = df
            renamedCols = False

        # Merge localizations        
        mergedLocs = self.linker(procdf,
                                 self.mergeRadius,
                                 memory = self.offTime)
        
        # Compute track lengths and remove tracks shorter than minSegmentLength
        # Clear mergedLocs from memory when done
        mergedFilteredLocs = tp.filter_stubs(mergedLocs, self.minSegmentLength)
        del(mergedLocs)
        
        # Cluster remaining localizations
        maxFrame = mergedFilteredLocs['frame'].max() - \
                   mergedFilteredLocs['frame'].min()
        db = DBSCAN(eps = self.neighborRadius,
                    min_samples = maxFrame * self.minFracFiducialLength)
        db.fit(mergedFilteredLocs[['x', 'y']])
        
        # Check whether any fiducials were identified. If not, return the input
        # dataframe and exit function.
        numFiducials = len(np.unique(db.labels_)) - 1
        try:
            if numFiducials < 1:
                raise ZeroFiducialsFound(numFiducials)
        except ZeroFiducialsFound as excp:
            print(
            '{0} fiducials found. Returning original dataframe.'.format(excp))
            return df
        
        # Extract localizations as a list of dataframes for each fiducial
        # (-1 denotes unclustered localizations)
        fiducials = [mergedFilteredLocs[db.labels_ == label]
                         for label in np.unique(db.labels_) if label != -1]
        
        # Remove localizations belonging to the same frame
        for fiducialDF in fiducials:
            fiducialDF.drop_duplicates(subset  = 'frame',
                                       keep    = False,
                                       inplace = True)
                                       
        # Save fiducial trajectories to the class's fiducialTrajectories field
        self.fiducialTrajectories = [fids[['x', 'y', 'frame']]
                                         for fids in fiducials]

    def _fitSplines(self):
        """Fit splines to the fiducial trajectories.
        
        """ 
        for fid in self.fiducialTrajectories:
            maxFrame        = fid['frame'].max()
            minFrame        = fid['frame'].min()
            approxNumFrames = maxFrame - minFrame
            windowSize      = approxNumFrames / self.fracWindowSize
            sigma           = approxNumFrames / self.fracFilterSize
            
            # Determine the appropriate weighting factors
            _, varx = self._movingAverage(fid['x'],
                                          windowSize = windowSize,
                                          sigma      = sigma)
            _, vary = self._movingAverage(fid['y'],
                                          windowSize = windowSize,
                                          sigma      = sigma)
            
            # Perform spline fits. ext=1 means spline return 0 if
            # extrapolating outside the fit range.
            xSpline = UnivariateSpline(fid['frame'].as_matrix(),
                                       fid['x'].as_matrix(),
                                       w   = 1/np.sqrt(varx),
                                       ext = 1)
            ySpline = UnivariateSpline(fid['frame'].as_matrix(),
                                       fid['y'].as_matrix(),
                                       w   = 1/np.sqrt(vary),
                                       ext = 1)
                                       
            # Append results to class field splines
            self.splines['xS'].append(xSpline)
            self.splines['yS'].append(ySpline)
            self.splines['minFrame'].append(minFrame)
            self.splines['maxFrame'].append(maxFrame)
            
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
            The variance of the data within the moving window.
        
        References
        ----------
        http://www.nehalemlabs.net/prototype/blog/2014/04/12/how-to-fix-scipys-interpolating-spline-default-behavior/
        
        """
        b       = gaussian(windowSize, sigma)
        average = filters.convolve1d(series, b/b.sum())
        var     = filters.convolve1d(np.power(series-average,2), b/b.sum())
        return average, var
    
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
    
    def __init__(self, columnName, operator, filterParameter):
        """Define the data column and filter operation to perform.
        
        Parameters
        ----------
        columnName      : str
        operator        : str
            A string matching an operator defined in the _operatorMap dict.
            Examples include '+', '<=' and '>'.
        filterParameter : float
        
        """
        try:
            self._operator    = self._operatorMap[operator]
        except KeyError:
            print('Error: {:s} is not a recognized operator.'.format(operator))
            raise KeyError
        
        self._columnName      = columnName
        self._filterParameter = filterParameter
    
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
        # The index must be reset for some processors to work.
        procdf = df[self._operator(df[self._columnName],
                                   self._filterParameter)].reset_index(drop = True)
                                      
        return procdf

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
        
class Merge:
    """Merges nearby localizations in subsequent frames into one localization.
    
    """
    def __init__(self,
                 autoFindMergeRadius = True,
                 tOff                = 1,
                 mergeRadius         = 50,
                 precisionColumn     = 'precision'):
        """Set or calculate the merge radius and set the off time.
        
        The merge radius is the distance around a localization that another
        localization must be in space for the two to become merged. The off
        time is the maximum number of frames that a localization can be absent
        from before the its track in time is terminated.
        
        Parameters
        ----------
        autoFindMergeRadius : bool (default: True)
            If True, this will set the merge radius to three times the mean
            localization precision in the dataset.
        tOff                : int
            The off time for grouping molecules into one. Units are frames.
        mergeRadius         : float (default: 50)
            The maximum distance between localizations in space for them to be
            considered as one. Units are the same as x, y, and z. This is
            ignored if autoFindMergeRadius is True.
        precisionColumn     : str (default: 'precision')
            The name of the column containing the localization precision. This
            is ignored if autoFindMergeRadius is False.
        """
        self._autoFindMergeRadius = autoFindMergeRadius
        self._tOff                = tOff
        self._mergeRadius         = mergeRadius
        self._precisionColumn      = precisionColumn
    
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
        dfTracked = tp.link_df(df, mergeRadius, self._tOff)
        
        # Group the localizations by particle track ID
        particleGroups = dfTracked.groupby('particle')
        
        # Compute the statistics for each group of localizations
        tempResultsX           = particleGroups.apply(self._wAvg, 'x')
        tempResultsY           = particleGroups.apply(self._wAvg, 'y')
        tempResultsZ           = particleGroups.apply(self._wAvg, 'z')
        tempResultsMisc        = particleGroups.agg({'loglikelihood' : 'mean',
                                                     'frame'         : 'min',
                                                     'photons'       : 'sum',
                                                     'bg'            : 'sum'})
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
        
    def _wAvg(self, group, coordinate):
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
        
        Returns
        -------
        wAvg : float
            The weighted average over the grouped data in 'coordinate',
            weighted by the square root of values in the 'photons' column.
        """
        positions = group[coordinate]
        photons   = group['photons']
        
        wAvg = (positions * photons.apply(np.sqrt)).sum() \
               / photons.apply(np.sqrt).sum()
               
        return wAvg
        
class ZeroFiducialsFound(Exception):
    """Exception raised when zero fiducials are found during drift correction.
    
    """
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)
        
if __name__ == '__main__':
    example = 'fiducialDriftCorrect'

    # Set the directory to the data file and load it into a DataFrame
    from pathlib import Path
    p  = Path('../test-data/pSuper_1/pSuper_1_locResults.dat')
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
        