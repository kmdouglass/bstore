# © All rights reserved. ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Switzerland, Laboratory of Experimental Biophysics, 2016
# See the LICENSE.txt file for more details.

import pandas as pd
import trackpy as tp
import numpy as np
import matplotlib.pyplot as plt
import re
from abc import ABCMeta, abstractmethod, abstractproperty
from sklearn.cluster import DBSCAN
from operator import *
from scipy.signal import gaussian
from scipy.ndimage import filters
from scipy.interpolate import UnivariateSpline, interp1d
from scipy.optimize import minimize
from matplotlib.widgets import RectangleSelector
from bstore import config
from bstore.parsers import FormatMap
import warnings

__version__ = config.__bstore_Version__

"""Metaclasses
-------------------------------------------------------------------------------
"""


class ComputeTrajectories(metaclass=ABCMeta):
    """Basic functionality for computing trajectories from localizations.
    
    This is used to compute trajectories from regions of a dataset containing
    localizations, such as fiducial drift trajectories (position vs. frame
    number)or astigmatic calibration curves (PSF width vs. z).

    Attributes
    ----------
    regionLocs : Pandas DataFrame
        The localizations for individual regions.

    """

    def __init__(self):
        """Initializes the trajectory computer.

        """
        self._regionData = None
        
    def _plotCurves(self, curveNumber=None, coordCols=['x', 'y'],
                    horizontalLabels=['', 'time'], verticalLabels=['x', 'y'],
                    title='trajectories', splineCols=['t','x','y'],
                    offsets=[0,0], ylims=[-100, 500, -100, 500]):
        """Make a plot of each region's trajectory and the average spline fit.

        plotCurves allows the user to check the trajectories of localizations
        and their fits against the average spline fit.

        Parameters
        ----------
        curveNumber      : int
            Index of the spline to plot. (0-index)
        coordCols        : list of string
            The column names corresponding to the trajectory's dependent
            variable (e.g. time or z-position) and the localizations' x- and
            y-coordinates (order is t, x, y).
        horizontalLabels : list of string
            The labels for the x-axes of each trajectory plot.
        verticalLabels   : list of string
            The labels for the y-axes for each trajectory (order is
            x-trajectory, then y).
        title : str
            The title of each plot.
        splineCols : list of str
            The column names of the average spline DataFrame that correspond to
            the trajectory's dependent variable (i.e. z-position or frame
            number,) the localizations' x-coordinates, and the localizaitons'
            y-coordinates, respectively.
        offsets : list of int
            The vertical offsets to apply to the curves.
        ylims   : list of float
            The y-limits of the two trajectory plots (order is min and max of 
            x-trajectory, then min and max of the y-trajectory).

        """
        t, x, y                    = coordCols
        xHorzLabel, yHorzLabel     = horizontalLabels
        xVertLabel, yVertLabel     = verticalLabels
        ts, xs, ys                 = splineCols
        x0, y0                     = offsets
        minxy, maxxy, minyy, maxyy = ylims

        if self.regionLocs is None:
            raise ZeroRegions(
                'Zero regions are currently saved with this processor.')

        fig, (axx, axy) = plt.subplots(nrows=2, ncols=1, sharex=True)
        locs = self.regionLocs.xs(curveNumber, level='region_id',
                                  drop_level=False)

        # Filter out localizations that are outliers
        outliers = locs.loc[locs[self._includeColName] == False]
        locs = locs.loc[locs[self._includeColName]]

        if (curveNumber in self.useTrajectories) or (not self.useTrajectories):
            markerColor = 'blue'
        else:
            markerColor = '#999999' # gray

        axx.plot(locs[t],
                 locs[x] - x0,
                 '.',
                 color=markerColor,
                 alpha=0.5)
        axx.plot(outliers[t],
                 outliers[x] - x0,
                 'x',
                 color='#999999',
                 alpha=0.5)
        axx.plot(self.avgSpline[ts],
                 self.avgSpline[xs],
                 linewidth=2,
                 color='orange')
        axx.set_xlabel(xHorzLabel)
        axx.set_ylabel(xVertLabel)
        axx.set_title('{0:s}, Region number: {1:d}'.format(title, curveNumber))
        axx.set_ylim((minxy, maxxy))

        axy.plot(locs[t],
                 locs[y] - y0,
                 '.',
                 color=markerColor,
                 alpha=0.5)
        axy.plot(outliers[t],
                 outliers[y] - y0,
                 'x',
                 color='#999999',
                 alpha=0.5)
        axy.plot(self.avgSpline[ts],
                 self.avgSpline[ys],
                 linewidth=2,
                 color='orange')
        axy.set_xlabel(yHorzLabel)
        axy.set_ylabel(yVertLabel)
        axy.set_ylim((minyy, maxyy))
        plt.show()

    @property
    def regionLocs(self):
        """DataFrame holding the localizations for individual fiducials.

        """
        return self._regionData

    @regionLocs.setter
    def regionLocs(self, regionData):
        """Checks that the fiducial localizations are formatted correctly.

        """
        if regionData is not None:
            assert 'region_id' in regionData.index.names, \
                'regionLocs DataFrame requires index named "region_id"'

            # Sort the multi-index to allow slicing
            regionData.sort_index(inplace=True)

        self._regionData = regionData

    def clearRegionLocs(self):
        """Clears any currently held localization data.

        """
        self._regionData = None

    @abstractmethod
    def computeTrajectory(self):
        """Computes the trajectory.

        """
        pass
    
    def _movingAverage(self, series, windowSize=100, sigma=3):
        """Estimate the weights for smoothing splines.

        Parameters
        ----------
        series     : array of int
            Discrete samples from a time series.
        windowSize : int
            Size of the moving average window in axial slices.
        sigma      : int
            Size of the Gaussian averaging kernel in axial slices.

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
        b = gaussian(windowSize, sigma)
        average = filters.convolve1d(series, b / b.sum())
        var = filters.convolve1d(np.power(series - average, 2), b / b.sum())
        return average, var

    @abstractmethod
    def reset(self):
        """Resets the drift computer to its initial value.

        """
        pass


class DriftCorrect(metaclass=ABCMeta):
    """Basic functionality for a drift correction processor.

    Attributes
    ----------
    correctorType : string
        Identifies the type of drift corrector for a specific class.
    driftTrajectory : Pandas DataFrame
        x,y pairs each possessing a unique frame number.

    """
    @abstractproperty
    def correctorType(self):
        """Identifies the type of drift corrector for a specific class.

        """
        pass

    @abstractproperty
    def driftTrajectory(self):
        """A list of x,y pairs with each possessing a unique frame number.

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


class MergeStats(metaclass=ABCMeta):
    """Basic functionality for computing statistics from merged localizations.

    """
    @abstractmethod
    def computeStatistics(self):
        """Computes the merged molecule statistics.

        """
        pass

    def _wAvg(self, group, coordinate, photonsCol='photons'):
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
        photons = group[photonsCol]

        wAvg = (positions * photons.apply(np.sqrt)).sum() \
            / photons.apply(np.sqrt).sum()

        return wAvg
    
"""
Utility classes
-------------------------------------------------------------------------------
"""


