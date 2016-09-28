# © All rights reserved. ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Switzerland, Laboratory of Experimental Biophysics, 2016
# See the LICENSE.txt file for more details.

"""Unit tests for the batch module.

Notes
-----
nosetests should be run in the directory just above the `tests` folder.
 
"""

__author__ = 'Kyle M. Douglass'
__email__ = 'kyle.m.douglass@gmail.com' 

from nose.tools import assert_equal, ok_
from pathlib    import Path
from bstore.batch import CSVBatchProcessor, HDFBatchProcessor
from bstore       import processors as proc
from bstore       import database   as db
from bstore       import config
from bstore.datasetTypes.Localizations import Localizations
import shutil
import pandas as pd
import json

config.__Registered_DatasetTypes__.append('Localizations')

testDataRoot   = Path(config.__Path_To_Test_Data__)
pathToTestData = testDataRoot / Path('test_experiment_2')
assert pathToTestData.exists(), 'Test data could not be found.'

# Build the test batch processors
outputDir  = testDataRoot / Path('batch_test_results/')
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

outputDirHDF  = outputDir / Path('HDFBatch_test_results/')
if outputDirHDF.exists():
    shutil.rmtree(str(outputDirHDF))
    
inputDB    = testDataRoot / Path('test_experiment/test_experiment_db.h5')
myDB       = db.HDFDatabase(inputDB)
locFilter1 = proc.Filter('loglikelihood', '<', 800)
locFilter2 = proc.Filter('sigma',         '<', 200)
pipeline   = [locFilter1, locFilter2]                               
bpHDF      = HDFBatchProcessor(inputDB, pipeline,
                               outputDirectory = outputDirHDF)

def test_CSVBatchProcessor_DatasetParser():
    """CSVBatchProcessor correctly identifies the localization files.
    
    """
    knownDatasets = ['HeLaS_Control_IFFISH_A647_1_MMStack_Pos0_locResults.dat',
                     'HeLaS_Control_IFFISH_A647_2_MMStack_Pos0_locResults.dat',
                     'HeLaS_shTRF2_IFFISH_A647_1_MMStack_Pos0_locResults.dat',
                     'HeLaS_shTRF2_IFFISH_A647_2_MMStack_Pos0_locResults.dat']
                     
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
    results = [
           'HeLaS_Control_IFFISH_A647_1_MMStack_Pos0_locResults_processed.csv',
           'HeLaS_Control_IFFISH_A647_2_MMStack_Pos0_locResults_processed.csv',
           'HeLaS_shTRF2_IFFISH_A647_1_MMStack_Pos0_locResults_processed.csv',
           'HeLaS_shTRF2_IFFISH_A647_2_MMStack_Pos0_locResults_processed.csv']
               
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
    knownDS = [myDB.dsID('HeLaL_Control', 1, 'Localizations', None,
                         'A647', None, (0,), None),
               myDB.dsID('HeLaS_Control', 2, 'Localizations', None,
                         'A647', None, (0,), None)]
                    
    assert_equal(len(bpHDF.datasetList), 2)
    
    # This test might fail if the lists aren't zipped in the right order
    for currDS, currKnownDS in zip(bpHDF.datasetList, knownDS):
        assert_equal(currDS.acqID,       currKnownDS.acqID)
        assert_equal(currDS.channelID,   currKnownDS.channelID)
        assert_equal(currDS.posID,       currKnownDS.posID)
        assert_equal(currDS.prefix,      currKnownDS.prefix)
        assert_equal(currDS.sliceID,     currKnownDS.sliceID)
        assert_equal(currDS.datasetType, currKnownDS.datasetType)
        
def test_HDFBatchProcess_Go():
    """Batch processor properly executes a pipeline.
    
    """
    bpHDF.go()
    
    results = [outputDirHDF / \
                Path('HeLaL_Control/HeLaL_Control_1/Localizations_A647_Pos0.csv'),
               outputDirHDF / \
                Path('HeLaS_Control/HeLaS_Control_2/Localizations_A647_Pos0.csv')]
                
    for currRes in results:
        df = pd.read_csv(str(currRes))
        
        # Verify that filters were applied during the processing
        ok_(df['loglikelihood'].max() <= 800,
            'Loglikelihood column has wrong values.')
        ok_(df['sigma'].max()         <= 200,
            'sigma column has wrong values.')
    
    # Verify that the atomic ID information was written correctly        
    atomIDs = [outputDirHDF / \
               Path('HeLaL_Control/HeLaL_Control_1/Localizations_A647_Pos0.json'),
               outputDirHDF / \
               Path('HeLaS_Control/HeLaS_Control_2/Localizations_A647_Pos0.json')]
               
    with open(str(atomIDs[0]), 'r') as infile:        
        info = json.load(infile)
        
    assert_equal(info[0], 'HeLaL_Control')
    assert_equal(info[1],               1)
    assert_equal(info[2], 'Localizations')
    assert_equal(info[3],            None)
    assert_equal(info[4],          'A647')
    assert_equal(info[5],            None)
    assert_equal(info[6],             [0])
    assert_equal(info[7],            None)
    
    with open(str(atomIDs[1]), 'r') as infile:        
        info = json.load(infile)

    assert_equal(info[0], 'HeLaS_Control')
    assert_equal(info[1],               2)
    assert_equal(info[2], 'Localizations')
    assert_equal(info[3],            None)
    assert_equal(info[4],          'A647')
    assert_equal(info[5],            None)
    assert_equal(info[6],             [0])
    assert_equal(info[7],            None)