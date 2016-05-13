"""Unit tests for the batch module.

Notes
-----
nosetests should be run in the directory just above the `tests` folder.
 
"""

__author__ = 'Kyle M. Douglass'
__email__ = 'kyle.m.douglass@gmail.com' 

from nose.tools import *
from pathlib    import Path
from DataSTORM.batch import CSVBatchProcessor, HDFBatchProcessor
from DataSTORM import processors as proc
from DataSTORM import database   as db
import shutil
import pandas as pd

# Update this to point towards the test data on your system or network
pathToTestData = Path(('/home/kmdouglass/ownCloud/'
                       'test-data/Telomeres_Knockdowns'))
assert pathToTestData.exists(), 'Test data could not be found.'

# Build the test batch processors
outputDir  = Path('tests/test_files/batch_test_results/')
if outputDir.exists():
    shutil.rmtree(str(outputDir))

cleanup    = proc.CleanUp()
locFilter1 = proc.Filter('loglikelihood', '<', 250)
locFilter2 = proc.Filter('sigma [nm]',    '<', 180)
pipeline   = [cleanup, locFilter1, locFilter2]
bpCSV      = CSVBatchProcessor(pathToTestData, pipeline,
                               useSameFolder   = False,
                               suffix          = 'locResults.dat',
                               outputDirectory = outputDir)

inputDB    = Path('tests/test_files/test_experiment/test_experiment_db.h5')
locFilter1 = proc.Filter('loglikelihood', '<', 800)
pipeline   = [locFilter1, locFilter2]                               
bpHDF      = HDFBatchProcessor(inputDB, pipeline)

def test_CSVBatchProcessor_DatasetParser():
    """CSVBatchProcessor correctly identifies the localization files.
    
    """
    knownDatasets = ['HeLaS_Control_IFFISH_A647_1_MMStack_locResults.dat',
                     'HeLaS_Control_IFFISH_A647_2_MMStack_locResults.dat',
                     'HeLaS_shTRF2_IFFISH_A647_1_MMStack_locResults.dat',
                     'HeLaS_shTRF2_IFFISH_A647_2_MMStack_locResults.dat']
                     
    assert_equal(len(bpCSV.datasetList), 4)
                     
    for ds in bpCSV.datasetList:
        ok_(str(ds.name) in knownDatasets,
            'Batch processor found a file not in the known datasets.')
            
def test_CSVBatchProcessor_Pipeline():
    """The batch processor correctly applies the pipeline to the data.
    
    """
    # Execute the batch process
    bpCSV.go()
    
    # Check the results of the filtering
    results = ['HeLaS_Control_IFFISH_A647_1_MMStack_locResults_processed.dat',
               'HeLaS_Control_IFFISH_A647_2_MMStack_locResults_processed.dat',
               'HeLaS_shTRF2_IFFISH_A647_1_MMStack_locResults_processed.dat',
               'HeLaS_shTRF2_IFFISH_A647_2_MMStack_locResults_processed.dat']
               
    for currRes in results:
        pathToCurrRes = outputDir / Path(currRes)
        df = pd.read_csv(str(pathToCurrRes), sep = ',')
        
        # Verify that filters were applied during the processing
        ok_(df['loglikelihood'].max() <= 250,
            'Loglikelihood column has wrong values.')
        ok_(df['sigma [nm]'].max()    <= 180,
            'sigma [nm] column has wrong values.')
            
def test_HDFBatchProcessor_DatasetParser():
    """HDFBatchProcessor correctly finds the datasets in the HDF file.
    
    """
    #knownDatasets = ['HeLaL_Control/HeLaL_Control_1/locResults_A647_Pos0',
    #                 'HeLaS_Control/HeLaS_Control_2/locResults_A647_Pos0']
    knownDS = [db.Dataset(1, 'A647', None, (0,),
                          'HeLaL_Control', None, 'locResults'),
               db.Dataset(2, 'A647', None, (0,),
                          'HeLaS_Control', None, 'locResults')]
                    
    assert_equal(len(bpHDF.datasetList), 2)
    
    # This test might fail if the lists aren't zipped in the right order
    for currDS, currKnownDS in zip(bpHDF.datasetList, knownDS):
        assert_equal(currDS.acqID,       currKnownDS.acqID)
        assert_equal(currDS.channelID,   currKnownDS.channelID)
        assert_equal(currDS.posID,       currKnownDS.posID)
        assert_equal(currDS.prefix,      currKnownDS.prefix)
        assert_equal(currDS.sliceID,     currKnownDS.sliceID)
        assert_equal(currDS.datasetType, currKnownDS.datasetType)