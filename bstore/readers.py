# © All rights reserved. ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Switzerland, Laboratory of Experimental Biophysics, 2017
# See the LICENSE.txt file for more details.

from abc import ABCMeta, abstractmethod, abstractproperty

import pandas as pd
import inspect

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
    def __repr__(self):
        pass
    
    @abstractproperty
    def __signature__(self):
        """The custom Signature object for the class's __call__ method.
        
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
    
    The constructor for CSVReader creates the class's custom call signature
    
    References
    ----------
    http://pandas.pydata.org/pandas-docs/stable/generated/pandas.read_csv.html
    
    """ 
    def __init__(self):
        # Create the custom call signature for this Reader
        # https://docs.python.org/3.5/library/inspect.html#inspect.Signature
        f   = pd.read_csv
        sig = inspect.signature(f)
        p1  = inspect.Parameter(
            'filename', inspect.Parameter.POSITIONAL_ONLY)
            
        newParams = [p1] + [param for name, param in sig.parameters.items()
                                  if name != 'filepath_or_buffer']
                                    
        self._sig = sig.replace(parameters = newParams)
       
    def __call__(self, filename, **kwargs) -> pd.DataFrame:
        """Calls the CSV reading machinery.
        
        Parameters
        ----------
        filename : str, Path, or buffer object
            The filename of the file containing the data.
        **kwargs : dict
            key-value arguments to pass to the csv reading machinery.
            
        Returns
        -------
        Pandas DataFrame
            
        """
        # Inspect read_csv and pull out only its keyword arguments from
        # **kwargs. This will prevent errors in passing unrecognized kwargs.
        kwargs = {k: v for k, v in kwargs.items()
                       if k in self.__signature__.parameters
                       and k != 'filename'}        
        
        return pd.read_csv(filename, **kwargs)
    
    def __repr__(self):
        return 'CSVReader()'
    
    @property        
    def __signature__(self):
        return self._sig
    
    def __str__(self):
        return 'Generic CSV File Reader'
        
class JSONReader(Reader):
    """Reads data from a generic JSON (CSV) file.
    
    This reader utilizes the Pandas read_json() function, which allows many
    different parameters to be adjusted while reading JSON files.
    
    The constructor for JSONReader creates the class's custom call signature.
    
    References
    ----------
    http://pandas.pydata.org/pandas-docs/stable/generated/pandas.read_json.html
    
    """
    def __init__(self):
        # Create the custom call signature for this Reader
        # https://docs.python.org/3.5/library/inspect.html#inspect.Signature
        f   = pd.read_json
        sig = inspect.signature(f)
        p1  = inspect.Parameter(
            'filename', inspect.Parameter.POSITIONAL_ONLY)
            
        newParams = [p1] + [param for name, param in sig.parameters.items()
                                  if name != 'filepath_or_buffer']
                                    
        self._sig = sig.replace(parameters = newParams)
    
    def __call__(self, filename, **kwargs):
        """Calls the JSON reading machinery.
        
        Parameters
        ----------
        filename : str, Path, or buffer object
            The filename of the file containing the data.
        **kwargs : dict
            key-value arguments to pass to the csv reading machinery.
            
        Returns
        -------
        Pandas DataFrame
            
        """
        # Inspect read_csv and pull out only its keyword arguments from
        # **kwargs. This will prevent errors in passing unrecognized kwargs.
        kwargs = {k: v for k, v in kwargs.items()
                       if k in self.__signature__.parameters
                       and k != 'filename'}        
        
        return pd.read_json(filename, **kwargs)
    
    def __repr__(self):
        return('JSONReader()')
    
    @property
    def __signature__(self):
        return self._sig
    
    def __str__(self):
        return 'Generic JSON File Reader'

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