# © All rights reserved. ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Switzerland, Laboratory of Experimental Biophysics, 2016
# See the LICENSE.txt file for more details.

"""Process multiple inputs from a SMLM experiment.

A multiprocessor is similar to a processor except that it takes more than just
one  DataFrame as its input. Multiprocessors can, for example, take multiple
DataFrames, such as localizations in multiple channels, widefield images, etc.

"""

import numpy             as np
import matplotlib.pyplot as plt
from bstore import processors as proc
from scipy.signal import fftconvolve
from scipy.ndimage import zoom

class AlignToWidefield:
    """Aligns localizations to a corresponding widefield image.
    
    AlignToWidefield is a multiprocessor that estimates by how much a
    set of localizations is shifted relative to a corresponding
    widefield image. It works by computing a 2D histogram from the
    localizations and cross-correlating it with an upsampled version of
    the widefield image. The result is a two-element tuple of the
    estimated shifts in units of the x- and y-localization
    coordinates.
    
    The cross-correlation is performed using fftconvolve from
    scipy.signal; this means it is an estimate of the global offset
    between the 2D histogram and the widefield image. Small, field-
    dependent deviations between the localizations and widefield
    image should therefore be expected.
    
    Parameters
    ----------
    coordCols      : list of str
        The x- and y-coordinate column labels.
    pixelSize      : float
        The linear size of a pixel in the same units at the localizations.
    upsampleFactor : int
        The amount of upsampling to perform on the widefield image. For
        example, a factor of 5 means 1 pixel is transformed into 5.
    
    Attributes
    ----------
    coordCols      : list of str
        The x- and y-coordinate column labels.
    pixelSize      : float
        The linear size of a pixel in the same units at the localizations.
    upsampleFactor : int
        The amount of upsampling to perform on the widefield image. For
        example, a factor of 5 means 1 pixel is transformed into 5.

    """
    def __init__(self, coordCols = ['x', 'y'], pixelSize = 108.0,
                 upsampleFactor = 5):
        self.coordCols      = coordCols
        self.pixelSize      = pixelSize
        self.upsampleFactor = upsampleFactor
        
    def __call__(self, locs, wfImage):
        """Align a set of localizations to a widefield image.
        
        Parameters
        ----------
        locs    : Pandas DataFrame
            The DataFrame containing the localizations. x- and y-column
            labels are specified in self.coordCols.
        wfImage : array of int or array of float 
            The widefield image to align the localizations to.
        
        Returns
        -------
        offsets : tuple of float
            The estimated offset between the localizations and widefield
            image. The first element is the offset in x and the second
            in y. These should be subtracted from the input localizations
            to align them to the widefield image.
            
        """
        upsampleFactor = self.upsampleFactor
        
        # Bin the localizations into a 2D histogram;
        # x corresponds to rows for histogram2d
        binsX = np.arange(0, upsampleFactor * wfImage.shape[0] + 1, 1) \
                                            * self.pixelSize / upsampleFactor
        binsY = np.arange(0, upsampleFactor * wfImage.shape[1] + 1, 1) \
                                            * self.pixelSize / upsampleFactor
        H, _, _ = np.histogram2d(locs[self.coordCols[0]],
                                 locs[self.coordCols[1]],
                                 bins = [binsX, binsY])
                           
        # Upsample and flip the image to align it to the histogram;
        # then compute the cross correlation
        crossCorr = fftconvolve(H,
                                zoom(np.transpose(wfImage)[::-1, ::-1], 
                                     upsampleFactor, order = 0),
                                mode = 'same')
        
        # Find the maximum of the cross correlation
        centerLoc = np.unravel_index(np.argmax(crossCorr), crossCorr.shape)

        # Find the center of the widefield image
        imgCorr = fftconvolve(zoom(np.transpose(wfImage)[::-1, ::-1], 
                                   upsampleFactor, order = 0),
                              zoom(np.transpose(wfImage)[::-1, ::-1], 
                                   upsampleFactor, order = 0),
                              mode = 'same')
        centerWF = np.unravel_index(np.argmax(imgCorr), imgCorr.shape)
                              
        # Find the shift between the images.
        # dx -> rows, dy -> cols because the image was transposed during
        # fftconvolve operation.
        dy = (centerLoc[1] - centerWF[1]) / upsampleFactor * self.pixelSize
        dx = (centerLoc[0] - centerWF[0]) / upsampleFactor * self.pixelSize
        
        offsets = (dx, dy)
        return offsets
    
