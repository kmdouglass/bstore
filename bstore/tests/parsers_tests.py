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

from nose.tools import assert_equal, raises, ok_

# Register the test generic
from bstore  import config
config.__Registered_DatasetTypes__.append('TestType')
config.__Registered_DatasetTypes__.append('Localizations')
config.__Registered_DatasetTypes__.append('WidefieldImage')
config.__Registered_DatasetTypes__.append('LocMetadata')

from bstore import parsers, database
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

def test_MMParser_ParseGenericFile():
    """Will MMParser properly extract the acquisition information?
    
    """
    inputFilename   = 'Cos7_Microtubules_A647_3_MMStack_Pos0_locResults.dat'
    datasetType     = 'TestType'
    
    mmParser = parsers.MMParser()
    mmParser.parseFilename(inputFilename, datasetType)
    assert_equal(mmParser.dataset.datasetIDs['acqID'],                    3)
    assert_equal(mmParser.dataset.datasetIDs['channelID'],           'A647')
    assert_equal(mmParser.dataset.datasetIDs['posID'],                 (0,))
    assert_equal(mmParser.dataset.datasetIDs['prefix'], 'Cos7_Microtubules')
    assert_equal(mmParser.dataset.datasetType,                   'TestType')

@raises(parsers.DatasetTypeError)
def test_MMParser_UnregisteredType_WillNot_Parse():
    """Unregistered datasetTypes should raise an error if parsed.
    
    """
    inputFilename   = 'Cos7_Microtubules_A647_3_MMStack_Pos0_locResults.dat'
    datasetType     = 'Localizations_Cool'
    
    mmParser = parsers.MMParser()
    mmParser.parseFilename(inputFilename, datasetType)
 
def test_MMParser_Channel_Underscores():
    """Will MMParser extract the prefix and channel with weird underscores?
    
    """
    inputFilename = ['Cos7_Microtubules_Cy5_3_MMStack_Pos0_locResults.dat',
                     '_Cy5_Cos7_Microtubules_3_MMStack_Pos0_locResults.dat',
                     'Cy5_Cos7_Microtubules_3_MMStack_Pos0_locResults.dat',
                     'Cos7_Cy5_Microtubules_3_MMStack_Pos0_locResults.dat',
                     'Cos7_MicrotubulesCy5_3_MMStack_Pos0_locResults.dat',
                     'Cos7_Microtubules__Cy5_3_MMStack_Pos0_locResults.dat',
                     'Cos7___Microtubules__Cy5_3_MMStack_Pos0_locResults.dat']
    datasetType   = 'TestType'
    
    mmParser = parsers.MMParser()
    for currFilename in inputFilename:
        mmParser.parseFilename(currFilename, datasetType)
        assert_equal(mmParser.dataset.datasetIDs['acqID'],                   3)
        assert_equal(mmParser.dataset.datasetIDs['channelID'],           'Cy5')
        assert_equal(mmParser.dataset.datasetIDs['posID'],                (0,))
        assert_equal(mmParser.dataset.datasetIDs['prefix'],'Cos7_Microtubules')
        assert_equal(mmParser.dataset.datasetType,                  'TestType')
  
def test_MMParser_Attributes_NoChannel():
    """Will MMParser extract the acquisition info w/o a channel identifier?
    
    """
    inputFilename   = 'Cos7_Microtubules_12_MMStack_Pos1_locResults.dat'
    datasetType     = 'TestType'
    
    mmParser = parsers.MMParser()
    mmParser.parseFilename(inputFilename, datasetType)
    assert_equal(mmParser.dataset.datasetIDs['acqID'],                      12)
    assert_equal(mmParser.dataset.datasetIDs['posID'],                    (1,))
    assert_equal(mmParser.dataset.datasetIDs['prefix'],    'Cos7_Microtubules')
    assert_equal(mmParser.dataset.datasetType,                      'TestType')
    assert_equal(mmParser.dataset.datasetIDs['channelID'],                None)
   
def test_MMParser_Attributes_NoPosition():
    """Will MMParser extract the acquisition info w/o a position identifier?
    
    """
    inputFilename   = 'Cos7_Microtubules_12_MMStack_locResults.dat'
    datasetType     = 'TestType'
    
    mmParser = parsers.MMParser()
    mmParser.parseFilename(inputFilename, datasetType)
    assert_equal(mmParser.dataset.datasetIDs['acqID'],                      12)
    assert_equal(mmParser.dataset.datasetIDs['posID'],                    None)
    assert_equal(mmParser.dataset.datasetIDs['prefix'],    'Cos7_Microtubules')
    assert_equal(mmParser.dataset.datasetType,                      'TestType')
    assert_equal(mmParser.dataset.datasetIDs['channelID'],                None)
  
