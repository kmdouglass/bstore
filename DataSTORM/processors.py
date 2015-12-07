import pandas            as pd
import trackpy           as tp
import numpy             as np
import matplotlib.pyplot as plt

from pathlib            import Path
from sklearn.cluster    import DBSCAN
from operator           import *
from scipy.signal       import gaussian
from scipy.ndimage      import filters
from scipy.interpolate  import UnivariateSpline
from matplotlib.widgets import RectangleSelector

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
        procdf.reindex()
        
        return procdf

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
    fiducialTrajectories : list of Pandas DataFrame
    splines              : list of dict of 2x UnivariateSpline, 2x int
    avgSpline            : Pandas DataFrame
    
    """
    def __init__(self,
                 mergeRadius           = 90,
                 offTime               = 3,
                 minSegmentLength      = 30,
                 minFracFiducialLength = 0.75,
                 neighborRadius        = 100,
                 interactiveSearch     = False,
                 searchRegions         = [{'xMin' : None,
                                           'xMax' : None,
                                           'yMin' : None,
                                           'yMax' : None}],
                 dropFiducials         = True,
                 smoothingWindowSize   = 625,
                 smoothingFilterSize   = 400,
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
            The minimum number of frames segments must span to be considered a
            fiducial candidate.
        minFracFiducialLength : float
            The minimum fraction of the total number of frames a track must
            span to be a fiducial. Must lie between 0 and 1.
        neighborRadius        : float
            The neighborhood radius for DBSCAN when grouping localizations from
            candidate segments.
        interactiveSearch     : bool
            Interactively search for fiducials to reduce the size of the search
            area when the corrector is called.
        searchRegions         : list of dict of float
            Non-overlapping subregions of the data to search for fiducials.
            Dict keys are 'xMin', 'xMax', 'yMin', and 'yMax'.
        dropFiducials         : bool
            Should the fiducial trajectories be dropped from the final dataset?
        smoothingWindowSize   : float
            Moving average window size in frames for spline fitting.
        smoothingFilterSize   : float
            Moving average Gaussian kernel width in frames for spline fitting.
        linker                : function
            Specifies what linker function to use. The choices are tp.link_df
            for when the entire data frame is stored in memory and
            tp.link_df_iter for when streaming from an HDF5 file.
            (NOT IMPLEMENTED)
            
        """
        self.mergeRadius           = mergeRadius
        self.offTime               = offTime
        self.minSegmentLength      = minSegmentLength
        self.minFracFiducialLength = minFracFiducialLength
        self.neighborRadius        = neighborRadius
        self.interactiveSearch     = interactiveSearch
        self.searchRegions         = searchRegions
        self.dropFiducials         = dropFiducials
        self.smoothingWindowSize   = smoothingWindowSize
        self.smoothingFilterSize   = smoothingFilterSize
        self.linker                = linker
        self.fiducialTrajectories  = []        
        
        # Dict object holds the splines and their range
        self.splines   = [{'xS'       : [],
                           'yS'       : [],
                           'minFrame' : [],
                           'maxFrame' : []}]
        
    def __call__(self, df):
        """Automatically find fiducial localizations and do drift correction.
        
        Parameters
        ----------
        df : DataFrame
            A Pandas DataFrame object.
            
        Returns
        -------
        procdf : DataFrame
            A DataFrame object with drift-corrected x- and y-coordinates.
        
        """
        copydf = df.copy()   
        
        # Rename 'x [nm]' and 'y [nm]' to 'x' and 'y' if necessary
        # This allows ThunderSTORM format to be used as well as the LEB format
        if ('x [nm]' in copydf.columns) and ('y [nm]' in copydf.columns):
            copydf.rename(columns = {'x [nm]' : 'x', 'y [nm]' : 'y'},
                          inplace = True)
            renamedCols = True
        else:
            renamedCols = False        
        
        # Visually find areas where fiducials are likely to be present
        if self.interactiveSearch:        
            self.iSearch(copydf)
            
        # Extract subregions to search for fiducials
        fidRegionsdf = self._reduceSearchArea(copydf)
        
        # Reset the fiducial trajectories and find the fiducials
        self.fiducialTrajectories = []        
        self._detectFiducials(fidRegionsdf)
        
        # Check whether fiducial trajectories are empty
        if not self.fiducialTrajectories:
            return df
            
        # Drop the fiducials from the full dataset
        # MUST FIX BUGS
        if self.dropFiducials:
            copydf = self._dropFiducials(copydf)
        
        # Perform spline fits on fiducial tracks
        self._fitSplines()
        
        # Average the splines together        
        self._combineSplines(copydf['frame'])
        
        # Correct the localizations with the average spline fit
        # This will delete copydf and replace it with procdf
        procdf = self._correctLocalizations(copydf)
        
        if renamedCols:
            procdf.rename(columns = {'x'  : 'x [nm]',
                                     'y'  : 'y [nm]',
                                     'dx' : 'dx [nm]',
                                     'dy' : 'dy [nm]'},
                          inplace = True)
            
        return procdf
        
    def _combineSplines(self, framesdf):
        """Average the splines from different fiducials together.
        
        _combineSplines(self, framesdf) relies on the assumption that fiducial
        trajectories span a significant portion of the full number of frames in
        the acquisition. Under this assumption, it uses the splines found in
        _fitSplines() to extrapolate values outside of their tracks using the
        boundary value. It next evaluates the splines at each frame spanning
        the input DataFrame, shifts the evaluated splines to zero at the first
        frame, and then computes the average across different fiducials.
        
        Parameters
        ----------
        framesdf : Pandas Series
            All the frames present in the input data frame
        """
        
        # Build list of evaluated splines between the absolute max and 
        # min frames.
        minFrame   = framesdf.min()
        maxFrame   = framesdf.max()
        frames     = np.arange(minFrame, maxFrame + 1, 1)
        numSplines = len(self.splines)
        
        fullRangeSplines = {'xS' : np.array([self.splines[i]['xS'](frames)
                                                 for i in range(numSplines)]),
                            'yS' : np.array([self.splines[i]['yS'](frames)
                                                 for i in range(numSplines)])}
        
        # Shift each spline to (x = 0, y = 0) by subtracting its first value
        for key in fullRangeSplines.keys():
            for ctr, spline in enumerate(fullRangeSplines[key]):
                firstFrameValue = spline[0]
                fullRangeSplines[key][ctr] = fullRangeSplines[key][ctr] - \
                                                                firstFrameValue  
        
        # Compute the average over spline values
        avgSpline = {'xS' : [], 'yS' : []}
        for key in avgSpline.keys():
            avgSpline[key] = np.mean(fullRangeSplines[key], axis = 0)
        
        # Append frames to avgSpline
        avgSpline['frame'] = frames
        
        self.avgSpline = pd.DataFrame(avgSpline)
        self.avgSpline.set_index('frame', inplace = True)
    
    def _correctLocalizations(self, df):
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
        
        xc = self.avgSpline.lookup(corrdf.frame, ['xS'] * corrdf.frame.size)
        yc = self.avgSpline.lookup(corrdf.frame, ['yS'] * corrdf.frame.size)
        
        corrdf['dx'] = xc
        corrdf['dy'] = yc
        corrdf['x']  = corrdf['x'] - xc
        corrdf['y']  = corrdf['y'] - yc
        
        return corrdf
        
    def _detectFiducials(self, df):
        """Automatically detect fiducials.
        
        The algorithm works by finding long-lived tracks after merging the
        localizations. It then spatially clusters the long-lived tracks and
        keeps clusters with a user-defined number of points, usually equal to
        approximately 1/2 the total number of frames. Finally, it removes
        duplicate localizations found in the same frame.
        
        Parameters
        ----------
        df : Pandas dataframe
        
        """
        
        procdf = df.copy()
        
        # Merge localizations        
        mergedLocs = self.linker(procdf,
                                 self.mergeRadius,
                                 memory = self.offTime)
        
        # Compute track lengths and remove tracks shorter than minSegmentLength
        # Clear mergedLocs and procdf from memory when done for efficiency.
        mergedFilteredLocs = tp.filter_stubs(mergedLocs, self.minSegmentLength)
        del(mergedLocs)
        del(procdf)
        
        # Cluster remaining localizations
        maxFrame = mergedFilteredLocs['frame'].max() - \
                   mergedFilteredLocs['frame'].min()
        db = DBSCAN(eps = self.neighborRadius,
                    min_samples = maxFrame * self.minFracFiducialLength)
        db.fit(mergedFilteredLocs[['x', 'y']])
        
        # Check whether any fiducials were identified. If not, return the input
        # dataframe and exit function.
        nonNoiseLabels = db.labels_[db.labels_ != -1]
        numFiducials   = len(nonNoiseLabels)
        try:
            if numFiducials < 1:
                raise ZeroFiducialsFound(numFiducials)
        except ZeroFiducialsFound as excp:
            print(
            '{0} fiducials found. Returning original dataframe.'.format(excp))
        
        # Extract localizations as a list of dataframes for each fiducial
        # (-1 denotes unclustered localizations)
        # (copy command prevents modifying slice of copy warning)
        fiducials = [mergedFilteredLocs[db.labels_ == label].copy()
                         for label in np.unique(db.labels_) if label != -1]
        
        # Remove localizations belonging to the same frame
        for fiducialDF in fiducials:
            fiducialDF.drop_duplicates(subset  = 'frame',
                                       keep    = False,
                                       inplace = True)
                                       
        # Save fiducial trajectories to the class's fiducialTrajectories field
        self.fiducialTrajectories = fiducials
                                             
        print('{0:d} fiducial(s) detected.'.format(
                                               len(self.fiducialTrajectories)))
    
    def _dropFiducials(self, df):
        """Drop rows belong to fiducial localizations from the dataset.
        
        Parameters
        ----------
        df : Pandas DataFrame
        
        Returns
        -------
        procdf : Pandas DataFrame
        
        """
        procdf = df.copy()
        
        for fid in self.fiducialTrajectories:
            procdf = pd.concat([procdf, fid], ignore_index = True)
            procdf.drop_duplicates(subset = ['x', 'y', 'frame'],
                                   keep = False,
                                   inplace = True)
            
        try:
            del procdf['particle']
        except:
            pass
        
        return procdf       

    def _fitSplines(self):
        """Fit splines to the fiducial trajectories.
        
        """ 
        # Check whether fiducial trajectories already exist
        if not self.fiducialTrajectories:
            return
            
        # Clear current spline fits
        self.splines = []
        
        for fid in self.fiducialTrajectories:
            maxFrame        = fid['frame'].max()
            minFrame        = fid['frame'].min()
            windowSize      = self.smoothingWindowSize
            sigma           = self.smoothingFilterSize
            
            # Determine the appropriate weighting factors
            _, varx = self._movingAverage(fid['x'],
                                          windowSize = windowSize,
                                          sigma      = sigma)
            _, vary = self._movingAverage(fid['y'],
                                          windowSize = windowSize,
                                          sigma      = sigma)
            
            # Perform spline fits. Extrapolate using boundary values (const)
            extrapMethod = 'const'
            xSpline = UnivariateSpline(fid['frame'].as_matrix(),
                                       fid['x'].as_matrix(),
                                       w   = 1/np.sqrt(varx),
                                       ext = extrapMethod)
            ySpline = UnivariateSpline(fid['frame'].as_matrix(),
                                       fid['y'].as_matrix(),
                                       w   = 1/np.sqrt(vary),
                                       ext = extrapMethod)
            
            # Append results to class field splines
            self.splines.append({'xS'       : xSpline,
                                 'yS'       : ySpline,
                                 'minFrame' : minFrame,
                                 'maxFrame' : maxFrame})
    
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
        
    def _reduceSearchArea(self, df):
        """Reduce the size of the search area for automatic fiducial detection.
        
        Parameters
        ----------
        df           : Pandas DataFrame
            DataFrame that will be spatially filtered.
        
        Returns
        -------
        fidRegionsdf : Pandas DataFrame
            DataFrame containing only select regions in which to search for
            fiducials.
        
        """
        # If search regions are not defined, return all localizations to search
        if not self.searchRegions[0]['xMin']:
            return df
        
        fidRegionsdf = []
        numRegions   = len(self.searchRegions)
        for region in range(numRegions):
            xMin = self.searchRegions[region]['xMin']
            xMax = self.searchRegions[region]['xMax']
            yMin = self.searchRegions[region]['yMin']
            yMax = self.searchRegions[region]['yMax']
        
            fidRegionsdf.append(df[(df['x'] > xMin) &
                                   (df['x'] < xMax) &
                                   (df['y'] > yMin) &
                                   (df['y'] < yMax)])
        
        return pd.concat(fidRegionsdf).drop_duplicates()
        
    def iSearch(self,
                df,
                gridSize       = 100,
                unitConvFactor = 1./1000,
                unitLabel      = 'microns'):
        """Interactively find fiducials in the histogram images.
        
        Allows the user to select regions in which to search for fiducials.
        
        WARNING: This will reset the currently saved search regions.
        
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
        self.resetSearchRegions()
        
        def onClose(event):
            """Run when the figure closes.
            
            """
            print('Closed Figure!')
            fig.canvas.stop_event_loop()
            
        def onSelect(eclick, erelease):
            pass
        
        def toggleSelector(event, processor):
            """Handles user input.
            
            """
            if event.key in ['r', 'R']:
                print('Search regions reset to None.')
                self.resetSearchRegions()
            
            if event.key in [' ']:
                # Clear searchRegions if they are not empty
                #(Important for when multiple search regions are selected.)
                if not self.searchRegions[0]['xMin']:                
                    # Convert searchRegions to empty list ready for appending
                    self.searchRegions = []
                
                print('Space bar pressed!')
                xMin, xMax, yMin, yMax = toggleSelector.RS.extents
                processor.searchRegions.append({'xMin' : xMin/unitConvFactor,
                                                'xMax' : xMax/unitConvFactor,
                                                'yMin' : yMin/unitConvFactor,
                                                'yMax' : yMax/unitConvFactor})
    
        fig, ax = plt.subplots()
        fig.canvas.mpl_connect('close_event', onClose)        
        
        im      = ax.hexbin(df['x'] * unitConvFactor,
                            df['y'] * unitConvFactor,
                            gridsize = gridSize,
                            cmap = plt.cm.YlOrRd_r)
        ax.set_xlabel(r'x-position, ' + unitLabel)
        ax.set_ylabel(r'y-position, ' + unitLabel)
        ax.invert_yaxis()
    
        cb      = plt.colorbar(im)
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
        plt.show()        
        fig.canvas.start_event_loop_default()
    
    def fitSplines(self):
        """Perform a spline fit based on previously identified fiducials.
        
        NOT IMPLEMENTED
        
        """
        pass
    
    def plotFiducials(self, splineNumber = None):
        """Make a plot of each fiducial track and spline fit for verification.
                
        Parameters
        ----------
        splineNumber : int
            Index of the spline to plot. (0-index)
        
        """
        if not splineNumber:
            startIndex = 0
            stopIndex  = len(self.splines)
        else:
            # Plot only the input spline
            startIndex = splineNumber
            stopIndex  = splineNumber + 1
        
        for fid in range(startIndex, stopIndex):
            fig, (axx, axy) = plt.subplots(nrows = 2, ncols = 1, sharex = True) 
            
            # Shift fiducial trajectories to zero at their start
            x0 = self.fiducialTrajectories[fid]['x'].iloc[[0]].as_matrix()
            y0 = self.fiducialTrajectories[fid]['y'].iloc[[0]].as_matrix()
            
            axx.plot(self.fiducialTrajectories[fid]['frame'],
                     self.fiducialTrajectories[fid]['x'] - x0,
                     '.',
                     color = 'blue',
                     alpha = 0.5)
            axx.plot(self.avgSpline.index,
                     self.avgSpline['xS'],
                     linewidth = 3,
                     color = 'red')
            axx.set_ylabel('x-position')
            axx.set_title('Fiducial number: {0:d}'.format(fid))
                     
            axy.plot(self.fiducialTrajectories[fid]['frame'],
                     self.fiducialTrajectories[fid]['y'] - y0,
                     '.',
                     color = 'blue',
                     alpha = 0.5)
            axy.plot(self.avgSpline.index,
                     self.avgSpline['yS'],
                     linewidth = 3,
                     color = 'red')
            axy.set_xlabel('Frame number')
            axy.set_ylabel('y-position')
            plt.show()
            
    def plotSplines(self):
        """Plot the spline fits on top of one another.
        
        NOT IMPLEMENTED
        
        """
        pass
    
    def resetSearchRegions(self):
        """Resets the search regions so that the entire dataset is searched.
        
        """
        self.searchRegions = [{'xMin' : None,
                               'xMax' : None,
                               'yMin' : None,
                               'yMax' : None}]
    
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
        ts2leb['sigma [nm]']         = 'sigma'
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
        