class SelectLocalizations:
    """Interactively select localizations using rectangular ROI's.
    
    This class is used to display an image containing information about the
    local density of localizations within a dataset. From this image, a user
    may interactively select regions containing localizations for further
    analysis, such as when performing fiducial drift corrections.
    
    """
    def __init__(self):
        # Setup the class fields
        self._regions = [{'xMin': None, 'xMax': None,
                          'yMin': None, 'yMax': None}]
            
    def doInteractiveSearch(self, df, gridSize=100, unitConvFactor=1. / 1000,
                            unitLabel='microns'):
        """Interactively find regions in the histogram images.

        Allows the user to select regions and extract localizations.

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
        self._regions = [{'xMin': None, 'xMax': None,
                          'yMin': None, 'yMax': None}]

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
                if not self._regions[0]['xMin']:
                    # Convert _regions to empty list ready for appending
                    self._regions = []

                xMin, xMax, yMin, yMax = toggleSelector.RS.extents
                processor._regions.append({'xMin': xMin / unitConvFactor,
                                           'xMax': xMax / unitConvFactor,
                                           'yMin': yMin / unitConvFactor,
                                           'yMax': yMax / unitConvFactor})

        fig, ax = plt.subplots()
        fig.canvas.mpl_connect('close_event', onClose)

        im = ax.hexbin(df[self._coordCols[0]] * unitConvFactor,
                       df[self._coordCols[1]] * unitConvFactor,
                       gridsize=gridSize, cmap=plt.cm.YlOrRd_r)
        ax.set_xlabel(r'x-position, ' + unitLabel)
        ax.set_ylabel(r'y-position, ' + unitLabel)
        ax.invert_yaxis()

        cb = plt.colorbar(im)
        cb.set_label('Counts')

        toggleSelector.RS = RectangleSelector(ax,
                                              onSelect,
                                              drawtype='box',
                                              useblit=True,
                                              button=[1, 3],  # l/r only
                                              spancoords='data',
                                              interactive=True)
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
        if not self._regions[0]['xMin']:
            raise ZeroFiducialRegions('Error: Identified no fiducial regions.')

        locsInRegions = []
        numRegions = len(self._regions)
        for regionNumber in range(numRegions):
            xMin = self._regions[regionNumber]['xMin']
            xMax = self._regions[regionNumber]['xMax']
            yMin = self._regions[regionNumber]['yMin']
            yMax = self._regions[regionNumber]['yMax']

            # Isolate the localizations within the current region
            locsInCurrRegion = df[(df[self._coordCols[0]] > xMin) &
                                  (df[self._coordCols[0]] < xMax) &
                                  (df[self._coordCols[1]] > yMin) &
                                  (df[self._coordCols[1]] < yMax)].copy()

            # Add a multi-index identifying the region number
            locsInCurrRegion['region_id'] = regionNumber
            locsInCurrRegion.set_index(['region_id'], append=True,
                                       inplace=True)

            locsInRegions.append(locsInCurrRegion)

        return pd.concat(locsInRegions)

"""
Concrete classes
-------------------------------------------------------------------------------
"""


class AddColumn:
    """Adds a column to a DataFrame.

    AddColumn adds a column to a DataFrame and initializes every row to the
    same value.

    Parameters
    ----------
    columnName   : str
        The name of the new column.
    defaultValue : mixed datatype
        The default value to assign to each row of the new column.

    Attributes
    ----------
    columnName       : str
        The name of the new column.
    defaultValue     : mixed datatype
        The default value to assign to each row of the new column.

    """

    def __init__(self, columnName, defaultValue=True):
        self.columnName = columnName
        self.defaultValue = defaultValue

    def __call__(self, df):
        """Add the new column to the DataFrame.

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

        numRows, _ = procdf.shape
        procdf[self.columnName] = pd.Series([self.defaultValue] * numRows,
                                            index=procdf.index)

        return procdf

class CalibrateAstigmatism(SelectLocalizations):
    """Computes calibration curves for astigmatic imaging from bead stacks.
    
    Parameters
    ----------
    interactiveSearch : bool
        Determines whether the user will interactively find fiducials.
        Setting this to False means that fiducials are found automatically,
        although this is not always reliable.
    coordCols : list of str
        List of strings identifying the x- and y-coordinate column names
        in that order.
    sigmaCols : list of str
        List of strings identifying the column names containing the PSF widths
        in x and y.
    zCol      : str
        Name of the column identifying the z-coordinate values.
    astigmatismComputer: ComputeTrajectories
        Algorithm for computing astigmatic calibration curves.
    wobbleComputer: ComputeTrajectories
        Algorithm for computing wobble calibration curves.
        
    Attributes
    ----------
    interactiveSearch : bool
        Determines whether the user will interactively find fiducials.
        Setting this to False means that fiducials are found automatically,
        although this is not always reliable.
    astigmatismComputer: AstigComputer
        Algorithm for computing astigmatic calibration curves.
    calibrationCurves : func, func
        The calibration curves for astigmatic 3D imaging. The first
        element contains the PSF width in x as a function of z and
        the second contains the width in y as a function of z.
    wobbleCurves : func, func
        The wobble curves for astigmatic 3D imaging. These map the PSF centroid
        positions as a function of z. See Ref. 1 for more information.
        
    References
    ----------
    1. Carlini, et al., "Correction of a Depth-Dependent Lateral Distortion in
    3D Super-Resolution Imaging," PLoS One 10(11):e0142949 (2015).
    
    """
    def __init__(self, interactiveSearch=True, coordCols=['x', 'y'],
                 sigmaCols=['sigma_x', 'sigma_y'], zCol='z', startz=None,
                 stopz=None, astigmatismComputer=None, wobbleComputer=None):
        self.interactiveSearch = interactiveSearch
        self.calibrationCurves = None
        self.wobbleCurves      = None
        
        self._coordCols = coordCols
        self._sigmaCols = sigmaCols
        self._zCol      = zCol
        
        if astigmatismComputer:
            self.astigmatismComputer = astigmatismComputer
        else:
            self.astigmatismComputer = DefaultAstigmatismComputer(
                                           coordCols=coordCols, 
                                           sigmaCols=sigmaCols, zCol=zCol)
            
        if wobbleComputer:
            self.wobbleComputer = wobbleComputer
        else:
            self.wobbleComputer = DefaultAstigmatismComputer(
                                      coordCols=coordCols, sigmaCols=coordCols,
                                      zCol=zCol, zeroz=0)            
        
    
    def __call__(self, df):
        """Computes the astigmatic calibration curves from user-selected beads.
        
        Parameters
        ----------
        df : DataFrame
            A Pandas DataFrame object.
            
        Returns
        -------
        df : DataFrame
            The same Pandas DataFrame object is returned because the original
            localizations are not modified.
        
        """
        # Update the wobble computer to match the same fitting range as the
        # astigmatism computer. This prevents problems with the display of bead
        # fits where the points not included in the astigmatism curve fits
        # reflected the wobble computer settings.   
        print(('Setting wobble fiting range to the match the astigmatism fit '
               'range. startz and stopz are set in the astigmatism computer.'))
        self.wobbleComputer.startz = self.astigmatismComputer.startz
        self.wobbleComputer.stopz  = self.astigmatismComputer.stopz
        
        if self.interactiveSearch:
            self.doInteractiveSearch(df)

            try:
                locs = self._extractLocsFromRegions(df)
            except ZeroFiducialRegions:
                print('No regions containing localizations identified. '
                      'Returning original DataFrame.')
                self.astigmatismComputer.clearRegionLocs()
                self.wobbleComputer.clearRegionLocs()
                return df
        else:
            locs = self.astigmatismComputer.regionLocs
        
        # This returns the average splines, but we don't need them.
        _ = self.astigmatismComputer.computeTrajectory(locs)
        _ = self.wobbleComputer.computeTrajectory(locs)
        
        self.calibrationCurves = self._computeCalibrationCurves(
                                     self.astigmatismComputer.avgSpline)
        self.wobbleCurves      = self._computeCalibrationCurves(
                                     self.wobbleComputer.avgSpline)
        
        return df
    
    def _computeCalibrationCurves(self, avgSpline):
        """Computes the 3D astigmatic calibration curve from average splines.
        
        Parameters
        ----------
        avgSpline : Pandas DataFrame
            The averaged spline fits to bead data.
        
        Returns
        -------
        fx : func
            The calibration curve that returns the the width in x as
            a function of z.
        fy : func
            The calibration curve that returns the the width in y as
            a function of z.
        
        """
        xS, yS     = avgSpline['xS'], avgSpline['yS']
        zPos       = avgSpline['z']
        
        
        fx = interp1d(zPos, xS, kind='cubic', bounds_error=False,
                      fill_value=np.NaN, assume_sorted=False)
        fy = interp1d(zPos, yS, kind='cubic', bounds_error=False,
                      fill_value=np.NaN, assume_sorted=False)
        
        return fx, fy
    

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
            procdf[column] = pd.to_numeric(procdf[column], errors='coerce')

        procdf.replace([np.inf, -np.inf], np.nan, inplace=True)
        procdf.dropna(inplace=True)

        # DO NOT USE procdf.reindex() because it will not
        # automatically reorder an index correctly. It is
        # used for other purposes.
        procdf.index = np.arange(procdf.shape[0])

        return procdf