def test_MMParser_Attributes_MultipleXY():
    """Will MMParser extract multiple xy positions?
    
    """
    inputFilename   = 'HeLa_Actin_4_MMStack_1-Pos_012_003_locResults.dat'
    datasetType     = 'TestType'
    
    mmParser = parsers.MMParser()
    mmParser.parseFilename(inputFilename, datasetType)
    assert_equal(mmParser.dataset.datasetIDs['acqID'],             4)
    assert_equal(mmParser.dataset.datasetIDs['channelID'],      None)
    assert_equal(mmParser.dataset.datasetIDs['posID'],        (12,3))
    assert_equal(mmParser.dataset.datasetIDs['prefix'], 'HeLa_Actin')
    assert_equal(mmParser.dataset.datasetIDs['sliceID'],        None)
    assert_equal(mmParser.dataset.datasetType,            'TestType')
 
def test_MMParser_Path_Input():
    """Will MMParser properly convert Path inputs to strings?
    
    """
    inputFile = \
        Path('results/Cos7_Microtubules_A750_3_MMStack_Pos0_locResults.dat')
    datasetType = 'TestType'
    
    mmParser = parsers.MMParser()
    mmParser.parseFilename(inputFile, datasetType)
    assert_equal(mmParser.dataset.datasetIDs['acqID'],                       3)
    assert_equal(mmParser.dataset.datasetIDs['channelID'],              'A750')
    assert_equal(mmParser.dataset.datasetIDs['posID'],                    (0,))
    assert_equal(mmParser.dataset.datasetIDs['prefix'],    'Cos7_Microtubules')
    assert_equal(mmParser.dataset.datasetIDs['sliceID'],                  None)
    assert_equal(mmParser.dataset.datasetType,                      'TestType')
                                                                    
def test_MMParser_Widefield_Attributes():
    """Will MMParser properly extract information from a widefield image?
    
    """
    f = [
        'HeLa_Control_A647_WF13_MMStack_Pos0.ome.tif',
        'HeLa_WF13_Control_A647_MMStack_Pos0.ome.tif',
         'WF13_HeLa_Control_A647_MMStack_Pos0.ome.tif',
        'HeLa_Control_A647_WF13__MMStack_Pos0.ome.tif',
        '_WF13_HeLa_Control_A647_MMStack_Pos0.ome.tif',
        '_WF13_HeLa_Control_A647_MMStack_Pos0.ome.tif',
        'HeLa_Control_A647_WF13_MMStack_Pos0.ome.tif',
        'HeLa_Control_A647_WF_13_MMStack_Pos0.ome.tif',
        'HeLa_WF__13_Control_A647_MMStack_Pos0.ome.tif'
    ]    
    
    mmParser = parsers.MMParser()
    for filename in f:
        mmParser.parseFilename(filename, 'WidefieldImage')
        assert_equal(mmParser.dataset.datasetIDs['acqID'],                  13)
        assert_equal(mmParser.dataset.datasetIDs['channelID'],          'A647')
        assert_equal(mmParser.dataset.datasetIDs['posID'],                (0,))
        assert_equal(mmParser.dataset.datasetIDs['prefix'],     'HeLa_Control')
        assert_equal(mmParser.dataset.datasetIDs['sliceID'],              None)
        assert_equal(mmParser.dataset.datasetType,            'WidefieldImage')
    
def test_MMParser_Widefield_NoChannel():
    """Will MMParser properly extract widefield info w/o a channel?
    
    """
    f = [
        'HeLa_Control_WF13_MMStack_Pos0.ome.tif',
        'HeLa_WF13_Control_MMStack_Pos0.ome.tif',
         'WF13_HeLa_Control_MMStack_Pos0.ome.tif',
        'HeLa_Control_WF13__MMStack_Pos0.ome.tif',
        '_WF13_HeLa_Control_MMStack_Pos0.ome.tif',
        '_WF13_HeLa_Control_MMStack_Pos0.ome.tif',
        'HeLa_Control_WF13_MMStack_Pos0.ome.tif',
        'HeLa_Control_WF_13_MMStack_Pos0.ome.tif',
        'HeLa_WF__13_Control_MMStack_Pos0.ome.tif'
    ]    
    
    mmParser = parsers.MMParser()
    for filename in f:
        mmParser.parseFilename(filename, 'WidefieldImage')
        assert_equal(mmParser.dataset.datasetIDs['acqID'],                  13)
        assert_equal(mmParser.dataset.datasetIDs['channelID'],            None)
        assert_equal(mmParser.dataset.datasetIDs['posID'],                (0,))
        assert_equal(mmParser.dataset.datasetIDs['prefix'],     'HeLa_Control')
        assert_equal(mmParser.dataset.datasetIDs['sliceID'],              None)
        assert_equal(mmParser.dataset.datasetType,            'WidefieldImage')
   
