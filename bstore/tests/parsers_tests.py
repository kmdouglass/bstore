"""Unit tests for the parsers module.

Notes
-----
nosetests should be run in the directory just above the `tests` folder.
 
"""

__author__ = 'Kyle M. Douglass'
__email__ = 'kyle.m.douglass@gmail.com' 

from nose.tools import *
from bstore  import parsers, database
from bstore  import config
from pathlib import Path

testDataRoot = Path(config.__Path_To_Test_Data__)

class TestParser(parsers.Parser):
    @property
    def data(self):
        pass
    
    @property
    def getDatabaseAtom(self):
        pass
    
    @property
    def uninitialized(self):
        pass
    
    def parseFilename():
        pass

def test_Parser_Attributes():
    """Will Parser accept and assign parameters to class attributes correctly?
    
    """
    acqID       =            1
    channelID   =       'A647'
    dateID      =         None
    posID       =         (0,) # Note that this is a tuple!
    prefix      = 'my_dataset'
    sliceID     =         None
    datasetType = 'locResults'    
    
    parser = TestParser(prefix, acqID, datasetType,
                        channelID = channelID, dateID = dateID,
                        posID = posID, sliceID = sliceID)
    assert_equal(parser.acqID,                  1)
    assert_equal(parser.channelID,         'A647')
    assert_equal(parser.posID,               (0,))
    assert_equal(parser.prefix,      'my_dataset')
    assert_equal(parser.sliceID,             None)
    assert_equal(parser.datasetType, 'locResults')

@raises(parsers.DatasetError)    
def test_Parser_datasetType():
    """Will Parser detect a bad value for datasetType?
    
    """
    acqID       =            1
    channelID   =       'A647'
    dateID      =         None
    posID       =         (0,)
    prefix      = 'my_dataset'
    sliceID     =         None
    datasetType = 'locRseults' # misspelled
    

    parser = TestParser(prefix, acqID, datasetType,
                        channelID = channelID, dateID = dateID,
                        posID = posID, sliceID = sliceID)
    
def test_Parser_getBasicInfo():
    """Will getBasicInfo return the right values?
    
    """
    acqID       =             3
    channelID   =        'A750'
    dateID      =          None
    posID       =         (0,1)
    prefix      =        'HeLa'
    sliceID     =          None
    datasetType = 'locMetadata'
    
    parser = TestParser(prefix, acqID, datasetType,
                        channelID = channelID, dateID = dateID,
                        posID = posID, sliceID = sliceID)
    basicInfo = parser.getBasicInfo()
    assert_equal(basicInfo['acqID'],                    3)
    assert_equal(basicInfo['channelID'],           'A750')
    assert_equal(basicInfo['posID'],                (0,1))
    assert_equal(basicInfo['prefix'],              'HeLa')
    assert_equal(basicInfo['sliceID'],               None)
    assert_equal(basicInfo['datasetType'],  'locMetadata')
    
def test_MMParser_LocResults_Attributes():
    """Will MMParser properly extract the acquisition information?
    
    """
    inputFilename   = 'Cos7_Microtubules_A647_3_MMStack_Pos0_locResults.dat'
    datasetType     = 'locResults'
    
    mmParser = parsers.MMParser()
    mmParser.parseFilename(inputFilename, datasetType)
    assert_equal(mmParser.acqID,                              3)
    assert_equal(mmParser.channelID,                     'A647')
    assert_equal(mmParser.dateID,                          None)
    assert_equal(mmParser.posID,                           (0,))
    assert_equal(mmParser.prefix,           'Cos7_Microtubules')
    assert_equal(mmParser.sliceID,                         None)
    assert_equal(mmParser.datasetType,             'locResults')
    
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
    datasetType   = 'locResults'
    
    mmParser = parsers.MMParser()
    for currFilename in inputFilename:
        mmParser.parseFilename(currFilename, datasetType)
        assert_equal(mmParser.acqID,                              3)
        assert_equal(mmParser.channelID,                      'Cy5')
        assert_equal(mmParser.posID,                           (0,))
        assert_equal(mmParser.prefix,           'Cos7_Microtubules')
        assert_equal(mmParser.sliceID,                         None)
        assert_equal(mmParser.datasetType,             'locResults')
    
def test_MMParser_Attributes_NoChannel():
    """Will MMParser extract the acquisition info w/o a channel identifier?
    
    """
    inputFilename   = 'Cos7_Microtubules_12_MMStack_Pos1_locResults.dat'
    datasetType     = 'locResults'
    
    mmParser = parsers.MMParser()
    mmParser.parseFilename(inputFilename, datasetType)
    assert_equal(mmParser.acqID,                        12)
    assert_equal(mmParser.channelID,                  None)
    assert_equal(mmParser.posID,                      (1,))
    assert_equal(mmParser.prefix,      'Cos7_Microtubules')
    assert_equal(mmParser.sliceID,                    None)
    assert_equal(mmParser.datasetType,        'locResults')
    
