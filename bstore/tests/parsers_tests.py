# © All rights reserved. ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Switzerland, Laboratory of Experimental Biophysics, 2016
# See the LICENSE.txt file for more details.

"""Unit tests for the parsers module.

Notes
-----
nosetests should be run in the directory just above the `tests` folder.
 
"""

__author__ = 'Kyle M. Douglass'
__email__ = 'kyle.m.douglass@gmail.com' 

from nose.tools import assert_equal, raises

# Register the test generic
from bstore  import config
config.__Registered_DatasetTypes__.append('TestType')
config.__Registered_DatasetTypes__.append('Localizations')
config.__Registered_DatasetTypes__.append('WidefieldImage')
config.__Registered_DatasetTypes__.append('LocMetadata')

from bstore import parsers
import bstore.datasetTypes.TestType as TestType
from pathlib import Path

testDataRoot = Path(config.__Path_To_Test_Data__)

class TestParser(parsers.Parser):
    @property
    def requiresConfig(self):
        return False
        
    def parseFilename(self):
        pass

def test_Parser_Attributes():
    """Will Parser accept and assign parameters to class attributes correctly?
    
    """
    dsIDs = {'prefix' : 'my_dataset', 'acqID' : 1,
             'channelID' : 'A647', 'posID' : (0,)}
    myDS  = TestType.TestType(datasetIDs = dsIDs)
    
    parser         = TestParser()
    parser.dataset = myDS
    assert_equal(parser.dataset.datasetIDs['acqID'],                  1)
    assert_equal(parser.dataset.datasetIDs['channelID'],         'A647')
    assert_equal(parser.dataset.datasetIDs['posID'],               (0,))
    assert_equal(parser.dataset.datasetIDs['prefix'],      'my_dataset')
    assert_equal(parser.dataset.datasetType,                 'TestType')

def test_FormatMap():
    """FormatMap provides a basic two-way hash table.
    
    """
    # Create an empty FormatMap
    testMap      = parsers.FormatMap()
    testMap['A'] = 'a'
    testMap['B'] = 'b'
    
    assert_equal(testMap['A'], 'a')
    assert_equal(testMap['a'], 'A')
    assert_equal(testMap['B'], 'b')
    assert_equal(testMap['b'], 'B')
    assert_equal(len(testMap),   2)
    
    del(testMap['b'])
    assert_equal(len(testMap),   1)
    
    # Tests undefined keys
    assert_equal(testMap['C'], 'C')

def test_FormatMap_Dict_Constructor():
    """FormatMap accepts a dict in its constructor.
    
    """
    # Create an empty FormatMap
    testMap      = parsers.FormatMap({'A' : 'a', 'B' : 'b'})
    
    assert_equal(testMap['A'], 'a')
    assert_equal(testMap['a'], 'A')
    assert_equal(testMap['B'], 'b')
    assert_equal(testMap['b'], 'B')
    assert_equal(len(testMap),   2)
    
    del(testMap['b'])
    assert_equal(len(testMap),   1)
    
    # Tests undefined keys
    assert_equal(testMap['C'], 'C')
    
def test_SimpleParser_ParseFilename_Localizations():
    """SimpleParser correctly converts localization files to Datasets.
    
    """
    # File number 1
    f = 'HeLaL_Control_1.csv'
    inputFile = testDataRoot / Path('parsers_test_files') \
                             / Path('SimpleParser/') / Path(f)
                             
    parser = parsers.SimpleParser()
    parser.parseFilename(inputFile)
    assert_equal(parser.dataset.datasetIDs['acqID'],                  1)
    assert_equal(parser.dataset.datasetIDs['prefix'],   'HeLaL_Control')
    assert_equal(parser.dataset.datasetType,            'Localizations')
    
    f = 'HeLaS_Control_2.csv'
    inputFile = testDataRoot / Path('parsers_test_files') \
                             / Path('SimpleParser/') / Path(f)
    parser = parsers.SimpleParser()
    parser.parseFilename(inputFile)
    assert_equal(parser.dataset.datasetIDs['acqID'],                  2)
    assert_equal(parser.dataset.datasetIDs['prefix'],   'HeLaS_Control')
    assert_equal(parser.dataset.datasetType,            'Localizations')
    
