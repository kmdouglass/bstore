from nose.tools import *
from DataSTORM import processors as proc
import pandas as pd
import numpy as np
import sys

# Load localization + fiducial ground truth test set
locs = pd.read_csv('tests/test_files/test_localizations_with_fiducials.csv')

def test_DriftCorrection():
    """Drift correction is properly applied to all localizations.
    
    """
    # Create the drift corrector
    dc = proc.FiducialDriftCorrect(minFracFiducialLength = 0.5,
                                   neighborRadius        = 150,
                                   smoothingWindowSize   = 800,
                                   smoothingFilterSize   = 200,
                                   interactiveSearch     = False,
                                   doFiducialSearch      = False,
                                   noLinking             = True,
                                   noClustering          = False,
                                   removeFiducials       = True)
                                   
    # Tell the drift corrector where the fiducials are.
    # Normally, these methods are not directly access by users; this is why
    # we need to handle renaming of columns.
    dc.searchRegions = [
        {'xMin' : 730,
         'xMax' : 870,
         'yMin' : 730,
         'yMax' : 820},
         {'xMin' : 1400,
          'xMax' : 1600,
          'yMin' : 1400,
          'yMax' : 1600}
         ]
    locs.rename(columns = {'x [nm]' : 'x', 'y [nm]' : 'y'}, inplace = True)
    fidRegions = dc.reduceSearchArea(locs)
    dc.detectFiducials(fidRegions)
    locs.rename(columns = {'x' : 'x [nm]', 'y' : 'y [nm]'}, inplace = True)
    
    # Did we find the trajectories?
    assert_equal(len(dc.fiducialTrajectories), 2)
    
    # Correct the localizations
    corrLocs = dc(locs)
    
    # Were fiducial locs removed? There should be 20000 ground truth
    # localizations after the localizations belonging to
    # fiducials are removed.
    assert_equal(corrLocs.shape[0], 20000)
    
    # Was the correct drift trajectory applied? The original locs
    # should be in x + dx and y + dy of corrdf
    # round() avoids rounding errors when making comparisons
    checkx = (corrLocs['x [nm]'] + corrLocs['dx [nm]']).round(2).isin(
                                           locs['x [nm]'].round(2).as_matrix())
    checky = (corrLocs['y [nm]'] + corrLocs['dy [nm]']).round(2).isin(
                                           locs['y [nm]'].round(2).as_matrix())
    ok_(checkx.all())
    ok_(checky.all())
    
    # dx and dy should equal the avgSpline
    fidTraj_x = corrLocs[['dx [nm]', 'frame']].sort_values(
              'frame').drop_duplicates('frame')['dx [nm]'].round(2).as_matrix()
    fidTraj_y = corrLocs[['dy [nm]', 'frame']].sort_values(
              'frame').drop_duplicates('frame')['dy [nm]'].round(2).as_matrix()
    spline_x  = dc.avgSpline['xS'].round(2).as_matrix()
    spline_y  = dc.avgSpline['yS'].round(2).as_matrix()
    ok_(all(fidTraj_x == spline_x))
    ok_(all(fidTraj_y == spline_y))
    
def test_DriftCorrection_dropTrajectories():
    """Drift correction works after a trajectory is dropped.
    
    """    
    # Create the drift corrector
    dc = proc.FiducialDriftCorrect(minFracFiducialLength = 0.5,
                                   neighborRadius        = 150,
                                   smoothingWindowSize   = 800,
                                   smoothingFilterSize   = 200,
                                   interactiveSearch     = False,
                                   doFiducialSearch      = False,
                                   noLinking             = True,
                                   noClustering          = False,
                                   removeFiducials       = True)
                                   
    # Tell the drift corrector where the fiducials are.
    # Normally, these methods are not directly access by users; this is why
    # we need to handle renaming of columns.
    dc.searchRegions = [
        {'xMin' : 730,
         'xMax' : 870,
         'yMin' : 730,
         'yMax' : 820},
         {'xMin' : 1400,
          'xMax' : 1600,
          'yMin' : 1400,
          'yMax' : 1600}
         ]
    locs.rename(columns = {'x [nm]' : 'x', 'y [nm]' : 'y'}, inplace = True)
    fidRegions = dc.reduceSearchArea(locs)
    dc.detectFiducials(fidRegions)
    locs.rename(columns = {'x' : 'x [nm]', 'y' : 'y [nm]'}, inplace = True)
    
    # Did we find the trajectories?
    assert_equal(len(dc.fiducialTrajectories), 2)
    
    # Correct the localizations
    corrLocs = dc(locs)
    assert_equal(corrLocs.shape[0], 20000)
    
    # Drop second trajectory (index = 1)
    dc.dropTrajectories([1])
    assert_equal(len(dc.fiducialTrajectories), 1)
    
    # Recorrect the localizations
    corrLocs = dc(locs)
    # Since we didn't drop a trajectory, there should be 30000 locs now
    assert_equal(corrLocs.shape[0], 30000)
    
    # Was the correct drift trajectory applied? The original locs
    # should be in x + dx and y + dy of corrdf
    # round() avoids rounding errors when making comparisons
    checkx = (corrLocs['x [nm]'] + corrLocs['dx [nm]']).round(2).isin(
                                           locs['x [nm]'].round(2).as_matrix())
    checky = (corrLocs['y [nm]'] + corrLocs['dy [nm]']).round(2).isin(
                                           locs['y [nm]'].round(2).as_matrix())
    ok_(checkx.all())
    ok_(checky.all())
    
    # dx and dy should equal the avgSpline
    fidTraj_x = corrLocs[['dx [nm]', 'frame']].sort_values(
              'frame').drop_duplicates('frame')['dx [nm]'].round(2).as_matrix()
    fidTraj_y = corrLocs[['dy [nm]', 'frame']].sort_values(
              'frame').drop_duplicates('frame')['dy [nm]'].round(2).as_matrix()
    spline_x  = dc.avgSpline['xS'].round(2).as_matrix()
    spline_y  = dc.avgSpline['yS'].round(2).as_matrix()
    ok_(all(fidTraj_x == spline_x))
    ok_(all(fidTraj_y == spline_y))
    
def test_ClusterStats():
    """Cluster statistics are computed correctly.
    
    """
    statProc = proc.ComputeClusterStats()
    data     = pd.read_csv('tests/test_files/test_cluster_stats.csv')
    
    # Rename columns to work with ComputeClusterStats
    data.rename(columns = {'x [nm]' : 'x', 'y [nm]' : 'y'}, inplace = True)
    
    stats = statProc(data)
    
    # Cluster ID 0: symmetric about center
    assert_equal(stats['x_center'].iloc[0],                                  0)
    assert_equal(stats['y_center'].iloc[0],                                  0)
    assert_equal(stats['number_of_localizations'].iloc[0],                   5)
    assert_equal(stats['radius_of_gyration'].iloc[0].round(2),            0.77)
    assert_equal(stats['eccentricity'].iloc[0].round(2),                     1)
    assert_equal(stats['convex_hull_area'].iloc[0].round(2),                 1)
    
    # Cluster ID 1: longer in x than in y
    assert_equal(stats['x_center'].iloc[1],                                 10)
    assert_equal(stats['y_center'].iloc[1],                                  2)
    assert_equal(stats['number_of_localizations'].iloc[1],                   5)
    assert_equal(stats['radius_of_gyration'].iloc[1].round(2),            2.45)
    assert_equal(stats['eccentricity'].iloc[1].round(2),                     4)
    assert_equal(stats['convex_hull_area'].iloc[1].round(2),                 8)