def test_MMParser_Attributes_NoPosition():
    """Will MMParser extract the acquisition info w/o a position identifier?
    
    """
    inputFilename   = 'Cos7_Microtubules_12_MMStack_locResults.dat'
    datasetType     = 'locResults'
    
    mmParser = parsers.MMParser()
    mmParser.parseFilename(inputFilename, datasetType)
    assert_equal(mmParser.acqID,                        12)
    assert_equal(mmParser.channelID,                  None)
    assert_equal(mmParser.posID,                      None)
    assert_equal(mmParser.prefix,      'Cos7_Microtubules')
    assert_equal(mmParser.sliceID,                    None)
    assert_equal(mmParser.datasetType,        'locResults')
    
def test_MMParser_Attributes_MultipleXY():
    """Will MMParser extract multiple xy positions?
    
    """
    inputFilename   = 'HeLa_Actin_4_MMStack_1-Pos_012_003_locResults.dat'
    datasetType     = 'locResults'
    
    mmParser = parsers.MMParser()
    mmParser.parseFilename(inputFilename, datasetType)
    assert_equal(mmParser.acqID,                        4)
    assert_equal(mmParser.channelID,                  None)
    assert_equal(mmParser.posID,                    (12,3))
    assert_equal(mmParser.prefix,             'HeLa_Actin')
    assert_equal(mmParser.sliceID,                    None)
    assert_equal(mmParser.datasetType,        'locResults')
    
  
def test_MMParser_Path_Input():
    """Will MMParser properly convert Path inputs to strings?
    
    """
    inputFile = \
        Path('results/Cos7_Microtubules_A750_3_MMStack_Pos0_locResults.dat')
    datasetType = 'locResults'
    
    mmParser = parsers.MMParser()
    mmParser.parseFilename(inputFile, datasetType)
    assert_equal(mmParser.acqID,                              3)
    assert_equal(mmParser.channelID,                     'A750')
    assert_equal(mmParser.posID,                           (0,))
    assert_equal(mmParser.prefix,           'Cos7_Microtubules')
    assert_equal(mmParser.sliceID,                         None)
    assert_equal(mmParser.datasetType,             'locResults')
    
def test_MMParser_Metadata():
    """Will MMParser properly read a metadata file with double position info?
    
    """
    f = 'bacteria_HaloInduced_A647_1_MMStack_1-Pos_002_002_locMetadata.json'
    inputFile   = testDataRoot / Path('parsers_test_files') / Path(f)
    datasetType = 'locMetadata'
    
    mmParser = parsers.MMParser()
    mmParser.parseFilename(inputFile, datasetType)
    assert_equal(mmParser.acqID,                                            1)
    assert_equal(mmParser.channelID,                                   'A647')
    assert_equal(mmParser.posID,                                        (2,2))
    assert_equal(mmParser.prefix,                      'bacteria_HaloInduced')
    assert_equal(mmParser.sliceID,                                       None)
    assert_equal(mmParser.datasetType,                          'locMetadata')
    assert_equal(mmParser.data['InitialPositionList']['Label'],
                                                              '1-Pos_002_002')
                                                              
def test_MMParser_Metadata_NoPosition_Metadata():
    """Will MMParser properly read a metadata file with empty position info?
    
    """
    # Note that the json entry for position information is empty in this file!
    f = 'HeLa_Control_A750_1_MMStack_Pos0_locMetadata.json'
    inputFile   = testDataRoot / Path('parsers_test_files') / Path(f)
    datasetType = 'locMetadata'
    
    mmParser = parsers.MMParser()
    mmParser.parseFilename(inputFile, datasetType)
    assert_equal(mmParser.acqID,                                            1)
    assert_equal(mmParser.channelID,                                   'A750')
    assert_equal(mmParser.posID,                                         (0,))
    assert_equal(mmParser.prefix,                              'HeLa_Control')
    assert_equal(mmParser.sliceID,                                       None)
    assert_equal(mmParser.datasetType,                          'locMetadata')
    assert_equal(mmParser.data['InitialPositionList'],                   None)
    
def test_MMParser_Metadata_SinglePosition():
    """Will MMParser properly read a metadata file with a single position?
    
    """
    # Note that the json entry for position information is empty in this file!
    f = 'HeLa_Control_A750_2_MMStack_Pos0_locMetadata.json'
    inputFile   = testDataRoot / Path('parsers_test_files') / Path(f)
    datasetType = 'locMetadata'
    
    mmParser = parsers.MMParser()
    mmParser.parseFilename(inputFile, datasetType)
    assert_equal(mmParser.acqID,                                            2)
    assert_equal(mmParser.channelID,                                   'A750')
    assert_equal(mmParser.posID,                                         (0,))
    assert_equal(mmParser.prefix,                              'HeLa_Control')
    assert_equal(mmParser.sliceID,                                       None)
    assert_equal(mmParser.datasetType,                          'locMetadata')
    assert_equal(mmParser.data['InitialPositionList']['Label'],        'Pos0')
    
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
        mmParser.parseFilename(filename, 'widefieldImage')
        assert_equal(mmParser.acqID,                                        13)
        assert_equal(mmParser.channelID,                                'A647')
        assert_equal(mmParser.posID,                                      (0,))
        assert_equal(mmParser.prefix,                           'HeLa_Control')
        assert_equal(mmParser.sliceID,                                    None)
        assert_equal(mmParser.datasetType,                    'widefieldImage')
    
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
        mmParser.parseFilename(filename, 'widefieldImage')
        assert_equal(mmParser.acqID,                                        13)
        assert_equal(mmParser.channelID,                                  None)
        assert_equal(mmParser.posID,                                      (0,))
        assert_equal(mmParser.prefix,                           'HeLa_Control')
        assert_equal(mmParser.sliceID,                                    None)
        assert_equal(mmParser.datasetType,                    'widefieldImage')
        
