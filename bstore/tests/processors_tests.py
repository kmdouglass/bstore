# © All rights reserved. ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Switzerland, Laboratory of Experimental Biophysics, 2016
# See the LICENSE.txt file for more details.

from nose.tools import *
from bstore import processors as proc
from bstore import config
import pandas as pd
from pathlib import Path
import numpy as np

testDataRoot = Path(config.__Path_To_Test_Data__)

# Load localization + fiducial ground truth test set
pathToTestData = testDataRoot / Path('processor_test_files') \
                              / Path('test_localizations_with_fiducials.csv')
locs = pd.read_csv(str(pathToTestData))

def test_FiducialDriftCorrect_Instantiation():
    """The FiducialDriftCorrect processor has the required methods and fields.
    
    """
    dc = proc.FiducialDriftCorrect()

def test_DriftCorrection():
    """Drift correction is properly applied to all localizations.
    
    """
    # Create the drift corrector
    dc = proc.FiducialDriftCorrect(coordCols = ['x [nm]', 'y [nm]'],
                                   frameCol = 'frame', removeFiducials = True)
                                   
    # Tell the drift corrector where the fiducials are.
    # Normally, these methods are not directly access by users; this is why
    # we need to handle renaming of columns.
    dc._fidRegions = [
        {'xMin' : 730,
         'xMax' : 870,
         'yMin' : 730,
         'yMax' : 820},
         {'xMin' : 1400,
          'xMax' : 1600,
          'yMin' : 1400,
          'yMax' : 1600}
         ]
         
    # Extract fiducials from the localizations
    fiducialLocs = dc._extractLocsFromRegions(locs)
    dc.driftComputer.fiducialLocs = fiducialLocs
    
    # Did we find the trajectories?
    assert_equal(fiducialLocs.index.levels[1].max(), 1)

    # Correct the localizations
    dc.interactiveSearch = False
    corrLocs = dc(locs)
    
    # Were fiducial locs removed? There should be 20000 ground truth
    # localizations after the localizations belonging to
    # fiducials are removed.
    assert_equal(corrLocs.shape[0], 20000)
    
    # Was the correct drift trajectory applied? The original locs
    # should be in x + dx and y + dy of corrdf
    # round() avoids rounding errors when making comparisons
    checkx = (corrLocs['x [nm]'] + corrLocs['dx']).round(2).isin(
                                           locs['x [nm]'].round(2).as_matrix())
    checky = (corrLocs['y [nm]'] + corrLocs['dy']).round(2).isin(
                                           locs['y [nm]'].round(2).as_matrix())
    ok_(checkx.all())
    ok_(checky.all())
    
    # dx and dy should equal the avgSpline
    fidTraj_x = corrLocs[['dx', 'frame']].sort_values(
              'frame').drop_duplicates('frame')['dx'].round(2).as_matrix()
    fidTraj_y = corrLocs[['dy', 'frame']].sort_values(
              'frame').drop_duplicates('frame')['dy'].round(2).as_matrix()
    spline_x  = dc.driftTrajectory['xS'].round(2).as_matrix()
    spline_y  = dc.driftTrajectory['yS'].round(2).as_matrix()
    ok_(all(fidTraj_x == spline_x))
    ok_(all(fidTraj_y == spline_y))
    