def test_SimpleParser_ParseFilename_LocMetadata():
    """SimpleParser correctly converts metadata files to Datasets.
    
    """
    # File number 1
    f = 'HeLaL_Control_1.txt'
    inputFile = testDataRoot / Path('parsers_test_files') \
                             / Path('SimpleParser/') / Path(f)
                             
    parser = parsers.SimpleParser()
    parser.parseFilename(inputFile, datasetType = 'LocMetadata')
    assert_equal(parser.dataset.datasetIDs['acqID'],                  1)
    assert_equal(parser.dataset.datasetIDs['prefix'],   'HeLaL_Control')
    assert_equal(parser.dataset.datasetType,              'LocMetadata')
    
    f = 'HeLaS_Control_2.txt'
    inputFile = testDataRoot / Path('parsers_test_files') \
                             / Path('SimpleParser/') / Path(f)
    parser = parsers.SimpleParser()
    parser.parseFilename(inputFile, datasetType = 'LocMetadata')
    assert_equal(parser.dataset.datasetIDs['acqID'],                  2)
    assert_equal(parser.dataset.datasetIDs['prefix'],   'HeLaS_Control')
    assert_equal(parser.dataset.datasetType,              'LocMetadata')
    
def test_SimpleParser_ParseFilename_WidefieldImage():
    """SimpleParser correctly converts widefield image files to Datasets.
    
    """
    # File number 1
    f = 'HeLaL_Control_1.tif'
    inputFile = testDataRoot / Path('parsers_test_files') \
                             / Path('SimpleParser/') / Path(f)
                             
    parser = parsers.SimpleParser()
    parser.parseFilename(inputFile, datasetType = 'WidefieldImage')
    assert_equal(parser.dataset.datasetIDs['acqID'],                  1)
    assert_equal(parser.dataset.datasetIDs['prefix'],   'HeLaL_Control')
    assert_equal(parser.dataset.datasetType,           'WidefieldImage')
    
    f = 'HeLaS_Control_2.tif'
    inputFile = testDataRoot / Path('parsers_test_files') \
                             / Path('SimpleParser/') / Path(f)
    parser = parsers.SimpleParser()
    parser.parseFilename(inputFile, datasetType = 'WidefieldImage')
    assert_equal(parser.dataset.datasetIDs['acqID'],                  2)
    assert_equal(parser.dataset.datasetIDs['prefix'],   'HeLaS_Control')
    assert_equal(parser.dataset.datasetType,           'WidefieldImage')

def test_SimpleParser_Read_Localizations():
    """SimpleParser correctly reads localization results.
    
    """
    f = 'HeLaL_Control_1.csv'
    inputFile = testDataRoot / Path('parsers_test_files') \
                             / Path('SimpleParser/') / Path(f)
                             
    parser = parsers.SimpleParser()
    parser.parseFilename(inputFile, datasetType = 'Localizations')
    parser.dataset.data = parser.dataset.readFromFile(inputFile)
    
    # Test a couple of the localization results
    assert_equal(parser.dataset.data['x'].iloc[0], 6770)
    assert_equal(parser.dataset.data['intensity'].iloc[0],4386.6)
    assert_equal(parser.dataset.data['x'].iloc[1], 7958.1)
  
def test_SimpleParser_Read_LocMetadata():
    """SimpleParser correctly reads metadata.
    
    """
    f = 'HeLaL_Control_1.txt'
    inputFile = testDataRoot / Path('parsers_test_files') \
                             / Path('SimpleParser/') / Path(f)
                             
    parser = parsers.SimpleParser()
    parser.parseFilename(inputFile, datasetType = 'LocMetadata')
    parser.dataset.data = parser.dataset.readFromFile(inputFile)
    
    # Test a couple of the metadata fields
    assert_equal(parser.dataset.data['StartFrame_sCMOS'], 50)
    assert_equal(parser.dataset.data['Width'], 927)
    
def test_SimpleParser_Read_WidefieldImage():
    """SimpleParser correctly reads metadata.
    
    """
    f = 'HeLaL_Control_1.tif'
    inputFile = testDataRoot / Path('parsers_test_files') \
                             / Path('SimpleParser/') / Path(f)
                             
    parser = parsers.SimpleParser()
    parser.parseFilename(inputFile, datasetType = 'WidefieldImage')
    parser.dataset.data = parser.dataset.readFromFile(inputFile)
    
    # Test the size of the widefield image and its first value
    assert_equal(parser.dataset.data.shape, (927, 927))
    assert_equal(parser.dataset.data[0, 0], 102)
    
