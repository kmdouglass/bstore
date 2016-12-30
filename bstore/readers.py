# © All rights reserved. ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Switzerland, Laboratory of Experimental Biophysics, 2017
# See the LICENSE.txt file for more details.

from abc import ABCMeta, abstractmethod, abstractproperty
import bstore.datasetTypes as dsTypes

"""Metaclasses
-------------------------------------------------------------------------------
"""
class Reader(metaclass = ABCMeta):
    """Reads the data for a given datasetType from file.
    
    """
    def __init__(self):
        # Check that datasetType is valid
        if self.datasetType not in dsTypes.__all__:
            raise DatasetTypeError(
                'Error: {:s} is not a recognized dataset type.'.format(
                    self.datasetType))
    
    @abstractmethod
    def __call__(self):
        pass
    
    @abstractproperty
    def datasetType(self):
        pass
    
"""Concrete classes
-------------------------------------------------------------------------------
"""

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