def test_MMParser_Widefield_Bizarre_Underscores():
    """Will MMParser correctly parse this name with bizarre underscores?
    
    """
    filename = '__HeLa_Control__FISH___WF__173_MMStack_Pos0.ome.tif'
    
    mmParser = parsers.MMParser()
    mmParser.parseFilename(filename, 'widefieldImage')
    assert_equal(mmParser.acqID,                                           173)
    assert_equal(mmParser.channelID,                                      None)
    assert_equal(mmParser.posID,                                          (0,))
    assert_equal(mmParser.prefix,                          'HeLa_Control_FISH')
    assert_equal(mmParser.sliceID,                                        None)
    assert_equal(mmParser.datasetType,                        'widefieldImage')
    
def test_MMParser_DatabaseAtom():
    """MMParser returns the correct DatabaseAtom.
    
    """
    f = 'HeLa_Control_A750_1_MMStack_Pos0_locMetadata.json'
    inputFile = testDataRoot / Path('parsers_test_files') / Path(f)
    datasetType = 'locMetadata'
    
    mmParser = parsers.MMParser()
    mmParser.parseFilename(inputFile, datasetType)
    dbAtom   = mmParser.getDatabaseAtom()
    
    ok_(isinstance(dbAtom, database.DatabaseAtom), ('Wrong type returned. '
                                                    'dbAtom should be a '
                                                    'DatabaseAtom.'))
    assert_equal(dbAtom.acqID,                                               1)
    assert_equal(dbAtom.channelID,                                      'A750')
    assert_equal(dbAtom.posID,                                            (0,))
    assert_equal(dbAtom.prefix,                                 'HeLa_Control')
    assert_equal(dbAtom.sliceID,                                          None)
    assert_equal(dbAtom.datasetType,                             'locMetadata')
    
    # Test a few metadata entries    
    assert_equal(dbAtom.data['Slices'],                                      1)
    assert_equal(dbAtom.data['InitialPositionList'],                      None)
    assert_equal(dbAtom.data['PixelType'],                             'GRAY8')
    assert_equal(dbAtom.data['Positions'],                                   1)

@raises(parsers.ParserNotInitializedError)    
def test_MMParser_Uninitialized():
    """Will MMParser throw an error when getDatabaseAtom is prematurely run?
    
    """
    mmParser = parsers.MMParser()
    mmParser.getDatabaseAtom()
    
@raises(parsers.ParserNotInitializedError)    
def test_MMParser_Uninitialized_After_Use():
    """Will MMParser throw an error if getDatabaseAtom is run after uninit'ing?
    
    """
    f = 'HeLa_Control_A750_1_MMStack_Pos0_locMetadata.json'
    inputFile   = testDataRoot / Path('parsers_test_files') / Path(f)
    datasetType = 'locMetadata'
    
    mmParser = parsers.MMParser()
    mmParser.parseFilename(inputFile, datasetType)
    mmParser.getDatabaseAtom()
    
    mmParser.uninitialized = True
    mmParser.getDatabaseAtom()
    
def test_MMParser_Widefield_Data():
    """MMParser correctly loads widefield image data.
    
    """
    f = 'Cos7_A647_WF1_MMStack_Pos0.ome.tif'
    inputFile   = testDataRoot / Path('parsers_test_files') \
                               / Path('Cos7_A647_WF1/') / Path(f)
    datasetType = 'widefieldImage'
    
    mmParser = parsers.MMParser()
    mmParser.parseFilename(inputFile, datasetType)
    ds = mmParser.getDatabaseAtom()    
    
    assert_equal(ds.data.shape, (512, 512))
    
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
    
def test_MMParser_ConvertsSpacesToUnderscores():
    """The MMParser will convert spaces in the prefix to underscores.
    
    """
    acqID       =            1
    channelID   =       'A647'
    dateID      =        None,
    posID       =         (0,) 
    prefix      = 'my dataset' # Note the space in the name!
    sliceID     =         None
    datasetType = 'locResults'    
    
    parser = TestParser(prefix, acqID, datasetType,
                        channelID = channelID, dateID = dateID,
                        posID = posID, sliceID = sliceID)
    assert_equal(parser.acqID,                  1)
    assert_equal(parser.channelID,         'A647')
    assert_equal(parser.posID,               (0,))
    assert_equal(parser.prefix,      'my_dataset') # Note the underscore
    assert_equal(parser.sliceID,             None)
    assert_equal(parser.datasetType, 'locResults')