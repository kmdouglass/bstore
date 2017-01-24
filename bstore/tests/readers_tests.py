# © All rights reserved. ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Switzerland, Laboratory of Experimental Biophysics, 2016-2017
# See the LICENSE.txt file for more details.

"""Unit tests for the readers module.

Notes
-----
nosetests should be run in the directory just above the `tests` folder.
 
"""

__author__ = 'Kyle M. Douglass'
__email__  = 'kyle.m.douglass@gmail.com' 

from nose.tools import assert_equal, raises

# Register the test generic
from bstore  import config
config.__Registered_DatasetTypes__.append('Localizations')

from bstore import readers, parsers
import bstore.datasetTypes.Localizations as Localizations
from pathlib import Path

testDataRoot = Path(config.__Path_To_Test_Data__)

def test_CSVReader_Comma_Delimited_Data():
    """CSVReader reads comma delimited files.
    
    """
    filePath = testDataRoot / Path('readers_test_files/csv/comma_delimited/')
    filename = filePath / Path('HeLaL_Control_1.csv')
    reader = readers.CSVReader()
    
    # Read the data from file
    data = reader(filename)
    
    # Verify data was read correctly
    assert_equal(len(data.columns), 9)
    assert_equal(len(data), 11)
    
def test_CSVReader_Tab_Delimited_Data():
    """CSVReader reads tab-delimited files.
    
    """
    filePath = testDataRoot / Path('readers_test_files/csv/tab_delimited/')
    filename = filePath / Path('HeLaL_Control_1.csv')
    reader = readers.CSVReader()
    
    # Read the data from file
    # sep is a keyword argument to Pandas read_csv()
    data = reader(filename, sep = '\t')
    
    # Verify data was read correctly
    assert_equal(len(data.columns), 9)
    assert_equal(len(data), 11)
    
def test_CSVReader_Kwargs():
    """CSVReader passes keyword arguments to Pandas read_csv() function.
    
    """
    filePath = testDataRoot / Path('readers_test_files/csv/comma_delimited/')
    filename = filePath / Path('HeLaL_Control_1.csv')
    reader = readers.CSVReader()
    
    # Read the data from file
    # 'usecols' and 'nrows' are keywords of the Pandas read_csv() function
    data = reader(filename, usecols = ['x', 'y'], nrows = 5)
    
    # Verify data was read correctly
    assert_equal(len(data.columns), 2)
    assert_equal(len(data), 5)
    
def test_CSVReader_Works_With_Parser():
    """CSVReader is correctly passed to readFromFile() from SimpleParser.
    
    """
    filePath = testDataRoot / Path('readers_test_files/csv/tab_delimited/')
    filename = filePath / Path('HeLaL_Control_1.csv')
    
    # Initialize the Parser and Reader                        
    parser = parsers.SimpleParser()
    reader = readers.CSVReader()
    
    # reader keyword argument passes the CSVReader instance;
    # all other keyword arguments are passed to CSVReader's __call__ function.
    parser.parseFilename(
        filename, datasetType = 'Localizations', reader = reader, sep = '\t')
    
    # Test a couple of the localization results
    assert_equal(parser.dataset.data['x'].iloc[0], 6770)
    assert_equal(parser.dataset.data['intensity'].iloc[0],4386.6)
    assert_equal(parser.dataset.data['x'].iloc[1], 7958.1)
    assert_equal(len(parser.dataset.data.columns), 9)
    assert_equal(len(parser.dataset.data), 11)

def test_JSONReader_Columns_Format():
    """JSONReader reads JSON files formatted by columns.
    
    http://pandas.pydata.org/pandas-docs/stable/generated/pandas.read_json.html
    
    """
    filePath = testDataRoot / Path('readers_test_files/json/columns')
    filename = filePath / Path('HeLaL_Control_1.json')
    reader = readers.JSONReader()
    
    # Read the data from file
    data = reader(filename)
    
    # Verify data was read correctly
    assert_equal(len(data.columns), 9)
    assert_equal(len(data), 11)
    
def test_JSONReader_Index_Format():
    """JSONReader reads JSON files formatted by index.
    
    http://pandas.pydata.org/pandas-docs/stable/generated/pandas.read_json.html
    
    """
    filePath = testDataRoot / Path('readers_test_files/json/index/')
    filename = filePath / Path('HeLaL_Control_1.json')
    reader = readers.JSONReader()
    
    # Read the data from file
    # orient is a keyword argument to Pandas read_json()
    data = reader(filename, orient='index')
    
    # Verify data was read correctly
    assert_equal(len(data.columns), 9)
    assert_equal(len(data), 11)
    
def test_JSONReader_Kwargs():
    """JSONReader passes keyword arguments to Pandas read_json() function.
    
    """
    filePath = testDataRoot / Path('readers_test_files/json/columns/')
    filename = filePath / Path('HeLaL_Control_1.json')
    reader = readers.JSONReader()
    
    # Read the data from file
    # precise_float is a keyword of the Pandas read_json() function
    data = reader(filename, orient='columns', precise_float=True)
    
    # Verify data was read correctly
    assert_equal(len(data.columns), 9)
    assert_equal(len(data), 11)
    
def test_JSONReader_Works_With_Parser():
    """JSONReader is correctly passed to readFromFile() from SimpleParser.
    
    """
    filePath = testDataRoot / Path('readers_test_files/json/index/')
    filename = filePath / Path('HeLaL_Control_1.json')
    
    # Initialize the Parser and Reader                        
    parser = parsers.SimpleParser()
    reader = readers.JSONReader()
    
    # reader keyword argument passes the CSVReader instance;
    # all other keyword arguments are passed to JSONReader's __call__ function.
    parser.parseFilename(
        filename, datasetType='Localizations', reader=reader, orient='index')
    
    
    
    # Test a couple of the localization results
    assert_equal(parser.dataset.data['x'].iloc[0], 6770)
    assert_equal(parser.dataset.data['intensity'].iloc[0],4386.6)
    assert_equal(parser.dataset.data['x'].iloc[1], 7958.1)
    assert_equal(len(parser.dataset.data.columns), 9)
    assert_equal(len(parser.dataset.data), 11)