def test_DriftCorrection_dropTrajectories():
    """Drift correction works after a trajectory is dropped.
    
    """    
    # Create the drift corrector
    dc = proc.FiducialDriftCorrect(coordCols = ['x [nm]', 'y [nm]'],
                                   frameCol = 'frame', removeFiducials = True)
                                   
    # Tell the drift corrector where the fiducials are.
    # Normally, these methods are not directly access by users; this is why
    # we need to handle renaming of columns.
    dc._fidRegions = [
        {'xMin' : 730,
         'xMax' : 870,
         'yMin' : 730,
         'yMax' : 820},
         {'xMin' : 1400,
          'xMax' : 1600,
          'yMin' : 1400,
          'yMax' : 1600}
         ]
    # Extract fiducials from the localizations
    fiducialLocs = dc._extractLocsFromRegions(locs)
    dc.driftComputer.fiducialLocs = fiducialLocs
    
    # Did we find the trajectories?
    assert_equal(fiducialLocs.index.levels[1].max(), 1)
    
    # Correct the localizations
    dc.interactiveSearch = False
    corrLocs = dc(locs)
    
    # Were fiducial locs removed? There should be 20000 ground truth
    # localizations after the localizations belonging to
    # fiducials are removed.
    assert_equal(corrLocs.shape[0], 20000)
    
    # Use the first trajectory only (index = 0)
    dc.driftComputer.useTrajectories = [0]
    
    # Recorrect the localizations
    corrLocs = dc(locs)
    
    # Was the correct drift trajectory applied? The original locs
    # should be in x + dx and y + dy of corrdf
    # round() avoids rounding errors when making comparisons
    checkx = (corrLocs['x [nm]'] + corrLocs['dx']).round(2).isin(
                                           locs['x [nm]'].round(2).as_matrix())
    checky = (corrLocs['y [nm]'] + corrLocs['dy']).round(2).isin(
                                           locs['y [nm]'].round(2).as_matrix())
    ok_(checkx.all())
    ok_(checky.all())
    
    # dx and dy should equal the avgSpline
    fidTraj_x = corrLocs[['dx', 'frame']].sort_values(
              'frame').drop_duplicates('frame')['dx'].round(2).as_matrix()
    fidTraj_y = corrLocs[['dy', 'frame']].sort_values(
              'frame').drop_duplicates('frame')['dy'].round(2).as_matrix()
    spline_x  = dc.driftTrajectory['xS'].round(2).as_matrix()
    spline_y  = dc.driftTrajectory['yS'].round(2).as_matrix()
    ok_(all(fidTraj_x == spline_x))
    ok_(all(fidTraj_y == spline_y))
    
def test_ClusterStats():
    """Cluster statistics are computed correctly.
    
    """
    statProc   = proc.ComputeClusterStats()
    pathToData = testDataRoot \
               / Path('processor_test_files/test_cluster_stats.csv')
    data       = pd.read_csv(str(pathToData))
    
    # Rename columns to work with ComputeClusterStats
    data.rename(columns = {'x [nm]' : 'x', 'y [nm]' : 'y'}, inplace = True)
    
    stats = statProc(data)
    
    # Cluster ID 0: symmetric about center
    assert_equal(stats['x_center'].iloc[0],                                  0)
    assert_equal(stats['y_center'].iloc[0],                                  0)
    assert_equal(stats['number_of_localizations'].iloc[0],                   5)
    assert_equal(stats['radius_of_gyration'].iloc[0].round(2),            0.63)
    assert_equal(stats['eccentricity'].iloc[0].round(2),                     1)
    
    # Cluster ID 1: longer in x than in y
    assert_equal(stats['x_center'].iloc[1],                                 10)
    assert_equal(stats['y_center'].iloc[1],                                  2)
    assert_equal(stats['number_of_localizations'].iloc[1],                   5)
    assert_equal(stats['radius_of_gyration'].iloc[1].round(2),            2.00)
    assert_equal(stats['eccentricity'].iloc[1].round(2),                     4)
    
    # Only run these tests if pyhull is installed
    # pyhull is not available in Linux
    try:
        from pyhull import qconvex
        assert_equal(stats['convex_hull'].iloc[0].round(2), 1)
        assert_equal(stats['convex_hull'].iloc[1].round(2), 8)
    except ImportError:
        pass