def test_MMParser_Widefield_Bizarre_Underscores():
    """Will MMParser correctly parse this name with bizarre underscores?
    
    """
    filename = '__HeLa_Control__FISH___WF__173_MMStack_Pos0.ome.tif'
    
    mmParser = parsers.MMParser()
    mmParser.parseFilename(filename, 'WidefieldImage')
    assert_equal(mmParser.dataset.datasetIDs['acqID'],                     173)
    assert_equal(mmParser.dataset.datasetIDs['channelID'],                None)
    assert_equal(mmParser.dataset.datasetIDs['posID'],                    (0,))
    assert_equal(mmParser.dataset.datasetIDs['prefix'],    'HeLa_Control_FISH')
    assert_equal(mmParser.dataset.datasetIDs['sliceID'],                  None)
    assert_equal(mmParser.dataset.datasetType,                'WidefieldImage')
    
def test_MMParser_Dataset():
    """MMParser returns the correct Dataset.
    
    """
    f = 'HeLa_Control_A750_1_MMStack_Pos0_locMetadata.json'
    inputFile = testDataRoot / Path('parsers_test_files') / Path(f)
    datasetType = 'LocMetadata'
    
    mmParser = parsers.MMParser()
    mmParser.parseFilename(inputFile, datasetType)
    ds = mmParser.dataset
    
    ok_(isinstance(ds, database.Dataset))
    assert_equal(ds.datasetIDs['acqID'],                                     1)
    assert_equal(ds.datasetIDs['channelID'],                            'A750')
    assert_equal(ds.datasetIDs['posID'],                                  (0,))
    assert_equal(ds.datasetIDs['prefix'],                       'HeLa_Control')
    assert_equal(ds.datasetIDs['sliceID'],                                None)
    assert_equal(ds.datasetType,                                 'LocMetadata')
    
    # Test a few metadata entries
    ds.data = ds.readFromFile(inputFile)
    assert_equal(ds.data['Slices'],                                          1)
    assert_equal(ds.data['InitialPositionList'],                          None)
    assert_equal(ds.data['PixelType'],                                 'GRAY8')
    assert_equal(ds.data['Positions'],                                       1)

@raises(parsers.ParserNotInitializedError)    
def test_MMParser_Uninitialized():
    """Will MMParser throw an error when getDatabaseAtom is prematurely run?
    
    """
    mmParser = parsers.MMParser()
    mmParser.dataset
 
@raises(parsers.ParserNotInitializedError)    
def test_MMParser_Uninitialized_After_Use():
    """Will MMParser throw an error if getDatabaseAtom is run after uninit'ing?
    
    """
    f = 'HeLa_Control_A750_1_MMStack_Pos0_locMetadata.json'
    inputFile   = testDataRoot / Path('parsers_test_files') / Path(f)
    datasetType = 'LocMetadata'
    
    mmParser = parsers.MMParser()
    mmParser.parseFilename(inputFile, datasetType)
    mmParser.dataset
    
    mmParser.initialized = False
    mmParser.dataset

   
def test_MMParser_Widefield_Data():
    """MMParser correctly loads widefield image data.
    
    """
    f = 'Cos7_A647_WF1_MMStack_Pos0.ome.tif'
    inputFile   = testDataRoot / Path('parsers_test_files') \
                               / Path('Cos7_A647_WF1/') / Path(f)
    datasetType = 'WidefieldImage'
    
    mmParser = parsers.MMParser()
    mmParser.parseFilename(inputFile, datasetType)
    
    ds      = mmParser.dataset   
    ds.data = ds.readFromFile(inputFile)
    
    assert_equal(ds.data.shape, (512, 512))

   
def test_MMParser_ConvertsSpacesToUnderscores():
    """The MMParser will convert spaces in the prefix to underscores.
    
    """
    # Note the space in prefix!
    f = 'my dataset_A647_1_MMStack_Pos0_locResults.dat'    
    
    parser = parsers.MMParser()
    parser.parseFilename(f, 'TestType')
    assert_equal(parser.dataset.datasetIDs['acqID'],                  1)
    assert_equal(parser.dataset.datasetIDs['channelID'],         'A647')
    assert_equal(parser.dataset.datasetIDs['posID'],               (0,))
    
    # The space should now be an underscore
    assert_equal(parser.dataset.datasetIDs['prefix'],      'my_dataset')
    assert_equal(parser.dataset.datasetType,                 'TestType')

@raises(parsers.ParseFilenameFailure)    
def test_MMParser_ParseFailure():
    """MMParser raises a ParseFilenameFailure error when the filename is bad.
    
    """
    f = 'blablabla 214'
    
    parser = parsers.MMParser()
    parser.parseFilename(f, 'TestType')

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