class Cluster:
    """Clusters the localizations into spatial clusters.

    Parameters
    ----------
    minSamples : int
        Minimum number of samples within one neighborhood radius.
    eps        : float
        The neighborhood radius defining a cluster.
    coordCols  : list of str
        The columns of the data to be clustered in the format ['x', 'y'].

    """

    def __init__(self, minSamples=50, eps=20, coordCols=['x', 'y']):
        self._minSamples = minSamples
        self._eps = eps
        self._coordCols = coordCols

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
            A DataFrame object with containing a new column indicating the
            cluster ID.

        """
        columnsToCluster = self._coordCols

        # Setup and perform the clustering
        db = DBSCAN(min_samples=self._minSamples, eps=self._eps)
        db.fit(df[columnsToCluster])

        # Get the cluster labels and make it a Pandas Series
        clusterLabels = pd.Series(db.labels_, name='cluster_id')

        # Append the labels to the DataFrame
        procdf = pd.concat([df, clusterLabels], axis=1)

        return procdf


class ComputeClusterStats:
    """Computes statistics for clusters of localizations.

    Parameters
    ----------
    idLabel          : str
        The column name containing cluster ID's.
    coordCols        : list of string
        A list containing the column names containing the transverse
        localization coordinates.
    zCoord           : str
        The column name of the axial coordinate.
    statsFunctions   : dict of name/function pairs
        A dictionary containing column names and functions for computing
        custom statistics from the clustered localizations. The keys in
        dictionary determine the name of the customized column and the
        value contains a function that computes a number from the
        coordinates of the localizations in each cluster.

    """

    # The name to append to the center coordinate column names
    centerName = '_center'

    def __init__(self, idLabel='cluster_id',
                 coordCols=['x', 'y'],
                 zCoord='z',
                 statsFunctions=None):
        self._idLabel = idLabel
        self._statsFunctions = {'radius_of_gyration': self._radiusOfGyration,
                                'eccentricity': self._eccentricity,
                                'convex_hull': self._convexHull}

        self.coordCols = coordCols
        self.zCoord = zCoord

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
        tempResultsCoM = groups[self.coordCols].agg(np.mean)
        tempResultsLength = pd.Series(groups.size())

        # Compute the custom statistics for each cluster and set
        # the column name to the dictionary key
        tempResultsCustom = []
        for name, func in self._statsFunctions.items():
            temp = groups.apply(func, self.coordCols, self.zCoord)
            temp.name = name  # The name of the column is now the dictionary key
            tempResultsCustom.append(temp)

        # Appends '_center' to the names of the coordinate columns
        # and renames the series
        newCoordCols = [col + self.centerName for col in self.coordCols]
        nameMapping = dict(zip(self.coordCols, newCoordCols))

        tempResultsCoM.rename(columns=nameMapping,
                              inplace=True)
        tempResultsLength.name = 'number_of_localizations'

        # Create the merged DataFrame
        dataToJoin = [tempResultsCoM,
                      tempResultsLength]
        dataToJoin = dataToJoin + tempResultsCustom

        procdf = pd.concat(dataToJoin, axis=1)

        # Convert the cluster_id index to a column
        procdf.reset_index(level=['cluster_id'], inplace=True)

        return procdf

    def _radiusOfGyration(self, group, coordinates, zCoordinate):
        """Computes the radius of gyration of a grouped cluster.

        Parameters
        ----------
        group       : Pandas GroupBy
            The clustered localizations.
        coordinates : list of str
            The columns to use for performing the computation; 
            typically these containg the localization coordinates.
        zCoordinate : str
            The column title of the axial coordinate.

        Returns
        -------
        Rg    : float
            The radius of gyration of the group of localizations.

        Notes
        -----
        This currently only uses the transverse coordinates and
        ignores the z-coordinate.

        """
        variances = group[coordinates].var(ddof=0)

        Rg = np.sqrt(variances.sum())
        return Rg

    def _eccentricity(self, group, coordinates, zCoordinate):
        """ Computes the eccentricity of a grouped cluster.

        Parameters
        ----------
        group : Pandas GroupBy
            The clustered localizations.
        coordinates : list of str
            The columns to use for performing the computation; typically these
            containg the localization coordinates.
        zCoordinate : str
            The column title of the axial coordinate.

        Returns
        -------
        ecc   : float
            The eccentricity of the group of localizations.

        Notes
        -----
        This currently only uses the transverse coordinates and
        ignores the z-coordinate.

        """
        try:
            # Compute the covariance matrix  and its eigevalues
            Mcov = np.cov(group[coordinates].as_matrix(),
                          rowvar=0,
                          bias=1)
            eigs = np.linalg.eigvals(Mcov)
            ecc = np.max(eigs) / min(eigs)
        except:
            print('Warning: Error occurred during eccentricity computation. '
                  'Returning NaN instead.')
            ecc = np.nan
            
        return ecc

    def _convexHull(self, group, coordinates, zCoordinate):
        """Computes the volume of the cluster's complex hull.

        Parameters
        ----------
        group : Pandas GroupBy
            The clustered localizations.
        coordinates : list of str
            The columns to use for performing the computation; typically these
            containg the localization coordinates.
        zCoordinate : str
            The column title of the axial coordinate.

        Returns
        -------
        volume : float or np.nan

        Notes
        -----
        This currently only uses the transverse coordinates and
        ignores the z-coordinate.

        """
        # Compute CHull only if pyhull is installed
        # pyhull is only available in Linux
        try:
            from pyhull import qconvex
        except ImportError:
            print(('Warning: pyhull is not installed. '
                   'Cannot compute convex hull. Returning NaN instead.'))
            return np.nan

        # Find output volume
        try:
            points = group[coordinates].as_matrix()
            output = qconvex('FA', points)
            volume = [vol for vol in output if 'Total volume:' in vol][0]
            volume = float(re.findall(r'[-+]?[0-9]*\.?[0-9]+', volume)[0])
        except:
            print(('Warning: Error occurred during convhex hull computation. '
                   'Returning NaN instead.'))
            volume = np.nan

        return volume
    
class ComputeZPosition:
    """Computes the localizations' z-positions from calibration curves.
    
    Parameters
    ----------
    zFunc         : func
        Function(s) mapping the PSF widths onto Z. Supply this 
        argument as a tuple in the order (fx, fy).
    zCol          : str
        The name to assign to the new column of z-positions.
    coordCols     : list of str
        The x- and y-coordinate column names, in that order. This is only used
        for the wobble correction if wobbleFunc is not None.
    sigmaCols     : list of str
        The column names containing the PSF widths in the x- and y-directions,
        respectively.
    fittype       : str
        String indicating the type of fit to use when deriving the z-positions.
        Can be either 'huang', which minimizes a distance-like objective
        function, or 'diff', which interpolates a curve based on the difference
        between PSF widths in x and y.
    scalingFactor : float
        A scaling factor that multiples the computed z-values to account for
        a refractive index mismatch at the coverslip. See [1] for more details.
        This can safely be left at one and the computed z-values rescaled later
        if you are uncertain about the value to use.
    wobbleFunc    : func
        Function(s) mapping the PSF centroids onto Z. Supply this 
        argument as a tuple in the order (fx, fy). See [2] for more details.
        
    References
    ----------
    1. Huang, et al., Science 319, 810-813 (2008)
    2. Carlini, et al., PLoS One 10(11):e0142949 (2015).
    
    """
    def __init__(self, zFunc, zCol='z', coordCols=['x', 'y'],
                 sigmaCols=['sigma_x, sigma_y'],
                 fittype='diff', scalingFactor=1, wobbleFunc = None):
        self.zFunc         = zFunc
        self.zCol          = zCol
        self.coordCols     = coordCols
        self.sigmaCols     = sigmaCols
        self.fittype       = fittype
        self.scalingFactor = scalingFactor
        self.wobbleFunc    = wobbleFunc
        
        # This is the calibration curve computed when fittype='diff' and is
        # used internally for error checking and testing.
        self._f = None
    
    def __call__(self, df):
        """ Applies zFunc to the localizations to produce the z-positions.
        
        Parameters
        ----------
        df : DataFrame
            A Pandas DataFrame object.

        Returns
        -------
        procdf : DataFrame
            A DataFrame object with the same information but new column names.
            
        """
        x, y   = self.sigmaCols
        fx, fy = self.zFunc
        
        if self.fittype == 'diff':
            procdf = self._diff(df, x, y, fx, fy)
        elif self.fittype == 'huang':
            procdf = self._huang(df, x, y, fx, fy)
            
        procdf[self.zCol] *= self.scalingFactor
        
        if self.wobbleFunc:
            procdf = self._wobble(procdf)
            
        return procdf
    
    def _diff(self, df, x, y, fx, fy):
        """Determines the z-position from the difference in x- and y-widths.
        
        In this approach, the two calibration curves are sampled, subtracted
        from one another, and then reinterpolated to produce a function
        representing the axial position as a function of the difference between
        the PSF widths in x and y.
        
        In general, it is much faster than the optimization routine used in
        Huang et al., Science 2008.
        
        """
        df = df.copy() #  Prevents overwriting input DataFrame
        
        # Get minimum and maximum z-positions contained in calibration curves.
        # This is required to define the bounds on the sampling domain.
        zMin, zMax = np.min([fx.x, fy.x]), np.max([fx.x, fy.x])
        zSamples = np.linspace(zMin, zMax, num=150)
        
        # Create the function representing the difference between calibration
        # curves.
        def dW(fx, fy):
            return lambda z: fx(z) - fy(z)
        
        f = interp1d(dW(fx, fy)(zSamples), zSamples, bounds_error=False,
                     fill_value=np.NaN, assume_sorted=False)
        self._f = f
        
        # Compute the z-positions from this interpolated curve
        locWidths = df[x] - df[y]
        z = f(locWidths)
        
        df[self.zCol] = z
        return df
    
    def _huang(self, df, x, y, fx, fy):
        """Determines the z-position by objective minimization.
        
        This routine can be very slow, especially for large datasets. It is
        recommended to try it on a very slow dataset first.
        
        """
        df = df.copy() # Prevents overwriting input DataFrame
        
        # Create the objective function for the distance between the data and
        # calibration curves.
        def D(z, wx, wy):
            return np.sqrt((wx**0.5 - fx(z)**0.5)**2 + \
                           (wy**0.5 - fy(z)**0.5)**2)
        
        # Create the objective function to minimize
        def fmin(wx, wy):
            res = minimize(lambda z: D(z, wx, wy), [0], bounds=[(-600,600)])
            return res.x[0]
        
        df[self.zCol] = df.apply(lambda row: fmin(row[x], row[y]), axis=1)
        return df
    
    def _wobble(self, df):
        """Corrects localizations for wobble.
        
        This function takes a DataFrame of localizations whose z-positions were
        already computed and determines the x- and y-corrections necessary to
        correct for an axial dependence of the centriod position. It then
        applies these corrections and returns the processed DataFrame.
        
        Parameters
        ----------
        df : DataFrame
            A Pandas DataFrame containing the localizations.
            
        Returns
        -------
        df : DataFrame
            The wobble-corrected DataFrame.
        
        """
        df     = df.copy() # Prevents overwriting input DataFrame
        x, y   = self.coordCols
        zLocs  = df[self.zCol]
        fx, fy = self.wobbleFunc
        
        xc = fx(zLocs)
        yc = fy(zLocs)
        
        df['dx'] = xc
        df['dy'] = yc
        df[x] = df[x] - xc
        df[y] = df[y] - yc
        
        return df

class ConvertHeader:
    """Converts the column names in a localization file to a different format.

    Parameters
    ----------
    mapping      : FormatMap
        A two-way dictionary for converting from column name to another.

    Attributes
    ----------
    mapping      : FormatMap
        A two-way dictionary for converting from column name to another.

    """

    def __init__(self, mapping=FormatMap(config.__Format_Default__)):
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


class DefaultAstigmatismComputer(ComputeTrajectories):
    """Default algorithm for computing astigmatic calibration curves.
    
    Parameters
    ----------
    coordCols : list of str
        List of strings identifying the x- and y-coordinate column names
        in that order.
    sigmaCols : list of str
        List of strings identifying the column names containing the PSF widths
        in x and y.
    zCol      : str
        Name of the column identifying the z-coordinate values.
    smoothingWindowSize : float
        Moving average window size in slices for spline fitting.
    smoothingFilterSize : float
        Moving average Gaussian kernel width in slices for spline fitting.
    useTrajectories : list of int or empty list
        List of integers corresponding to the fiducial trajectories to use
        when computing the average trajectory. If [], all trajectories
        are used.
    startz    : float
        The start point of the z-fitting range.
    stopz     : float
        The end point of the z-fitting range.
    zeroz     : None or float
        The z-position corresponding to the focal plane. This is used only for
        the calculation of the wobble curves and NOT the astigmatism curves.
        Set to None if this computer is intended to compute astigmatism curves;
        set to a number to compute wobble curves.
    
    """
    def __init__(self, coordCols=['x','y'], sigmaCols=['sigma_x', 'sigma_y'],
                 zCol='z', smoothingWindowSize=20, smoothingFilterSize=3,
                 useTrajectories=[], startz=None, stopz=None, zeroz = None):
        self.coordCols           = coordCols
        self.sigmaCols           = sigmaCols
        self.zCol                = zCol
        self.smoothingWindowSize = smoothingWindowSize
        self.smoothingFilterSize = smoothingFilterSize
        self.useTrajectories     = useTrajectories
        self.startz = startz
        self.stopz  = stopz
        self.zeroz  = zeroz
        super(ComputeTrajectories, self).__init__()
        
        # Column of DataFrame used to indicate what localizations are not
        # included in a trajectory for a spline fit, e.g. outliers
        self._includeColName = 'included_in_trajectory'
        
        # initial state
        self._init_coordCols           = coordCols.copy()
        self._init_sigmaCols           = sigmaCols.copy()
        self._init_zCol                = zCol
        self._init_smoothingWindowSize = smoothingWindowSize
        self._init_smoothingFilterSize = smoothingFilterSize
        self._init_useTrajectories     = useTrajectories.copy()
        self._init_startz              = startz
        self._init_stopz               = stopz
        self._init_zeroz               = zeroz
        
        
    def combineCurves(self, startz, stopz):
        """Average the splines from different fiducials together.

        Parameters
        ----------
        startz : float
            Minimum frame number in full dataset
        stopz  : float
            Maximum frame number in full dataset

        """
        zPos = np.linspace(startz, stopz, num=100)
        numSplines = len(self.splines)

        # Evalute each x and y spline at every frame position
        fullRangeSplines = {'xS': np.array([self.splines[i]['xS'](zPos)
                                            for i in range(numSplines)]),
                            'yS': np.array([self.splines[i]['yS'](zPos)
                                            for i in range(numSplines)])}

        # Create the mask area if only certain fiducials are to be averaged
        if not self.useTrajectories:
            mask = np.arange(numSplines)
        else:
            mask = self.useTrajectories

        # Compute the average over spline values
        avgSpline = {'xS': [], 'yS': []}

        try:
            for key in avgSpline.keys():
                avgSpline[key] = np.mean(fullRangeSplines[key][mask], axis=0)
        except IndexError:
            raise UseTrajectoryError(
                'At least one of the indexes inside '
                'useTrajectories does not match a known fiducial '
                'index. The maximum fiducial index is {0:d}.'
                ''.format(
                    numSplines - 1))
        
        # Append z positions to avgSpline
        avgSpline['z'] = zPos

        self.avgSpline = pd.DataFrame(avgSpline)
        
    def computeTrajectory(self, locs):
        """Computes the final drift trajectory from fiducial localizations.

        Parameters
        ----------
        locs        : Pandas DataFrame
            DataFrame containing the localizations belonging to beads.

        Returns
        -------
        avgSpline : Pandas DataFrame
            A dataframe containing z-positions and PSF widths in x- and y- for
            calibrating an astigmatic imaging measurement.

        """
        z = self.zCol
        if self.startz:
            startz = self.startz
        else:
            startz = locs[z].min()
        
        if self.stopz:
            stopz = self.stopz
        else:
            stopz  = locs[z].max()
        
        self.clearRegionLocs()
        self.regionLocs = locs
        self._removeOutliers(startz, stopz)
        self.fitCurves()
        self.combineCurves(startz, stopz)

        return self.avgSpline
    
    def _computeOffsets(self, locs):
        """Compute the offsets for bead trajectories to align curves at z=0.

        Parameters
        ----------
        locs : Pandas DataFrame
            Localizations from a single bead region.

        Returns
        -------
        x0, y0 : tuple of int
            The offsets to subtract from the localizations belonging to a
            bead.

        """
        avgOffset = 10
        x, y = self.coordCols[0], self.coordCols[1]
        startFrame, stopFrame = locs[self.zCol].min(), \
            locs[self.zCol].max()
            
        # Convert None's to infinity for comparison
        if self.startz == None:
            startz = -np.inf
        else:
            startz = self.startz
        if self.stopz == None:
            stopz = np.inf
        else:
            stopz = self.stopz
        

        if self.zeroz > stopz or self.zeroz < startz:
            warnings.warn(('Warning: zeroz ({0:d}) is outside the '
                           'allowable range of frame numbers in this dataset '
                           '({1:d} - {2:d}). Try a different zeroz value.'
                           ''.format(self.zeroz, startFrame + avgOffset,
                                     stopFrame - avgOffset)))

        # Average the localizations around the zeroz value
        x0 = locs[(locs[self.zCol] > self.zeroz - avgOffset)
                & (locs[self.zCol] < self.zeroz + avgOffset)][x].mean()
        y0 = locs[(locs[self.zCol] > self.zeroz - avgOffset)
                & (locs[self.zCol] < self.zeroz + avgOffset)][y].mean()

        if (x0 is np.nan) or (y0 is np.nan):
            warnings.warn('Could not determine an offset value; '
                          'setting offsets to zero.')
            x0, y0 = 0, 0

        return x0, y0

    def fitCurves(self):
        """Fits individual splines to each z-scan.

        """
        print('Performing spline fits...')
        # Check whether trajectories already exist
        if self.regionLocs is None:
            raise ZeroRegions('Zero regions containing beads are currently '
                              'saved with this processor.')

        self.splines = []
        regionIDIndex = self.regionLocs.index.names.index('region_id')
        x = self.sigmaCols[0]
        y = self.sigmaCols[1]
        z = self.zCol
        
        # rid is an integer
        for rid in self.regionLocs.index.levels[regionIDIndex]:
            # Get localizations from inside the current region matching rid
            # and that passed the _removeOutliers() step
            currRegionLocs = self.regionLocs.xs(
                rid, level='region_id', drop_level=False)

            # Use only those fiducials within a certain radius of the
            # cluster of localization's center of mass
            currRegionLocs = currRegionLocs.loc[
                currRegionLocs[self._includeColName]]
            
            windowSize = self.smoothingWindowSize
            sigma = self.smoothingFilterSize
            
            # Shift the localization(s) at zeroz to (x = 0, y = 0) by
            # subtracting its value at frame number zeroFrame
            if self.zeroz is not None:
                x0, y0 = self._computeOffsets(currRegionLocs)
            else:
                x0, y0 = 0, 0
    
            # Determine the appropriate weighting factors
            _, varx = self._movingAverage(currRegionLocs[x] - x0,
                                          windowSize=windowSize,
                                          sigma=sigma)
            _, vary = self._movingAverage(currRegionLocs[y] - y0,
                                          windowSize=windowSize,
                                          sigma=sigma)
    
            # Perform spline fits. Extrapolate using boundary values (const)
            extrapMethod = 'extrapolate'
            xSpline = UnivariateSpline(currRegionLocs[z].as_matrix(),
                                       currRegionLocs[x].as_matrix() - x0,
                                       w=1 / np.sqrt(varx),
                                       ext=extrapMethod)
            ySpline = UnivariateSpline(currRegionLocs[z].as_matrix(),
                                       currRegionLocs[y].as_matrix() - y0,
                                       w=1 / np.sqrt(vary),
                                       ext=extrapMethod)
    
            # Append results to class field splines
            self.splines.append({'xS': xSpline,
                                 'yS': ySpline})
    
    def plotBeads(self, curveNumber=None):
        """Make a plot of each bead's z-stack and the average spline fit.

        plotBeads allows the user to check the individual beads and
        their fits against the average spline fit.

        Parameters
        ----------
        curveNumber : int
            Index of the spline to plot. (0-index)

        """
        coordCols = [
            self.zCol, 
            self.sigmaCols[0],
            self.sigmaCols[1]
        ]
        horizontalLabels = ['', 'z-position']
        verticalLabels = ['x', 'y']
        title = 'Avg. spline and bead'
        splineCols = ['z', 'xS', 'yS']
        
        
        # Set the y-axis based on the average spline
        minxy, maxxy = self.avgSpline['xS'].min(), self.avgSpline['xS'].max()
        minyy, maxyy = self.avgSpline['yS'].min(), self.avgSpline['yS'].max()
        minxy -= 50
        maxxy += 50
        minyy -= 50
        maxyy += 50
        ylims = [minxy, maxxy, minyy, maxyy]

        if curveNumber is None:
            # Plot all trajectories and splines
            startIndex = 0
            stopIndex = len(self.splines)
        else:
            # Plot only the input trajectory and spline
            startIndex = curveNumber
            stopIndex  = curveNumber + 1

        offsets=[0,0] # No offsets for these plots
        for fid in range(startIndex, stopIndex):
            locs = self.regionLocs.xs(fid, level='region_id', drop_level=False)
            locs = locs.loc[locs[self._includeColName]]
            
            if self.zeroz is not None:
                offsets = self._computeOffsets(locs)
            else:
                offsets = (0, 0)
            
            self._plotCurves(fid, coordCols, horizontalLabels,
                             verticalLabels, title, splineCols,
                             offsets, ylims)
        
    def _removeOutliers(self, startz, stopz):
        """
        Removes localizations lying outside the z-fitting range.

        Parameters
        ----------
        startz : float
        stopz  : float
        
        """
        z = self.zCol
        self.regionLocs[self._includeColName] = True
        self.regionLocs.loc[
                (self.regionLocs[z] < startz) | (self.regionLocs[z] > stopz),
                 self._includeColName
        ] = False
    
    def reset(self):
        """Resets the astigmatism computer to its initial state.
    
        """
        self.coordCols           = self._init_coordCols.copy()
        self.sigmaCols           = self._init_sigmaCols.copy()
        self.zCol                = self._init_zCol
        self.smoothingWindowSize = self._init_smoothingWindowSize
        self.smoothingFilterSize = self._init_smoothingFilterSize
        self.useTrajectories     = self._init_useTrajectories.copy()
        self.startz              = self._init_startz
        self.stopz               = self._init_stopz
        self.zeroz               = self._init_zeroz

class DefaultDriftComputer(ComputeTrajectories):
    """The default algorithm for computing a drift trajectory.

    The default drift computer fits a cubic smoothing spline to
    localizations from fiducial regions and averages the splines from multiple
    fiducials. It allows users to set the frame where the trajectories are
    equal to zero in x and y, to adjust the smoothing window parameters, and
    to select what trajectories are used to compute the final trajectory that
    is stored inside the avgSpline attribute.

    Parameters
    ----------
    coordCols           : list str
        List of strings identifying the x- and y-coordinate column names
        in that order.
    frameCol            : str
        Name of the column identifying the column containing the frames.
    maxRadius           : float
        The maximum distance that a localization may lie from the center of
        a cluster of fiducial localizations; localizations farther than this
        distance are not included in the fit. Set to None to include all
        fiducials. Units are the same as in coordCols.
    smoothingWindowSize : float
        Moving average window size in frames for spline fitting.
    smoothingFilterSize : float
        Moving average Gaussian kernel width in frames for spline fitting.
    useTrajectories     : list of int
        List of integers corresponding to the fiducial trajectories to use
        when computing the average trajectory. If empty, all trajectories
        are used.
    zeroFrame           : int
        Frame where all individual drift trajectories are equal to zero.
        This may be adjusted to help correct fiducial trajectories that
        don't overlap well near the beginning.

    Attributes
    ----------
    avgSpline           : Pandas DataFrame
        DataFrame with 'frame' index column and 'xS' and 'yS' position
        coordinate columns representing the drift of the sample during the
        acquisition.
    coordCols           : list str
        List of strings identifying the x- and y-coordinate column names
        in that order.
    regionLocs        : Pandas DataFrame
        DataFrame with a 'region_id' column denoting localizations from
        different regions of the original dataset. This is created by the
        parent ComputeTrajectories class.
    frameCol            : str
        Name of the column identifying the column containing the frames.
    maxRadius           : float
        The maximum distance that a localization may lie from the center of
        a cluster of fiducial localizations; localizations farther than this
        distance are not included in the fit. Set to None to include all
        fiducials. Units are the same as in coordCols.
    smoothingWindowSize : float
        Moving average window size in frames for spline fitting.
    smoothingFilterSize : float
        Moving average Gaussian kernel width in frames for spline fitting.
    splines             : list of dict of 2x UnivariateSpline, 2x int
        Individual splines fit to the fiducial trajectories. Key names are
        'xS', 'yS', 'minFrame', and 'maxFrame'.
    useTrajectories : list of int or empty list
        List of integers corresponding to the fiducial trajectories to use
        when computing the average trajectory. If [], all trajectories
        are used.
    zeroFrame       : int
        Frame where all individual drift trajectories are equal to zero.
        This may be adjusted to help correct fiducial trajectories that
        don't overlap well near the beginning.

    """

    def __init__(self, coordCols=['x', 'y'], frameCol='frame',
                 maxRadius=None, smoothingWindowSize=600,
                 smoothingFilterSize=400, useTrajectories=[],
                 zeroFrame=1000):

        self.coordCols = coordCols
        self.frameCol = frameCol
        self.maxRadius = maxRadius
        self.smoothingWindowSize = smoothingWindowSize
        self.smoothingFilterSize = smoothingFilterSize
        self.useTrajectories = useTrajectories
        self.zeroFrame = zeroFrame
        super(ComputeTrajectories, self).__init__()
        
        # Column of DataFrame used to indicate what localizations are not
        # included in a trajectory for a spline fit, e.g. outliers
        self._includeColName = 'included_in_trajectory'

        # initial state
        self._init_coordCols = coordCols.copy()
        self._init_frameCol = frameCol
        self._init_maxRadius = maxRadius
        self._init_smoothingWindowSize = smoothingWindowSize
        self._init_smoothingFilterSize = smoothingFilterSize
        self._init_useTrajectories = useTrajectories.copy()
        self._init_zeroFrame = zeroFrame

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
        frames = np.arange(startFrame, stopFrame + 1, 1)
        numSplines = len(self.splines)

        # Evalute each x and y spline at every frame position
        fullRangeSplines = {'xS': np.array([self.splines[i]['xS'](frames)
                                            for i in range(numSplines)]),
                            'yS': np.array([self.splines[i]['yS'](frames)
                                            for i in range(numSplines)])}

        # Create the mask area if only certain fiducials are to be averaged
        if not self.useTrajectories:
            mask = np.arange(numSplines)
        else:
            mask = self.useTrajectories

        # Compute the average over spline values
        avgSpline = {'xS': [], 'yS': []}

        try:
            for key in avgSpline.keys():
                avgSpline[key] = np.mean(fullRangeSplines[key][mask], axis=0)
        except IndexError:
            raise UseTrajectoryError(
                'At least one of the indexes inside '
                'useTrajectories does not match a known fiducial '
                'index. The maximum fiducial index is {0:d}.'
                ''.format(
                    numSplines - 1))

        # Append frames to avgSpline
        avgSpline['frame'] = frames

        self.avgSpline = pd.DataFrame(avgSpline)

    def computeTrajectory(self, regionLocs, startFrame, stopFrame):
        """Computes the final drift trajectory from fiducial localizations.

        Parameters
        ----------
        regionLocs    : Pandas DataFrame
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
        computeTrajectory() requires the start and stop frames
        because the fiducial localizations may not span the full range
        of frames in the dataset.

        """
        self.clearRegionLocs()
        self.regionLocs = regionLocs
        self._removeOutliers()
        self.fitCurves()
        self.combineCurves(startFrame, stopFrame)

        return self.avgSpline

    def _computeOffsets(self, locs):
        """Compute the offsets for fiducial trajectories based on zeroFrame.

        Parameters
        ----------
        locs : Pandas DataFrame
            Localizations from a single fiducial region.

        Returns
        -------
        x0, y0 : tuple of int
            The offsets to subtract from the localizations belonging to a
            fiducial.

        """
        avgOffset = 50
        x, y = self.coordCols[0], self.coordCols[1]
        startFrame, stopFrame = locs[self.frameCol].min(), \
            locs[self.frameCol].max()

        if self.zeroFrame > stopFrame or self.zeroFrame < startFrame:
            warnings.warn(('Warning: zeroFrame ({0:d}) is outside the '
                           'allowable range of frame numbers in this dataset '
                           '({1:d} - {2:d}). Try a different zeroFrame value'
                           'by adjusting driftComputer.zeroFrame.'
                           ''.format(self.zeroFrame, startFrame + avgOffset,
                                     stopFrame - avgOffset)))

        # Average the localizations around the zeroFrame value
        x0 = locs[(locs[self.frameCol] > self.zeroFrame - avgOffset)
                & (locs[self.frameCol] < self.zeroFrame + avgOffset)][x].mean()
        y0 = locs[(locs[self.frameCol] > self.zeroFrame - avgOffset)
                & (locs[self.frameCol] < self.zeroFrame + avgOffset)][y].mean()

        if (x0 is np.nan) or (y0 is np.nan):
            warnings.warn('Could not determine an offset value; '
                          'setting offsets to zero.')
            x0, y0 = 0, 0

        return x0, y0

    def fitCurves(self):
        """Fits individual splines to each fiducial.

        """
        print('Performing spline fits...')
        # Check whether fiducial trajectories already exist
        if self.regionLocs is None:
            raise ZeroRegions('Zero fiducials are currently saved '
                                'with this processor.')

        self.splines = []
        regionIDIndex = self.regionLocs.index.names.index('region_id')
        x = self.coordCols[0]
        y = self.coordCols[1]
        frameID = self.frameCol

        # fid is an integer
        for fid in self.regionLocs.index.levels[regionIDIndex]:
            # Get localizations from inside the current region matching fid
            # and that passed the _removeOutliers() step
            currRegionLocs = self.regionLocs.xs(
                fid, level='region_id', drop_level=False)

            # Use only those fiducials within a certain radius of the
            # cluster of localization's center of mass
            currRegionLocs = currRegionLocs.loc[
                currRegionLocs[self._includeColName]]

            maxFrame = currRegionLocs[frameID].max()
            minFrame = currRegionLocs[frameID].min()

            windowSize = self.smoothingWindowSize
            sigma = self.smoothingFilterSize

            # Shift the localization(s) at zeroFrame to (x = 0, y = 0) by
            # subtracting its value at frame number zeroFrame
            x0, y0 = self._computeOffsets(currRegionLocs)

            # Determine the appropriate weighting factors
            _, varx = self._movingAverage(currRegionLocs[x] - x0,
                                          windowSize=windowSize,
                                          sigma=sigma)
            _, vary = self._movingAverage(currRegionLocs[y] - y0,
                                          windowSize=windowSize,
                                          sigma=sigma)

            # Perform spline fits. Extrapolate using boundary values (const)
            extrapMethod = 'const'
            xSpline = UnivariateSpline(currRegionLocs[frameID].as_matrix(),
                                       currRegionLocs[x].as_matrix() - x0,
                                       w=1 / np.sqrt(varx),
                                       ext=extrapMethod)
            ySpline = UnivariateSpline(currRegionLocs[frameID].as_matrix(),
                                       currRegionLocs[y].as_matrix() - y0,
                                       w=1 / np.sqrt(vary),
                                       ext=extrapMethod)

            # Append results to class field splines
            self.splines.append({'xS': xSpline,
                                 'yS': ySpline,
                                 'minFrame': minFrame,
                                 'maxFrame': maxFrame})

    def plotFiducials(self, curveNumber=None):
        """Make a plot of each fiducial track and the average spline fit.

        plotFiducials allows the user to check the individual fiducial tracks
        against the average spline fit.

        Parameters
        ----------
        curveNumber : int
            Index of the spline to plot. (0-index)

        """
        coordCols = [
            self.frameCol,
            self.coordCols[0],
            self.coordCols[1]
        ]
        horizontalLabels = ['', 'Frame number']
        verticalLabels   = ['x-position', 'y-position']
        title            = 'Avg. spline and fiducial'
        splineCols       = ['frame', 'xS', 'yS']
        
        # Set the y-axis based on the average spline
        minxy, maxxy = self.avgSpline['xS'].min(), self.avgSpline['xS'].max()
        minyy, maxyy = self.avgSpline['yS'].min(), self.avgSpline['yS'].max()
        minxy -= 50
        maxxy += 50
        minyy -= 50
        maxyy += 50
        ylims  = [minxy, maxxy, minyy, maxyy]
        
        if curveNumber is None:
            # Plot all trajectories and splines
            startIndex = 0
            stopIndex  = len(self.splines)
        else:
            # Plot only the input trajectory and spline
            startIndex = curveNumber
            stopIndex  = curveNumber + 1

        for fid in range(startIndex, stopIndex):
            locs = self.regionLocs.xs(fid, level='region_id', drop_level=False)

            # Filter out localizations that are outliers and find
            # offsets
            locs = locs.loc[locs[self._includeColName]]
            offsets = self._computeOffsets(locs)

            self._plotCurves(fid, coordCols, horizontalLabels,
                             verticalLabels, title, splineCols,
                             offsets, ylims)

    def _removeOutliers(self):
        """Removes outlier localizations from fiducial tracks before fitting.

        _removeOutliers() computes the center of mass of each cluster of
        localizations belonging to a fiducial and then removes localizations
        lying farther than self.maxRadius from this center.

        """
        x = self.coordCols[0]
        y = self.coordCols[1]
        self.regionLocs[self._includeColName] = True

        maxRadius = self.maxRadius
        if not maxRadius:
            return

        # Change the region_id from an index to a normal column
        self.regionLocs.reset_index(level='region_id', inplace=True)
        groups = self.regionLocs.groupby('region_id')
        temp = []
        for _, group in groups:
            # Make a copy to avoid the warning about modifying slices
            group = group.copy()

            # Subtract the center of mass and filter by distances
            xc, yc = group.loc[:, [x, y]].mean()
            dfc = pd.concat(
                [group[x] - xc, group[y] - yc], axis=1)
            distFilter = dfc[x]**2 + dfc[y]**2 > maxRadius**2
            group.loc[distFilter, self._includeColName] = False
            temp.append(group)

        # Aggregate the filtered groups, reset the index, then recreate
        # self.regionLocs with the filtered localizations
        temp = pd.concat(temp)
        temp.set_index(
            ['region_id'], append=True, inplace=True)
        self.regionLocs = temp

    def reset(self):
        """Resets the drift computer to its initial state.

        """
        self.coordCols = self._init_coordCols.copy()
        self.frameCol = self._init_frameCol
        self.maxRadius = self._init_maxRadius
        self.smoothingWindowSize = self._init_smoothingWindowSize
        self.smoothingFilterSize = self._init_smoothingFilterSize
        self.useTrajectories = self._init_useTrajectories.copy()
        self.zeroFrame = self._init_zeroFrame


class FiducialDriftCorrect(DriftCorrect, SelectLocalizations):
    """Correct localizations for lateral drift using fiducials.

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

    Attributes
    ----------
    driftComputer     : ComputeTrajectories
        The algorithm for determining trajectories from fiducials.
    interactiveSearch : bool
        Should a window open allowing the user to identify fiducials when this
        processor is called?

    """
    _correctorType = 'FiducialDriftCorrect'

    def __init__(self, interactiveSearch=True, coordCols=['x', 'y'],
                 frameCol='frame', removeFiducials=True,
                 driftComputer=None):
        # Assign class properties based on input arguments
        self.interactiveSearch = interactiveSearch
        self._coordCols = coordCols
        self._frameCol = frameCol
        self._removeFiducials = removeFiducials

        if driftComputer:
            self.driftComputer = driftComputer
        else:
            self.driftComputer = DefaultDriftComputer(coordCols=coordCols,
                                                      frameCol=frameCol)

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
                regionLocs = self._extractLocsFromRegions(df)
            except ZeroFiducialRegions:
                print('No regions with fiducials identified. '
                      'Returning original DataFrame.')
                # Ensure any localizations are cleared from the drift computer
                self.driftComputer.clearRegionLocs()
                return df
        else:
            # If the interactive search was set to false, then the drift
            # corrector has already been called and the regions saved in the
            # drift computer. Read them back from the computer instead of
            # looking for them again in the raw localizations.
            regionLocs = self.driftComputer.regionLocs

        # Add clustering of localizations here if needed

        # Remove localizations inside the search regions from the DataFrame
        if self._removeFiducials:
            # Removes rows from the df DataFrame that have the same index rows
            # in regionLocs. This relies on all functions preceding this
            # line to not modify the index column of the input df.
            procdf = df[~df.index.isin(regionLocs.index.levels[0])]
        else:
            procdf = df

        # Compute the final drift trajectory
        frames = self._frameCol
        startFrame = procdf[frames].min()
        stopFrame = procdf[frames].max()
        self.driftTrajectory = \
            self.driftComputer.computeTrajectory(regionLocs,
                                                 startFrame,
                                                 stopFrame)

        procdf = self.correctLocalizations(procdf)

        return procdf

    @property
    def correctorType(self):
        return self._correctorType

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
        
        # Change frame to an index
        driftTrajectory = self.driftComputer.avgSpline.set_index(keys='frame')

        xc = driftTrajectory.lookup(corrdf.frame, ['xS'] * corrdf.frame.size)
        yc = driftTrajectory.lookup(corrdf.frame, ['yS'] * corrdf.frame.size)

        corrdf['dx'] = xc
        corrdf['dy'] = yc
        corrdf[x] = corrdf[x] - xc
        corrdf[y] = corrdf[y] - yc

        return corrdf

    def readSettings(self):
        # TODO
        raise(NotImplementedError)

    def writeSettings(self):
        # TODO
        raise(NotImplementedError)


class Filter:
    """Processor for filtering DataFrames containing localizations.

    A filter processor works by selecting a dolumn of the input DataFrame and
    creating a logical mask by applying the operator and parameter to each
    value in the column. Rows that correspond to a value for 'False' in the
    mask are removed from the DataFrame.

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

    _operatorMap = {'<': lt,
                    '<=': le,
                    '==': eq,
                    '!=': ne,
                    '>=': ge,
                    '>': gt}

    def __init__(self, columnName, operator, filterParameter, resetIndex=True):

        try:
            self._operator = self._operatorMap[operator]
        except KeyError:
            print('Error: {:s} is not a recognized operator.'.format(operator))
            raise KeyError

        self._columnName = columnName
        self._filterParameter = filterParameter
        self._resetIndex = resetIndex

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
            procdf = df[self._operator(
                df[self._columnName], self._filterParameter)].reset_index(drop=True)
        else:
            procdf = df[self._operator(df[self._columnName],
                                       self._filterParameter)]

        return procdf


