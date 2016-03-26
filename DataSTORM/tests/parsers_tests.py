from nose.tools import *
from DataSTORM import parsers

def test_Parser_Attributes():
    """Will Paraser accept and assign parameters to class attributes correctly?
    
    """
    acqID       =            1
    channelID   =       'A647'
    posID       =         (0,) # Note that this is a tuple!
    prefix      = 'my_dataset'
    datasetType = 'locResults'
    
    parser = parsers.Parser(acqID, channelID, posID, prefix, datasetType)
    assert_equal(parser.acqID,                  1)
    assert_equal(parser.channelID,         'A647')
    assert_equal(parser.posID,               (0,))
    assert_equal(parser.prefix,      'my_dataset')
    assert_equal(parser.datasetType, 'locResults')
    
def test_Parser_datasetType():
    """Will Parser detect a bad value for datasetType?
    
    """
    acqID       =            1
    channelID   =       'A647'
    posID       =         (0,)
    prefix      = 'my_dataset'
    datasetType = 'locRseults' # misspelled
    
    try:
        parser = parsers.Parser(acqID, channelID, posID, prefix, datasetType)
    except parsers.DatasetError:
        pass
    
def test_Parser_getBasicInfo():
    """Will getBasicInfo return the right values?
    
    """
    acqID       =             3
    channelID   =        'A750'
    posID       =         (0,1)
    prefix      =        'HeLa'
    datasetType = 'locMetadata' # misspelled
    
    parser    = parsers.Parser(acqID, channelID, posID, prefix, datasetType)
    basicInfo = parser.getBasicInfo()
    assert_equal(basicInfo['acquisition_id'],           3)
    assert_equal(basicInfo['channel_id'],          'A750')
    assert_equal(basicInfo['position_id'],          (0,1))
    assert_equal(basicInfo['prefix'],              'HeLa')
    assert_equal(basicInfo['dataset_type'], 'locMetadata')