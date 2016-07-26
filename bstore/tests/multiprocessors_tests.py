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
    assert_equal(round(dx), -194.0)
    assert_equal(round(dy), -173.0)