class Merge:
    """Merges nearby localizations in subsequent frames into one localization.

    The merge radius is the distance around a localization that another
    localization must be in space for the two to become merged. The off
    time is the maximum number of frames that a localization can be absent
    from before the its track in time is terminated.

    Parameters
    ----------
    autoFindMergeRadius : bool (default: False)
        If True, this will set the merge radius to three times the mean
        localization precision in the dataset.
    coordCols           : list of str
        List of strings identifying the x- and y-coordinate column names
        in that order.
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

    Attributes
    ----------
    autoFindMergeRadius : bool (default: False)
        If True, this will set the merge radius to three times the mean
        localization precision in the dataset.
    coordCols           : list of str
        List of strings identifying the x- and y-coordinate column names
        in that order.
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

    def __init__(self,
                 tOff=1,
                 mergeRadius=50,
                 autoFindMergeRadius=False,
                 statsComputer=None,
                 precisionColumn='precision',
                 coordCols=['x', 'y']):

        self.autoFindMergeRadius = autoFindMergeRadius
        self.tOff = tOff
        self.mergeRadius = mergeRadius
        self.statsComputer = statsComputer
        self.precisionColumn = precisionColumn
        self.coordCols = coordCols

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
        if self.autoFindMergeRadius:
            mergeRadius = 3 * df[self.precisionColumn].mean()
        else:
            mergeRadius = self.mergeRadius

        # Track individual localization trajectories
        dfTracked = tp.link_df(df, mergeRadius, memory=self.tOff,
                               pos_columns=self.coordCols)

        # Compute the statistics for each group of localizations
        if self.statsComputer:
            # Return a DataFrame containing merged statistics
            procdf = self.statsComputer.computeStatistics(dfTracked)
        else:
            # Return the original DataFrame with a new particle id column
            procdf = dfTracked

        return procdf


class MergeFang(MergeStats):
    """Merger for localizations computed from Fang's sCMOS MLE software.

    """

    def computeStatistics(self, df, particleCol='particle'):
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
        particleGroups = df.groupby(particleCol)

        tempResultsX = particleGroups.apply(self._wAvg, 'x')
        tempResultsY = particleGroups.apply(self._wAvg, 'y')
        tempResultsZ = particleGroups.apply(self._wAvg, 'z')
        tempResultsMisc = particleGroups.agg({'loglikelihood': 'mean',
                                              'frame': 'min',
                                              'photons': 'sum',
                                              'background': 'sum',
                                              'sigma': 'mean'})
        tempResultsLength = pd.Series(particleGroups.size())

        # Rename the series
        tempResultsX.name = 'x'
        tempResultsY.name = 'y'
        tempResultsZ.name = 'z'
        tempResultsLength.name = 'length'

        # Create the merged DataFrame
        dataToJoin = (tempResultsX,
                      tempResultsY,
                      tempResultsZ,
                      tempResultsMisc,
                      tempResultsLength)
        procdf = pd.concat(dataToJoin, axis=1)

        # Move the particle ID to a regular column
        procdf.reset_index(particleCol, inplace=True)

        return procdf


class MergeFangTS(MergeStats):
    """Merger for localizations computed from Fang's sCMOS MLE software.

    This computer is for DataFrames in the ThunderSTORM column format.

    """

    def computeStatistics(self, df, particleCol='particle'):
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
        particleGroups = df.groupby(particleCol)

        wAvg = lambda x, y: self._wAvg(x, y, photonsCol='intensity [photon]')

        tempResultsX = particleGroups.apply(wAvg, 'x [nm]')
        tempResultsY = particleGroups.apply(wAvg, 'y [nm]')
        tempResultsZ = particleGroups.apply(wAvg, 'z [nm]')
        tempResultsMisc = particleGroups.agg({'loglikelihood': 'mean',
                                              'frame': 'min',
                                              'intensity [photon]': 'sum',
                                              'offset [photon]': 'sum',
                                              'sigma [nm]': 'mean'})
        tempResultsLength = pd.Series(particleGroups.size())

        # Rename the series
        tempResultsX.name = 'x [nm]'
        tempResultsY.name = 'y [nm]'
        tempResultsZ.name = 'z [nm]'
        tempResultsLength.name = 'length'

        # Create the merged DataFrame
        dataToJoin = (tempResultsX,
                      tempResultsY,
                      tempResultsZ,
                      tempResultsMisc,
                      tempResultsLength)
        procdf = pd.concat(dataToJoin, axis=1)

        # Move the particle ID to a regular column
        procdf.reset_index(particleCol, inplace=True)

        return procdf
    

"""Exceptions
-------------------------------------------------------------------------------
"""


class UseTrajectoryError(Exception):
    """Raised when drift computer has invalid indexes to fiducial trajectories.

    """

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class ZeroRegions(Exception):
    """Raised when zero regions are present during trajectory computation.

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
