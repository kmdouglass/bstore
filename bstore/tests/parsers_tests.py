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

from bstore  import parsers, database
import bstore.datasetTypes.TestType as TestType
import bstore.datasetTypes.Localizations as Localizations
from pathlib import Path
from tifffile import TiffFile

testDataRoot = Path(config.__Path_To_Test_Data__)

class TestParser(parsers.Parser):
    def parseFilename():
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
    datasetType     = 'Localizations'
    
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
'''    
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
    
def test_MMParser_TiffFile():
    """MMParser loads an image as a TiffFile, not as a numpy array.
    
    """
    f = 'Cos7_A647_WF1_MMStack_Pos0.ome.tif'
    inputFile   = testDataRoot / Path('parsers_test_files') \
                               / Path('Cos7_A647_WF1/') / Path(f)
    datasetType = 'widefieldImage'
    
    mmParser = parsers.MMParser(readTiffTags = True)
    mmParser.parseFilename(inputFile, datasetType)
    ds = mmParser.getDatabaseAtom()
    
    ok_(isinstance(ds.data, TiffFile))
    assert_equal(ds.data.asarray().shape, (512, 512))
    
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
    
@raises(parsers.DatasetTypeError)    
def test_MMParser_Bad_Generic():
    """MMParser recognizes when a bad generic type is passed.
    
    """
    inputFile = Path('Cos7_Microtubules_A750_3_MMStack_Pos0_locResults.dat')
    
    parser = parsers.MMParser()
    parser.parseFilename(inputFile,
                         datasetType ='generic',
                         datasetTypeName = 'bogusType')
                        
def test_MMParser_Generic_GetDatabaseAtom():
    """MMParser returns a generic database atom.
    
    """
    inputFile = Path('Cos7_Microtubules_A750_3_MMStack_Pos0_locResults.dat')
    
    parser = parsers.MMParser()
    parser.parseFilename(inputFile,
                         datasetType ='generic',
                         datasetTypeName = 'TestType')
    dba = parser.getDatabaseAtom()
    assert_equal(dba.prefix, 'Cos7_Microtubules')
    assert_equal(dba.acqID,                    3)
    assert_equal(dba.datasetType,      'generic')
    assert_equal(dba.channelID,           'A750')
    assert_equal(dba.posID,                 (0,))
    assert_equal(dba.dateID,                None)
    assert_equal(dba.sliceID,               None)
    assert_equal(dba.datasetTypeName, 'TestType')
    
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
    
def test_SimpleParser_ParseFilename_LocResults():
    """SimpleParser correctly converts files to Datasets/DatabaseAtoms.
    
    """
    # File number 1
    f = 'HeLaL_Control_1.csv'
    inputFile = testDataRoot / Path('parsers_test_files') \
                             / Path('SimpleParser/') / Path(f)
                             
    parser = parsers.SimpleParser()
    parser.parseFilename(inputFile)
    assert_equal(parser.acqID,                  1)
    assert_equal(parser.channelID,           None)
    assert_equal(parser.posID,               None)
    assert_equal(parser.prefix,   'HeLaL_Control')
    assert_equal(parser.sliceID,             None)
    assert_equal(parser.datasetType, 'locResults')
    
    f = 'HeLaS_Control_2.csv'
    inputFile = testDataRoot / Path('parsers_test_files') \
                             / Path('SimpleParser/') / Path(f)
    parser = parsers.SimpleParser()
    parser.parseFilename(inputFile)
    assert_equal(parser.acqID,                  2)
    assert_equal(parser.channelID,           None)
    assert_equal(parser.posID,               None)
    assert_equal(parser.prefix,   'HeLaS_Control')
    assert_equal(parser.sliceID,             None)
    assert_equal(parser.datasetType, 'locResults')
    
def test_SimpleParser_ParseFilename_Metadata():
    """SimpleParser correctly converts files to Datasets/DatabaseAtoms.
    
    """
    # File number 1
    f = 'HeLaL_Control_1.txt'
    inputFile = testDataRoot / Path('parsers_test_files') \
                             / Path('SimpleParser/') / Path(f)
                             
    parser = parsers.SimpleParser()
    parser.parseFilename(inputFile, datasetType = 'locMetadata')
    assert_equal(parser.acqID,                   1)
    assert_equal(parser.channelID,            None)
    assert_equal(parser.posID,                None)
    assert_equal(parser.prefix,    'HeLaL_Control')
    assert_equal(parser.sliceID,              None)
    assert_equal(parser.datasetType, 'locMetadata')
    
    f = 'HeLaS_Control_2.txt'
    inputFile = testDataRoot / Path('parsers_test_files') \
                             / Path('SimpleParser/') / Path(f)
    parser = parsers.SimpleParser()
    parser.parseFilename(inputFile, datasetType = 'locMetadata')
    assert_equal(parser.acqID,                   2)
    assert_equal(parser.channelID,            None)
    assert_equal(parser.posID,                None)
    assert_equal(parser.prefix,    'HeLaS_Control')
    assert_equal(parser.sliceID,              None)
    assert_equal(parser.datasetType, 'locMetadata')
    
def test_SimpleParser_ParseFilename_WidefieldImage():
    """SimpleParser correctly converts files to Datasets/DatabaseAtoms.
    
    """
    # File number 1
    f = 'HeLaL_Control_1.txt'
    inputFile = testDataRoot / Path('parsers_test_files') \
                             / Path('SimpleParser/') / Path(f)
                             
    parser = parsers.SimpleParser()
    parser.parseFilename(inputFile, datasetType = 'widefieldImage')
    assert_equal(parser.acqID,                      1)
    assert_equal(parser.channelID,               None)
    assert_equal(parser.posID,                   None)
    assert_equal(parser.prefix,       'HeLaL_Control')
    assert_equal(parser.sliceID,                 None)
    assert_equal(parser.datasetType, 'widefieldImage')
    
    f = 'HeLaS_Control_2.txt'
    inputFile = testDataRoot / Path('parsers_test_files') \
                             / Path('SimpleParser/') / Path(f)
    parser = parsers.SimpleParser()
    parser.parseFilename(inputFile, datasetType = 'widefieldImage')
    assert_equal(parser.acqID,                      2)
    assert_equal(parser.channelID,               None)
    assert_equal(parser.posID,                   None)
    assert_equal(parser.prefix,       'HeLaS_Control')
    assert_equal(parser.sliceID,                 None)
    assert_equal(parser.datasetType, 'widefieldImage')
    
def test_SimpleParser_Read_LocResults():
    """SimpleParser correctly reads localization results.
    
    """
    f = 'HeLaL_Control_1.csv'
    inputFile = testDataRoot / Path('parsers_test_files') \
                             / Path('SimpleParser/') / Path(f)
                             
    parser = parsers.SimpleParser()
    parser.parseFilename(inputFile, datasetType = 'locResults')
    
    # Test a couple of the localization results
    assert_equal(parser.data['x'].iloc[0], 6770)
    assert_equal(parser.data['intensity'].iloc[0],4386.6)
    assert_equal(parser.data['x'].iloc[1], 7958.1)
    
def test_SimpleParser_Read_Metadata():
    """SimpleParser correctly reads metadata.
    
    """
    f = 'HeLaL_Control_1.txt'
    inputFile = testDataRoot / Path('parsers_test_files') \
                             / Path('SimpleParser/') / Path(f)
                             
    parser = parsers.SimpleParser()
    parser.parseFilename(inputFile, datasetType = 'locMetadata')
    
    # Test a couple of the metadata fields
    assert_equal(parser.data['StartFrame_sCMOS'], 50)
    assert_equal(parser.data['Width'], 927)
    
def test_SimpleParser_Read_WidefieldImage():
    """SimpleParser correctly reads metadata.
    
    """
    f = 'HeLaL_Control_1.tif'
    inputFile = testDataRoot / Path('parsers_test_files') \
                             / Path('SimpleParser/') / Path(f)
                             
    parser = parsers.SimpleParser()
    parser.parseFilename(inputFile, datasetType = 'widefieldImage')
    
    # Test the size of the widefield image and its first value
    assert_equal(parser.data.shape, (927, 927))
    assert_equal(parser.data[0, 0], 102)
    
def test_SimpleParser_GetDatabaseAtom():
    """SimpleParser returns a correct DatabaseAtom.
    
    """
    f = 'HeLaL_Control_1.tif'
    inputFile = testDataRoot / Path('parsers_test_files') \
                             / Path('SimpleParser/') / Path(f)
                             
    parser = parsers.SimpleParser()
    parser.parseFilename(inputFile, datasetType = 'widefieldImage')
    
    # Test the size of the widefield image and its first value
    ds = parser.getDatabaseAtom()
    assert_equal(ds.prefix, 'HeLaL_Control')
    assert_equal(ds.data.shape, (927, 927))

@raises(parsers.ParserNotInitializedError) 
def test_SimpleParser_GetDatabaseAtom_NotInitialized():
    """SimpleParser returns raises a not-initialized error.
    
    """                             
    parser = parsers.SimpleParser()
    parser.getDatabaseAtom()
    
@raises(Exception)
def test_SimpleParser_BadParse():
    """SimpleParser correctly catches errors during parsing.
    
    """
    f = 'HeLaL.tif' # No acqID; file shouldn't parse
                             
    parser = parsers.SimpleParser()
    parser.parseFilename(f, datasetType = 'widefieldImage')
    
@raises(ValueError)
def test_Simple_Parser_No_Generics():
    """Simple Parser will not parse generics.
    
    """
    parser = parsers.SimpleParser()
    parser.parseFilename('File', datasetType = 'generic')
'''