def test_ClusterStats_CustomCoordColumns():
    """ComputeClusterStats allows for customizing the coordinate columns.
    
    """
    # This is the same test as above, but the column names will be
    # changed in ComputeClusterStats's constructor instead.
    statProc   = proc.ComputeClusterStats(coordCols=['x [nm]', 'y [nm]'])
    pathToData = testDataRoot \
               / Path('processor_test_files/test_cluster_stats.csv')
    data       = pd.read_csv(str(pathToData))
    
    stats = statProc(data)
    
    # Cluster ID 0: symmetric about center
    assert_equal(stats['x [nm]_center'].iloc[0],                             0)
    assert_equal(stats['y [nm]_center'].iloc[0],                             0)
    assert_equal(stats['number_of_localizations'].iloc[0],                   5)
    assert_equal(stats['radius_of_gyration'].iloc[0].round(2),            0.63)
    assert_equal(stats['eccentricity'].iloc[0].round(2),                     1)
    
    # Cluster ID 1: longer in x than in y
    assert_equal(stats['x [nm]_center'].iloc[1],                            10)
    assert_equal(stats['y [nm]_center'].iloc[1],                             2)
    assert_equal(stats['number_of_localizations'].iloc[1],                   5)
    assert_equal(stats['radius_of_gyration'].iloc[1].round(2),            2.00)
    assert_equal(stats['eccentricity'].iloc[1].round(2),                     4)
    
    # Only run these tests if pyhull is installed
    # pyhull is not available in Linux
    try:
        from pyhull import qconvex
        assert_equal(stats['convex_hull'].iloc[0].round(2), 1)
        assert_equal(stats['convex_hull'].iloc[1].round(2), 8)
    except ImportError:
        pass
    
def test_ClusterStats_CustomStats():
    """ComputeClusterStats accepts custom stats functions.
    
    """
    # ComputeClusterStats's constructor should accept a dict with
    # name/function pairs and apply each function to the clustered
    # localizations. This allows customzing what statistics are
    # computed at run-time by the user.
    pathToData = testDataRoot \
               / Path('processor_test_files/test_cluster_stats.csv')
    data       = pd.read_csv(str(pathToData))
    
    # Define a custom statistic to compute
    def VarTimesTwo(group, coordinates):
        # Multiples each localization position by 2, then computes
        # the sum of the variances. This is silly but serves as an example.
        variances = group[coordinates].apply(lambda x: x * 2).var(ddof=0)
        return variances.sum()
    
    customStats = {'var_times_two' : VarTimesTwo}
        
    statProc   = proc.ComputeClusterStats(coordCols=['x [nm]', 'y [nm]'],
                                          statsFunctions = customStats)
                                          
    stats = statProc(data)
    ok_('var_times_two' in stats, 'Error: New column name not in DataFrame.')
    assert_equal(stats['var_times_two'].iloc[0].round(2),                 1.60)
    assert_equal(stats['var_times_two'].iloc[1].round(2),                16.00)
    
def test_MergeFang_Stats():
    """Merger correctly merges localizations from the same molecule.
    
    """
    merger         = proc.Merge(mergeRadius = 25,
                                tOff = 2,
                                statsComputer = proc.MergeFang())
    pathToTestData = testDataRoot / Path('processor_test_files/merge.csv')
    
    with open(str(pathToTestData), mode = 'r') as inFile:
        df = pd.read_csv(inFile, comment = '#')
    
    mergedDF = merger(df)
    
    # Localizations should be merged into two resulting localization
    assert_equal(len(mergedDF), 2)
    
    ok_(np.abs(mergedDF['x'].iloc[0].round(2) - 8.62) < 0.001,
        'Merged x-coordinate is incorrect.')
    ok_(np.abs(mergedDF['y'].iloc[0].round(2) - 10.24)< 0.001,
        'Merged y-coordinate is incorrect.')
    assert_equal(mergedDF['z'].iloc[0],               0)
    assert_equal(mergedDF['photons'].iloc[0],      5500)
    assert_equal(mergedDF['loglikelihood'].iloc[0], 100)
    assert_equal(mergedDF['background'].iloc[0],    600)
    assert_equal(mergedDF['frame'].iloc[0],           0)
    assert_equal(mergedDF['length'].iloc[0],          5)
    assert_equal(mergedDF['sigma'].iloc[0],         150)
    ok_('particle' in mergedDF)
    