class OverlayClusters:
    """Produces overlays of clustered localizations on widefield images.
    
    The OverlayClusters processor is used to overlay  clustered localizations
    onto widefield images. It shows both the full image and a zoomed region
    around the current cluster at the same time. The user can interactively
    step through each cluster with the keyboard.
    
    It also allows for annotating clusters by labeling clusters with a numeric
    ID between 0 and 9 or a True/False value, allowing for users to perform
    manual filtering or segmentation, for example.
    
    """
    def __init__(self,
                 annotateCol     = None,
                 clusterIDCol    = 'cluster_id',
                 coordCols       = ['x', 'y'],
                 coordCenterCols = ['x_center', 'y_center'],
                 filterCol       = None,
                 pixelSize       = 108,
                 zoomSize        = 21):
                     
        """Setup the OverlayClusters processor.
        
        Parameters
        ----------
        annotateCol    : str
            Name of the column in stats for deciding whether a cluster is
            retained for analysis.
        clusterIDCol   : str
            Name of the column containing the cluster id number.
        coordCols      : list of str
            The x- and y-coordinate column labels.
        filterCol      : str
            The name of a column containing boolean data in the 'stats'
            DataFrame. Only rows with a value of True in this column will be
            displayed.
        pixelSize      : float
            The physical size of a pixel. For converting the localization units
            to pixels.
        zoomSize       : int
            The linear size of the zoomed region around a cluster in pixels.
            
        """
        self.annotateCol     = annotateCol
        self.clusterIDCol    = clusterIDCol
        self.coordCols       = coordCols
        self.coordCenterCols = coordCenterCols
        self.filterCol       = filterCol
        self._pixelSize      = pixelSize
        self._zoomSize       = zoomSize
        
        # Holds information on the current cluster being analyzed
        self._currentClusterIndex = 0
        self.currentCluster       = []
        self.clusterIDs           = []
        
        # Holds information on the current figure
        self._fig           = None
        self._ax0           = None
        self._ax1           = None
        self._clusterLocs   = None
    
    def __call__(self, locs, stats = None, wfImage = None):
        """Overlay the localizations onto the widefield image.
        
        This opens an interactive matplotlib window that shows the full overlay
        and a zoomed region around a particular cluster. The user may use the
        keyboard to go forward and backward through the clusters.
        
        Parameters
        ----------
        locs         : DataFrame
            A Pandas DataFrame object containing the localizations.
        stats        : Pandas DataFrame
            DataFrame containing at least two columns: one for the cluster
            center x-coordinates and one for the y-coordinates. This DataFrame
            will be computed if none is provided. (The cluster centers are
            used for plotting, so these stats need to be computed.)
        wfImage    : Numpy Array
            Allows the user to specify the wfImage
            
        Returns
        -------
        procdf : DataFrame
            A DataFrame object with the merged localizations.
            
        """
        centerNameTemp = None
        if stats is None:
            # Compute the cluster statistics if none were provided.
            statsComp = proc.ComputeClusterStats(idLabel = self.clusterIDCol,
                                                 coordCols = self.coordCols)
            stats     = statsComp(locs)
            
            # Ignore the filter and annotate columns
            self.filterCol   = None            
            self.annotateCol = None
            
            # Override the center coordinate column names
            centerSuffix = statsComp.centerName
            x, y         = self.coordCols[0], self.coordCols[1]
            centerNameTemp       = self.coordCenterCols
            self.coordCenterCols = [x + centerSuffix, y + centerSuffix]
        
        # Ensure that the localizations are already clustered
        assert self.clusterIDCol in locs, \
               ('Error: No cluster ID column found in localization DataFrame. '
                'Searched for column name '
                '\' {0:s} \'.'.format(self.clusterIDCol))
        
        # Find the cluster ID information
        self._extractClusterID(stats)     
        
        # Draw the localizations in the figure
        self._initCanvas(locs, wfImage, stats)
        
        # Attach the keyboard monitor to the figure
        def onClose(event):
            """Run when the figure closes.
            
            """
            self._fig.canvas.stop_event_loop()
            
        def keyMonitor(event, processor):
            """Handles user input.
            
            """
            if event.key in ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0']:
                if self.annotateCol is not None:                
                    # Add a numeric label to the cluster
                    stats.loc[self.currentCluster, self.annotateCol] = \
                                                                 int(event.key)
                    self._currentClusterIndex += 1
                    self._drawCurrentCluster(locs)
            
            if event.key in ['b', 'B']:
                # Go back one cluster.
                if self._currentClusterIndex != 0:
                    self._currentClusterIndex -= 1
                    self._drawCurrentCluster(locs)
            
            if event.key in ['g', 'G']:
                # Go forward one cluster
                if self._currentClusterIndex != len(self.clusterIDs) - 1:
                    self._currentClusterIndex +=1
                    self._drawCurrentCluster(locs)
            
            if event.key in [' ']:
                if self.annotateCol is not None:
                    # Set annotateCol to True for this cluster
                    # and go to the next.
                    stats.loc[self.currentCluster, self.annotateCol] = True
                    self._currentClusterIndex += 1
                    self._drawCurrentCluster(locs)
                
            if event.key in ['r', 'R']:
                if self.annotateCol is not None:
                    # Set switchColumn to True for this cluster
                    # and go to the next.
                    stats.loc[self.currentCluster, self.annotateCol] = False
                    self._currentClusterIndex += 1
                    self._drawCurrentCluster(locs)
                
        self._fig.canvas.mpl_connect('close_event', onClose)
        plt.connect('key_press_event',
                    lambda event: keyMonitor(event, self))
        self._fig.canvas.start_event_loop_default()
        
        if centerNameTemp:
            # Reset the center names to the value that was overridden
            self.coordCenterCols = centerNameTemp
        
    def _drawCurrentCluster(self, locs):
        """Draws the current cluster onto the figure.
        
        """
        x, y = self.coordCols[0], self.coordCols[1]
        
        # Check for end of clusters
        if self._currentClusterIndex >= len(self.clusterIDs):
            plt.close(self._fig)
            return None
        
        self.currentCluster = self.clusterIDs[self._currentClusterIndex]
        ax1          = self._ax1
        zoomHalfSize = np.floor(self._zoomSize / 2)
        
        # Get the current cluster
        # Half a pixel is subtracted because matplotlib places the first
        # pixel's center at (0,0), rather than its corner.
        coords = \
            locs[locs[self.clusterIDCol] == self.currentCluster][[x, y]]
        xMean  = (coords[x].mean() / self._pixelSize) - 0.5
        yMean  = (coords[y].mean() / self._pixelSize) - 0.5
        
        # Draw the current cluster zoom to it; same half pixel shift as above
        self._clusterCenter.set_data([xMean], [yMean])
        self._clusterLocs.set_data(coords[x] / self._pixelSize - 0.5,
                                   coords[y] / self._pixelSize - 0.5)         
        ax1.set_xlim(xMean - zoomHalfSize, xMean + zoomHalfSize)
        ax1.set_ylim(yMean - zoomHalfSize, yMean + zoomHalfSize)
        ax1.set_title(('Current cluster ID: {0:d} : Index {1:d} / {2:d}'
                       ''.format((self.currentCluster),
                                 (self._currentClusterIndex) ,
                                 len(self.clusterIDs) - 1)))
        self._fig.canvas.draw()
        
    def _extractClusterID(self, stats):
        """Obtains a list of the cluster IDs.
        
        Parameters
        ----------
        stats : Pandas DataFrame
            Localization information.
            
        """
        # Get the cluster IDs except for the noise, which has ID -1, and those
        # whose 'annotateCols' are already set to false.
        if (not self.filterCol) and (not self.annotateCol):
            self.clusterIDs = stats[stats.index != -1].index.unique()
        elif not self.filterCol:
            self.clusterIDs = stats[(stats.index != -1)
            & (stats[self.annotateCol] != False)].index.unique()
        elif not self.annotateCol:
            self.clusterIDs = stats[(stats.index != -1)
            & (stats[self.filterCol] != False)].index.unique()
        else:
            self.clusterIDs = stats[(stats.index != -1)
                & (stats[self.annotateCol] != False)
                & (stats[self.filterCol] != False)].index.unique()
        self.currentCluster = np.min(self.clusterIDs)
        
    def _initCanvas(self, locs, wfImage, stats):
        """Draws the initial canvas for the localizations and other data.
        
        Parameters
        ----------
        locs    : Pandas DataFrame
            Localizations
        wfImage : 2D array of int
            The widefield image associated with the localizations.
        stats   : Pandas DataFrame
            The DataFrame containing the cluster statistics.
        
        """
        x, y      = self.coordCols[0], self.coordCols[1]
        xc, yc    = self.coordCenterCols[0], self.coordCenterCols[1]
        idCol     = self.clusterIDCol
        filterCol = self.filterCol
        
        if wfImage is None:
            centerColor = 'black'
        else:
            centerColor = 'white'
            
        if self.filterCol is None:
            plotx = stats.loc[:, xc] / self._pixelSize
            ploty = stats.loc[:, yc] / self._pixelSize
        else:
            plotx = stats.loc[stats[filterCol] != False, xc] / self._pixelSize
            ploty = stats.loc[stats[filterCol] != False, yc] / self._pixelSize    
        
        # Reset the current cluster to zero
        self._currentClusterIndex = 0
        self.currentCluster       = self.clusterIDs[self._currentClusterIndex]        
        
        # Create the figure and axes
        fig, (ax0, ax1) = plt.subplots(nrows = 1, ncols = 2)
        self._fig = fig
        self._ax0 = ax0
        self._ax1 = ax1    
        
        # Draw the cluster centers
        if wfImage is not None:
            ax0.imshow(wfImage,
                       cmap          = 'inferno',
                       interpolation = 'nearest',
                       #vmin          = np.max(wfImage) / 3,
                       vmax          = np.max(wfImage) / 2)
                       #vmax          = np.max(wfImage))

        ax0.scatter(plotx, 
                    ploty,
                    s     = 1,
                    color = centerColor)
        self._clusterCenter, = ax0.plot([],
                                        [],
                                        'oy',
                                        markersize      = 10,
                                        fillstyle       = 'none',
                                        markeredgewidth = 2.5)
        if wfImage is not None:            
            ax0.set_xlim(0, wfImage.shape[1])
            ax0.set_ylim(0, wfImage.shape[0])
        ax0.set_title('Cluster centers')
        ax0.set_xlabel('x-position, pixel')
        ax0.set_ylabel('y-position, pixel')
        ax0.set_aspect('equal')
        
        # Draw the zoomed region of the current cluster
        self._clusterLocs, = ax1.plot([], [], '.c')
        if wfImage is not None:
            ax1.imshow(wfImage,
                       cmap          = 'inferno',
                       interpolation = 'nearest',
                       #vmin          = np.max(wfImage) / 3,
                       vmax          = np.max(wfImage) / 2)
                       #vmax          = np.max(wfImage))
        # Plot unclustered localizations
        # Half a pixel is subtracted because matplotlib places the first
        # pixel's center at (0,0), rather than its corner.
        ax1.scatter(locs[locs[idCol] == -1][x] / self._pixelSize - 0.5,
                    locs[locs[idCol] == -1][y] / self._pixelSize - 0.5,
                    s = 4,
                    color = 'magenta')
        
        # Plot the cluster centers
        # Constants of 0.5 is explained a few lines above.
        ax1.scatter(plotx - 0.5,
                    ploty - 0.5,
                    s = 30,
                    color = 'green')
        ax1.set_xlabel('x-position, pixel')
        ax1.set_ylabel('y-position, pixel')
        ax1.set_aspect('equal')
        
        # Draw the initial cluster
        self._drawCurrentCluster(locs)        
        
        # Make the figure full screen
        figManager = plt.get_current_fig_manager()
        figManager.window.showMaximized()
        plt.show()