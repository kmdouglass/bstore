"""Process multiple inputs from a SMLM experiment.

A multiprocessor is similar to a processor except that it takes more than just
one  DataFrame as its input. Multiprocessors can, for example, take multiple
DataFrames, such as localizations in multiple channels, widefield images, etc.

Because each one takes different inputs that will need to be handled
differently, each will have its own batch processor associated with it.

"""
import pandas            as pd
import numpy             as np
import matplotlib.pyplot as plt
import DataSTORM.batch   as bp
import warnings

class OverlayClusters:
    """Produces overlays of clustered localizations on widefield images.
    
    The OverlayClusters processor is used to overlay localizations onto
    widefield images. It allows you to see the individual localizations and
    clusters on top of the widefield images, showing both the full image and
    a zoomed region at the same time. The user can interactively step through
    each cluster with the keyboard.
    
    It also allows for interactive processing, such as choosing to keep
    or reject clusters for analysis. For this, a secondary DataFrame whose
    index matches the clusters' numeric IDs is used. Typically, this DataFrame 
    will record the statistics for each cluster, such as the radius of
    gyration. Rejecting a cluster sets the value in the 'switchColumn' of the
    new DataFrame to False. Accepting it sets it to True.
    """
    def __init__(self,
                 switchColumn = 'keep_for_analysis',
                 pixelSize = 108,
                 zoomSize  = 21):
        """Setup the OverlayClusters processor.
        
        Parameters
        ----------
        switchColumn   : str
            Name of the column in stats for deciding whether a cluster is
            retained for analysis.
        pixelSize      : float
            The physical size of a pixel. For converting the localization units
            to pixels.
        zoomSize       : int
            The linear size of the zoomed region around a cluster in pixels.
            
        """
        self._switchColumn   = switchColumn
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
    
    def __call__(self, locs, wfImage = None, stats = None,
                 numberFilter = None, columnFilter = None):
        """Overlay the localizations onto the widefield image.
        
        This opens an interactive matplotlib window that shows the full overlay
        and a zoomed region around a particular cluster. The user may use the
        keyboard to go forward and backward through the clusters.
        
        Parameters
        ----------
        locs         : DataFrame
            A Pandas DataFrame object containing the localizations.
        wfImage    : Numpy Array
            Allows the user to specify the wfImage
        stats        : Pandas DataFrame
            Dataframe containing the statistics for each cluster.
        numberFilter : int
            Remove clusters with fewer than this number of localizations from
            the processing. They will automatically have their 'switchColumn'
            set to False.
        columnFilter : str
            The name of a column containing boolean data. Only rows with a
            value of True in this column will be displayed.
            
        Returns
        -------
        procdf : DataFrame
            A DataFrame object with the merged localizations.
            
        """
        # Ensure that the localizations are already clustered
        assert 'cluster_id' in locs, \
               'Error: No cluster ID column found in localization DataFrame. Searched for column name \'cluster_id\'.'
        assert self._switchColumn in stats, \
                'Error: No switchColumn found in statistics DataFrame. Searched for column name \'{0:s}\'.'.format(self._switchColumn)

        # Apply the initial filter to the data
        if numberFilter is not None:
            # A slice of the localization DataFrame is made here;
            # The original is not overwritten.
            stats.loc[stats['number_of_localizations'] <= numberFilter, self._switchColumn] = False
        
        # Apply the column filter, if it exists
        if columnFilter is not None:
            stats.loc[stats[columnFilter] == False, self._switchColumn] = False
        
        # Find the cluster ID information
        self._extractClusterID(stats, columnFilter)     
        
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
                # Add a numeric label to the cluster
                stats.loc[self.currentCluster, self._switchColumn] = \
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
                # Set switchColumn to True for this cluster and go to the next.
                stats.loc[self.currentCluster, self._switchColumn] = True
                self._currentClusterIndex += 1
                self._drawCurrentCluster(locs)
                
            if event.key in ['r', 'R']:
                # Set switchColumn to True for this cluster and go to the next.
                stats.loc[self.currentCluster, self._switchColumn] = False
                self._currentClusterIndex += 1
                self._drawCurrentCluster(locs)
                
        self._fig.canvas.mpl_connect('close_event', onClose)
        plt.connect('key_press_event',
                    lambda event: keyMonitor(event, self))
        self._fig.canvas.start_event_loop_default()
        
    def _drawCurrentCluster(self, locs):
        """Draws the current cluster onto the figure.
        
        """
        # Check for end of clusters
        if self._currentClusterIndex >= len(self.clusterIDs):
            plt.close(self._fig)
            return None
        
        self.currentCluster = self.clusterIDs[self._currentClusterIndex]
        ax1          = self._ax1
        zoomHalfSize = np.floor(self._zoomSize / 2)
        
        # Get the current cluster
        coords = locs[locs['cluster_id'] == self.currentCluster][['x', 'y']]
        xMean  = coords['x'].mean() / self._pixelSize
        yMean  = coords['y'].mean() / self._pixelSize
        
        # Draw the current cluster zoom to it
        self._clusterCenter.set_data([xMean], [yMean])
        self._clusterLocs.set_data(coords['x'] / self._pixelSize,
                                   coords['y'] / self._pixelSize)         
        ax1.set_xlim(xMean - zoomHalfSize, xMean + zoomHalfSize)
        ax1.set_ylim(yMean - zoomHalfSize, yMean + zoomHalfSize)
        ax1.set_title('Current cluster ID: {0:d} : Index {1:d} / {2:d}'.format((self.currentCluster), (self._currentClusterIndex) , len(self.clusterIDs) - 1))
        self._fig.canvas.draw()
        
    def _extractClusterID(self, stats, columnFilter):
        """Obtains a list of the cluster IDs.
        
        Parameters
        ----------
        stats : Pandas DataFrame
            Localization information.
        columnFilter : str
            The name of a column containing boolean data. Only rows with a
            value of True in this column will be analyzed.
            
        """
        # Get the cluster IDs except for the noise, which has ID -1, and those
        # whose 'switchColumns' are already set to false.
        if not columnFilter:
            self.clusterIDs     = stats[(stats.index != -1)
                                      & (stats[self._switchColumn] != False)].index.unique()
        else:
            self.clusterIDs     = stats[(stats.index != -1)
                                      & (stats[self._switchColumn] != False)
                                      & (stats[columnFilter]       != False)].index.unique()
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
        # Reset the current cluster to zero
        self._currentClusterIndex = 0
        self.currentCluster       = self.clusterIDs[self._currentClusterIndex]        
        
        # Create the figure and axes
        fig, (ax0, ax1) = plt.subplots(nrows = 1, ncols = 2)
        self._fig = fig
        self._ax0 = ax0
        self._ax1 = ax1    
        
        # Draw the cluster centers
        ax0.imshow(wfImage,
                   cmap          = 'inferno',
                   interpolation = 'nearest',
                   #vmin          = np.max(wfImage) / 6,
                   vmax          = np.max(wfImage) / 2)
                   #vmax          = np.max(wfImage) / 25)
        ax0.scatter(stats.loc[stats['keep_for_analysis'] != False, 'x_center'] / self._pixelSize,
                    stats.loc[stats['keep_for_analysis'] != False, 'y_center'] / self._pixelSize,
                    s     = 1,
                    color = 'white')
        self._clusterCenter, = ax0.plot([],
                                        [],
                                        'oy',
                                        markersize      = 10,
                                        fillstyle       = 'none',
                                        markeredgewidth = 2.5)
                    
        ax0.set_xlim(0, wfImage.shape[1])
        ax0.set_ylim(0, wfImage.shape[0])
        ax0.set_title('Cluster centers')
        ax0.set_xlabel('x-position, pixel')
        ax0.set_ylabel('y-position, pixel')
        ax0.set_aspect('equal')
        
        # Draw the zoomed region of the current cluster
        self._clusterLocs, = ax1.plot([], [], '.c')
        ax1.imshow(wfImage,
                   cmap          = 'inferno',
                   interpolation = 'nearest',
                   vmax          = np.max(wfImage) / 2)
                   #vmax          = np.max(wfImage) / 25)
        # Plot unclustered localizations
        ax1.scatter(locs[locs['cluster_id'] == -1]['x'] / self._pixelSize,
                    locs[locs['cluster_id'] == -1]['y'] / self._pixelSize,
                    s = 4,
                    color = 'white')
        
        # Plot the cluster centers
        ax1.scatter(stats.loc[stats['keep_for_analysis'] != False, 'x_center'] / self._pixelSize,
                    stats.loc[stats['keep_for_analysis'] != False, 'y_center'] / self._pixelSize,
                    s     = 30,
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