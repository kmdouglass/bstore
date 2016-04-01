from nose.tools import *
from DataSTORM import processors as proc
import pandas as pd
import numpy as np

def test_DriftCorrection_Processor():
    """Drift correction is properly applied to all localizations.
    
    """
    # Load localization + fiducial ground truth test set
    locs = pd.read_csv('test_files/test_localizations_with_fiducials.csv')
    
    # Create the drift corrector
    dc = proc.FiducialDriftCorrect(mergeRadius           = 25,
                                   offTime               = 1,
                                   minFracFiducialLength = 0.5,
                                   neighborRadius        = 150,
                                   smoothingWindowSize   = 800,
                                   smoothingFilterSize   = 200,
                                   interactiveSearch     = True,
                                   noLinking             = True,
                                   noClustering          = False,
                                   removeFiducials       = True)