def test_Merger():
    """Merger returns a Data Frame with particle column attached.
    
    """
    merger         = proc.Merge(mergeRadius   = 25,
                                tOff          = 2,
                                statsComputer = None)
    pathToTestData = testDataRoot / Path('processor_test_files/merge.csv')
    
    with open(str(pathToTestData), mode = 'r') as inFile:
        df = pd.read_csv(inFile, comment = '#')
        mergedDF = merger(df)
        
    ok_('particle' in mergedDF.columns,
        'Error: \'particle\' is not in columns.')
    assert_equal(mergedDF['particle'].max(), 1)

def test_MergeFang_ZeroOffTime():
    """Merger detects the off time gap and creates separate molecules.
    
    """
    merger         = proc.Merge(mergeRadius   = 25,
                                tOff          = 1,
                                statsComputer = proc.MergeFang())
    pathToTestData = testDataRoot / Path('processor_test_files/merge.csv')
    
    with open(str(pathToTestData), mode = 'r') as inFile:
        df = pd.read_csv(inFile, comment = '#')
        mergedDF = merger(df)  
    
    # Due to the smaller gap-time, there should be three tracks, not two
    assert_equal(len(mergedDF), 3)
    
def test_ConvertHeader():
    """ConvertHeader successfully applies the default mapping.
    
    """
    # Create a test dataset
    test_data                       = {}
    test_data['x [nm]']             = 1
    test_data['y [nm]']             = 2
    test_data['z [nm]']             = 3
    test_data['frame']              = 4
    test_data['uncertainty [nm]']   = 5
    test_data['intensity [photon]'] = 6
    test_data['offset [photon]']    = 7
    test_data['loglikelihood']      = 8
    test_data['sigma [nm]']         = 9
    test_data['dx [nm]']            = 10
    test_data['dy [nm]']            = 11
    test_data['length [frames]']    = 12
    
    # These two are not defined by the default format, so their names
    # should remain unchanged
    test_data['cluster_id']         = 13
    test_data['particle']           = 14
    
    # Pandas DataFrames with all scalars require an index; hence, index = [1]
    df = pd.DataFrame(test_data, index = [1])
    
    # Create the header converter and convert the columns to datastore default
    converter = proc.ConvertHeader()
    conv_df   = converter(df)
    
    assert_equal(conv_df['x'].loc[1],             1)
    assert_equal(conv_df['y'].loc[1],             2)
    assert_equal(conv_df['z'].loc[1],             3)
    assert_equal(conv_df['frame'].loc[1],         4)
    assert_equal(conv_df['precision'].loc[1],     5)
    assert_equal(conv_df['photons'].loc[1],       6)
    assert_equal(conv_df['background'].loc[1],    7)
    assert_equal(conv_df['loglikelihood'].loc[1], 8)
    assert_equal(conv_df['sigma'].loc[1],         9)
    assert_equal(conv_df['dx'].loc[1],           10)
    assert_equal(conv_df['dy'].loc[1],           11)
    assert_equal(conv_df['length'].loc[1],       12)
    assert_equal(conv_df['cluster_id'].loc[1],   13)
    assert_equal(conv_df['particle'].loc[1],     14)
    
def test_ConvertHeader_Custom_Mapping():
    """ConvertHeader successfully applies a user-defined mapping.
    
    """
    # Create a test dataset
    test_data                       = {}
    test_data['x [nm]']             = 1
    test_data['y [nm]']             = 2
    test_data['z [nm]']             = 3
    test_data['frame']              = 4
    
    # Pandas DataFrames with all scalars require an index; hence, index = [1]
    df = pd.DataFrame(test_data, index = [1])
    
    # Create the header converter and convert the columns to datastore default
    # Note that a mapping for 'frame' is not supplied, so it should not change.
    from bstore.parsers import FormatMap
    testMap = FormatMap({'x [nm]' : 'x',
                         'y [nm]' : 'y',
                         'z [nm]' : 'z'})
    converter = proc.ConvertHeader(mapping = testMap)
    conv_df   = converter(df)
    
    assert_equal(conv_df['x'].loc[1],             1)
    assert_equal(conv_df['y'].loc[1],             2)
    assert_equal(conv_df['z'].loc[1],             3)
    assert_equal(conv_df['frame'].loc[1],         4)