"""Unit tests for the batch module.

Notes
-----
nosetests should be run in the directory just above the `tests` folder.
 
"""

__author__ = 'Kyle M. Douglass'
__email__ = 'kyle.m.douglass@gmail.com' 

from nose.tools import *
from pathlib    import Path
from DataSTORM.batch import CSVBatchProcessor

# Update this to point towards the test data on your system or network
pathToTestData = Path('/home/douglass/ownCloud/test-data/Telomeres_Knockdowns')

# Build the test batch processors
pipeline = []
bp       = CSVBatchProcessor(pathToTestData, pipeline,
                             useSameFolder = True,
                             suffix = 'locResults.dat')

def test_CSVBatchProcessor_DatasetParser():
    """CSVBatchProcessor correctly identifies the localization files.
    
    """
    knownDatasets = ['HeLaS_Control_IFFISH_A647_1_MMStack_locResults.dat',
                     'HeLaS_Control_IFFISH_A647_2_MMStack_locResults.dat',
                     'HeLaS_shTRF2_IFFISH_A647_1_MMStack_locResults.dat',
                     'HeLaS_shTRF2_IFFISH_A647_2_MMStack_locResults.dat']
                     
    assert_equal(len(bp.datasetList), 4)
                     
    for ds in bp.datasetList:
        ok_(str(ds.name) in knownDatasets,
            'Batch processor found a file not in the known datasets.')    