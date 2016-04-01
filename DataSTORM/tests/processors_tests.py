from nose.tools import *
from DataSTORM import processors as proc
import pandas as pd
import numpy as np
import sys

def test_DriftCorrection():
    """Drift correction is properly applied to all localizations.
    
    """
    # Load localization + fiducial ground truth test set
    locs = pd.read_csv('test_files/test_localizations_with_fiducials.csv')
    
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
