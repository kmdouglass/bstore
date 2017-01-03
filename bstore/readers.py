# © All rights reserved. ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Switzerland, Laboratory of Experimental Biophysics, 2017
# See the LICENSE.txt file for more details.

from abc import ABCMeta, abstractmethod
import bstore.datasetTypes as dsTypes

import pandas as pd

"""Metaclasses
-------------------------------------------------------------------------------
"""
class Reader(metaclass = ABCMeta):
    """Reads the data for a given datasetType from file.
    
    The constructor checks that a Reader instance matches a datasetType that is
    already defined in B-Store.
    
    Parameters
    ----------
    instanceTypes : set of str
        The datasetTypes that the reader may be used with.
        
    Attributes
    ----------
    DATASETTYPE : set of str
        The datasetTypes that the reader may be used with.
    
    """
    DATASETTYPE = set()    
    
    def __init__(self, instanceTypes):
        # Check that datasetType is defined in B-Store
        if not (instanceTypes & set(dsTypes.__all__)):
            raise DatasetTypeError(
                'Error: {:s} is not a recognized dataset type.'.format(
                    self.datasetType))
    
    @abstractmethod
    def __call__(self, filename, **kwargs):
        """Reads the data inside a file into a Python object.
        
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
    
    Attributes
    ----------
    DATASETTYPE : set of str
        The datasetTypes that the reader may be used with.
    
    References
    ----------
    http://pandas.pydata.org/pandas-docs/stable/generated/pandas.read_csv.html
    
    """
    DATASETTYPE = {'Localizations', 
                   'WidefieldImage',
                   'AverageFiducial',
                   'FiducialTracks'}    
    
    def __init__(self):
        super(Reader, self).__init__(self.DATASETTYPE)
        
    def __call__(self, filename, **kwargs):
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
        return 'Generic CSV Reader'

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