def test_SimpleParser_GetDataset():
    """SimpleParser returns the correct Dataset.
    
    """
    f = 'HeLaL_Control_1.tif'
    inputFile = testDataRoot / Path('parsers_test_files') \
                             / Path('SimpleParser/') / Path(f)
                             
    parser = parsers.SimpleParser()
    parser.parseFilename(inputFile, datasetType = 'WidefieldImage')
    parser.dataset.data = parser.dataset.readFromFile(inputFile)
    
    # Test the size of the widefield image and its first value
    assert_equal(parser.dataset.datasetIDs['prefix'], 'HeLaL_Control')
    assert_equal(parser.dataset.data.shape, (927, 927))

@raises(parsers.ParserNotInitializedError) 
def test_SimpleParser_GetDataset_NotInitialized():
    """SimpleParser returns raises a not-initialized error.
    
    """                             
    parser = parsers.SimpleParser()
    parser.dataset
  
@raises(parsers.ParseFilenameFailure)
def test_SimpleParser_BadParse():
    """SimpleParser correctly catches errors during parsing.
    
    """
    f = 'HeLaL.tif' # No acqID; file shouldn't parse
                             
    parser = parsers.SimpleParser()
    parser.parseFilename(f, datasetType = 'WidefieldImage')
    
def test_PositionParser_ParseFilename():
    """PositionParser's full parseFilename() function works as expected.
    
    """
    f = 'HeLaL_Control_1.csv'
    inputFile = testDataRoot / Path('parsers_test_files') \
                             / Path('SimpleParser/') / Path(f)
                             
    parser = parsers.PositionParser(positionIDs = {0 : 'prefix',
                                                   1 : None, 2: 'acqID'})
    # Note: 'Control' will be dropped because it's surrounded by underscores
    parser.parseFilename(inputFile)
    
    assert_equal(parser.dataset.datasetIDs['acqID'],                  1)
    assert_equal(parser.dataset.datasetIDs['prefix'],           'HeLaL')
    assert_equal(parser.dataset.datasetType,            'Localizations')
    
    f = 'HeLaS_Control_2.csv'
    inputFile = testDataRoot / Path('parsers_test_files') \
                             / Path('SimpleParser/') / Path(f)
    parser.parseFilename(inputFile)
    
    assert_equal(parser.dataset.datasetIDs['acqID'],                  2)
    assert_equal(parser.dataset.datasetIDs['prefix'],           'HeLaS')
    assert_equal(parser.dataset.datasetType,            'Localizations')
    
def test_PositionParser_parse():
    """PositionParser correctly parses a number of different example filenames.
    
    """
    # filename, position ids, expected result
    f = [('HeLa_2',
          {0 : 'prefix', 1 : 'acqID'},
          {'prefix' : 'HeLa', 'acqID' : 2}),
         ('HeLa_A647_2',
          {0 : 'prefix', 1 : 'channelID', 2 : 'acqID'},
          {'prefix' : 'HeLa', 'channelID' : 'A647', 'acqID' : 2}),
         ('2016-12-11_Cos7_A647_5_4_3',
          {0 : 'dateID', 1 : 'prefix', 2 : 'channelID', 3 : 'posID',
           4 : 'sliceID', 5 : 'acqID'},
          {'dateID' : '2016-12-11', 'prefix' : 'Cos7', 'channelID' : 'A647',
          'posID' : 5, 'sliceID' : 4, 'acqID' : 3}),
         ('HeLa_1_MMStack_0',
          {0 : 'prefix', 1 : 'acqID', 2 : None, 3 : 'posID'},
          {'prefix' : 'HeLa', 'acqID' : 1, 'posID' : 0})]
          
    for currExample in f:
        parser = parsers.PositionParser(positionIDs = currExample[1])
        idDict = parser._parse(currExample[0])
                             
        for key, value in idDict.items():
            assert_equal(value, currExample[2][key])

@raises(parsers.ParseFilenameFailure)
def test_PositionParser_BadParse():
    """PositionParser correctly catches errors during parsing.
    
    """
    f = 'HeLaL.tif' # No acqID; file shouldn't parse
                             
    parser = parsers.PositionParser(positionIDs = {0 : 'prefix',
                                                   1 : None, 2: 'acqID'})
    # Note: There are more position IDs than there are actual positions in f
    parser.parseFilename(f)
                         
@raises(parsers.ParserNotInitializedError) 
def test_PositionParser_GetDataset_NotInitialized():
    """PositionParser returns raises a not-initialized error.
    
    """                             
    parser = parsers.PositionParser()
    parser.dataset