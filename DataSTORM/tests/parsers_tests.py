from nose.tools import *
from DataSTORM  import parsers
from pathlib    import Path

def test_Parser_Attributes():
    """Will Paraser accept and assign parameters to class attributes correctly?
    
    """
    acqID       =            1
    channelID   =       'A647'
    posID       =         (0,) # Note that this is a tuple!
    prefix      = 'my_dataset'
    sliceID     =         None
    datasetType = 'locResults'
    
    parser = parsers.Parser(acqID, channelID, posID,
                            prefix, sliceID, datasetType)
    assert_equal(parser.acqID,                  1)
    assert_equal(parser.channelID,         'A647')
    assert_equal(parser.posID,               (0,))
    assert_equal(parser.prefix,      'my_dataset')
    assert_equal(parser.sliceID,             None)
    assert_equal(parser.datasetType, 'locResults')
    
def test_Parser_datasetType():
    """Will Parser detect a bad value for datasetType?
    
    """
    acqID       =            1
    channelID   =       'A647'
    posID       =         (0,)
    prefix      = 'my_dataset'
    sliceID     =         None
    datasetType = 'locRseults' # misspelled
    
    try:
        parser = parsers.Parser(acqID, channelID, posID,
                                prefix, sliceID, datasetType)
    except parsers.DatasetError:
        pass
    else:
        raise Exception('DatasetError not caught.')
    
def test_Parser_getBasicInfo():
    """Will getBasicInfo return the right values?
    
    """
    acqID       =             3
    channelID   =        'A750'
    posID       =         (0,1)
    prefix      =        'HeLa'
    sliceID     =          None
    datasetType = 'locMetadata'
    
    parser    = parsers.Parser(acqID, channelID, posID,
                               prefix, sliceID, datasetType)
    basicInfo = parser.getBasicInfo()
    assert_equal(basicInfo['acquisition_id'],           3)
    assert_equal(basicInfo['channel_id'],          'A750')
    assert_equal(basicInfo['position_id'],          (0,1))
    assert_equal(basicInfo['prefix'],              'HeLa')
    assert_equal(basicInfo['slice_id'],              None)
    assert_equal(basicInfo['dataset_type'], 'locMetadata')
    
def test_MMParser_Attributes():
    """Will MMParser properly extract the acquisition information?
    
    """
    inputFilename   = 'Cos7_Microtubules_A647_3_MMStack_Pos0_locResults.dat'
    datasetType     = 'locResults'
    
    mmParser = parsers.MMParser()
    mmParser.parseFilename(inputFilename, datasetType)
    assert_equal(mmParser.acqID,                              3)
    assert_equal(mmParser.channelID,                     'A647')
    assert_equal(mmParser.posID,                           (0,))
    assert_equal(mmParser.prefix,           'Cos7_Microtubules')
    assert_equal(mmParser.sliceID,                         None)
    assert_equal(mmParser.datasetType,             'locResults')
    
def test_MMParser_Channel_Underscores():
    """Will MMParser extract the prefix and channel with weird underscores?
    
    """
    inputFilename   = ['Cos7_Microtubules_Cy5_3_MMStack_Pos0_locResults.dat',
                       '_Cy5_Cos7_Microtubules_3_MMStack_Pos0_locResults.dat',
                       'Cy5_Cos7_Microtubules_3_MMStack_Pos0_locResults.dat',
                       'Cos7_Cy5_Microtubules_3_MMStack_Pos0_locResults.dat',
                       'Cos7_MicrotubulesCy5_3_MMStack_Pos0_locResults.dat',
                       'Cos7_Microtubules__Cy5_3_MMStack_Pos0_locResults.dat',
                       'Cos7___Microtubules__Cy5_3_MMStack_Pos0_locResults.dat']
    datasetType     = 'locResults'
    
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
    """Will MMParser extract the acquisition info w/o a path identifier?
    
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
    inputFile = Path('tests') / Path(f)
    datasetType = 'locMetadata'
    
    mmParser = parsers.MMParser()
    mmParser.parseFilename(inputFile, datasetType)
    assert_equal(mmParser.acqID,                                            1)
    assert_equal(mmParser.channelID,                                   'A647')
    assert_equal(mmParser.posID,                                        (2,2))
    assert_equal(mmParser.prefix,                      'bacteria_HaloInduced')
    assert_equal(mmParser.sliceID,                                       None)
    assert_equal(mmParser.datasetType,                          'locMetadata')
    assert_equal(mmParser.metadata['InitialPositionList']['Label'],
                                                              '1-Pos_002_002')
                                                              
def test_MMParser_Metadata_NoPosition_Metadata():
    """Will MMParser properly read a metadata file with empty position info?
    
    """
    # Note that the json entry for position information is empty in this file!
    f = 'HeLa_Control_A750_1_MMStack_Pos0_locMetadata.json'
    inputFile = Path('tests') / Path(f)
    datasetType = 'locMetadata'
    
    mmParser = parsers.MMParser()
    mmParser.parseFilename(inputFile, datasetType)
    assert_equal(mmParser.acqID,                                            1)
    assert_equal(mmParser.channelID,                                   'A750')
    assert_equal(mmParser.posID,                                         (0,))
    assert_equal(mmParser.prefix,                              'HeLa_Control')
    assert_equal(mmParser.sliceID,                                       None)
    assert_equal(mmParser.datasetType,                          'locMetadata')
    assert_equal(mmParser.metadata['InitialPositionList'],               None)
    
def test_MMParser_Metadata_SinglePosition():
    """Will MMParser properly read a metadata file with a single position?
    
    """
    # Note that the json entry for position information is empty in this file!
    f = 'HeLa_Control_A750_2_MMStack_Pos0_locMetadata.json'
    inputFile = Path('tests') / Path(f)
    datasetType = 'locMetadata'
    
    mmParser = parsers.MMParser()
    mmParser.parseFilename(inputFile, datasetType)
    assert_equal(mmParser.acqID,                                            2)
    assert_equal(mmParser.channelID,                                   'A750')
    assert_equal(mmParser.posID,                                         (0,))
    assert_equal(mmParser.prefix,                              'HeLa_Control')
    assert_equal(mmParser.sliceID,                                       None)
    assert_equal(mmParser.datasetType,                          'locMetadata')
    assert_equal(mmParser.metadata['InitialPositionList']['Label'],    'Pos0')