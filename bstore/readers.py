# © All rights reserved. ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Switzerland, Laboratory of Experimental Biophysics, 2017
# See the LICENSE.txt file for more details.

from abc import ABCMeta, abstractmethod

import pandas as pd

"""Metaclasses
-------------------------------------------------------------------------------
"""
class Reader(metaclass = ABCMeta):
    """Reads the data for a given DatasetType from file.
    
    """    
    @abstractmethod
    def __call__(self, filename, **kwargs):
        """Reads the data inside a file into a Python object.
        
        Note that a return type function annotation must be specified in the
        concrete methods to automatically match a Reader with a DatasetType.
        
        Parameters
        ----------
        filename : str or buffer object
            The file containing the data to read.
        **kwargs : dict
            key-value arguments to pass to the auxillary functions used by the
            file reading functions.
        
        """
        pass
    
    @abstractmethod
    def __str__(self):
        """User-friendly and short description of the Reader.
        
        This will appear in GUI menus.
        
        """
        pass
    
"""Concrete classes
-------------------------------------------------------------------------------
"""        
class CSVReader(Reader):
    """Reads data from a generic comma separated values (CSV) file.
    
    This reader utilizes the Pandas read_csv() function, which allows many
    different parameters to be adjusted, such as the value separator. For an
    explanation of the parameters, see the reference below.
    
    References
    ----------
    http://pandas.pydata.org/pandas-docs/stable/generated/pandas.read_csv.html
    
    """        
    def __call__(self, filename, **kwargs) -> pd.DataFrame:
        """Calls the CSV reading machinery.
        
        Parameters
        ----------
        filename : str, Path, or buffer object
            The filename of the file containing the data.
        **kwargs : dict
            key-value arguments to pass to the csv reading machinery.
            
        """
        return pd.read_csv(filename, **kwargs)
    
    def __repr__(self):
        return 'CSVReader()'
    
    def __str__(self):
        return 'Generic CSV File Reader'

"""Exceptions
-------------------------------------------------------------------------------
"""
class DatasetTypeError(Exception):
    """Error raised when a bad or unregistered DatasetType is used.
    
    """
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)