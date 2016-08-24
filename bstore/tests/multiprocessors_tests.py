# © All rights reserved. ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Switzerland, Laboratory of Experimental Biophysics, 2016
# See the LICENSE.txt file for more details.

"""Unit tests for the multiprocessors module.

Notes
-----
nosetests should be run in the directory just above the `tests` folder.
 
"""

from nose.tools import *
from pathlib    import Path
from bstore import multiprocessors as mp
from bstore import config
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

testDataRoot   = Path(config.__Path_To_Test_Data__)
pathToTestData = testDataRoot / Path('multiprocessor_test_files')
assert pathToTestData.exists(), 'Test data could not be found.'

def test_AlignToWidefield():
    """AlignToWidefield works as expected.
    
    """
    pathToLocs = pathToTestData \
               / Path('align_to_widefield/locResults_A647_Pos0.csv')
    pathToWF = pathToTestData / Path('align_to_widefield') \
             /Path('HeLaS_Control_53BP1_IF_FISH_A647_WF1') \
             /Path('HeLaS_Control_53BP1_IF_FISH_A647_WF1_MMStack_Pos0.ome.tif')
             
    with open(str(pathToLocs), 'r') as f:
        locs = pd.read_csv(f)
        
    with open(str(pathToWF), 'rb') as f:
        wfImage = plt.imread(f)
        
    # Create the multiprocessor and align the data
    aligner = mp.AlignToWidefield()
    dx, dy  = aligner(locs, wfImage)
    
    # Correct shifts were determined in an interactive session
    assert_equal(round(dy), -194.0)
    assert_equal(round(dx), -173.0)
    
def test_EstimatePhotons():
    """EstimatePhotons correctly finds photons, backgrounds, and boundaries.
    
    """
    offset  = 100 # ADU
    ny, nx  = 50, 50
    imgTest = offset * np.ones((ny, nx))
    
    # Create a 11x11 region with a background of 50 ADU + offset = 150 ADU
    imgTest[5:16, 5:16] = 150
    
    # Create two circular spots of radius 4 px with center signal intensity
    # of 500 ADU. The other signal intensities should be 300 ADU. Add to
    # these the local background and offset. One spot is centered at (10,10),
    # the other at (30, 40).
    y,x    = np.ogrid[-10:ny - 10, -10:nx - 10]
    mask   = x * x + y * y <= 4 * 4
    imgTest[mask] = imgTest[mask] + 300
    imgTest[10, 10] = 100 + 50 + 500
    
    y,x    = np.ogrid[-30:ny - 30, -40:nx - 40]
    mask   = x * x + y * y <= 4 * 4
    imgTest[mask] = imgTest[mask] + 300
    imgTest[30, 40] = 100 + 500
    
    # Create a circular spot near the boundary at (48, 10)
    y,x    = np.ogrid[-48:ny - 48, -10:nx - 10]
    mask   = x * x + y * y <= 4 * 4
    imgTest[mask] = imgTest[mask] + 300
    imgTest[48, 10] = 100 + 50 + 500
    
    estimator = mp.EstimatePhotons()
    photons, bg = estimator(imgTest, [(10, 10), (30, 40), (48, 10)])
    
    assert_equal(photons[0], 29800)
    assert_equal(photons[1], 29800)
    ok_(np.isnan(photons[2]))
    
    assert_equal(bg[0], 50)
    assert_equal(bg[1], 0)
    ok_(np.isnan(bg[2]))

@raises(AssertionError)    
def test_EstimatePhotons_Bad_Mask_Size():
    """Assertion errors are raised when bgMaskSize is too small.
    
    """
    offset  = 100 # ADU
    ny, nx  = 50, 50
    imgTest = offset * np.ones((ny, nx))
    
    # Create a 11x11 region with a background of 50 ADU + offset = 150 ADU
    imgTest[5:16, 5:16] = 150
    
    # Create two circular spots of radius 4 px with center signal intensity
    # of 500 ADU. The other signal intensities should be 300 ADU. Add to
    # these the local background and offset. One spot is centered at (10,10),
    # the other at (30, 40).
    y,x    = np.ogrid[-10:ny - 10, -10:nx - 10]
    mask   = x * x + y * y <= 4 * 4
    imgTest[mask] = imgTest[mask] + 300
    imgTest[10, 10] = 100 + 50 + 500
    
    y,x    = np.ogrid[-30:ny - 30, -40:nx - 40]
    mask   = x * x + y * y <= 4 * 4
    imgTest[mask] = imgTest[mask] + 300
    imgTest[30, 40] = 100 + 500
    
    # Create a circular spot near the boundary at (48, 10)
    y,x    = np.ogrid[-48:ny - 48, -10:nx - 10]
    mask   = x * x + y * y <= 4 * 4
    imgTest[mask] = imgTest[mask] + 300
    imgTest[48, 10] = 100 + 50 + 500
    
    estimator = mp.EstimatePhotons(bgMaskSize = 8, spotMaskRadius = 4)
    photons, bg = estimator(imgTest, [(10, 10), (30, 40), (48, 10)])
    