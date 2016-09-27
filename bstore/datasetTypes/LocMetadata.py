# © All rights reserved. ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Switzerland, Laboratory of Experimental Biophysics, 2016
# See the LICENSE.txt file for more details.

import bstore.config as config
__version__ = config.__bstore_Version__

# Be sure not to use the from ... import syntax to avoid cyclical imports!
import bstore.database
import h5py
import json

class LocMetadata(bstore.database.Dataset):
    """Contains metadata associated with a localization results dataset.
    
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
                                          
    @property
    def attributeOf(self):
        """The other DatasetType that this DatasetType describes.
        
        If the DatasetType is an attribute of another type, return the name of
        this other DatasetType. An attribute means that it simply contains
        metadata and attributes that more fully describe another datasetType.
        If this DatasetType is not an attribute, return None.

        Returns
        -------
        str
        
        """
        return 'Localizations'
    
    @property
    def datasetType(self):
        """This should be set to the same name as the class.
        
        """
        return 'LocMetadata'
    
    def get(self, database, key, **kwargs):
        """Returns a dataset from the database.
        
        Parameters
        ----------
        database : str
            String containing the path to a B-Store HDF database.
        key      : str
            The HDF key pointing to the dataset location in the HDF database.
        
        Returns
        -------
        data : dict
            Metadata as key value pairs. All values are strings compatible
            with Python's JSON's dump.
        """
        with h5py.File(database, mode = 'r') as hdf:
            # Open the HDF file and get the dataset's attributes
            attrKeys = hdf[key].attrs.keys()
            attrID   = config.__HDF_Metadata_Prefix__
            data     = {}            
            
            # Currently h5py raises IOError when attributes are empty.
            # See https://github.com/h5py/h5py/issues/279
            # For this reason, I can't use a simple list comprehension
            # with a filter over attrs.items() to get the metadata.
            for currAttr in attrKeys:
                try:
                    # Filter out attributes irrelevant to the database.
                    # Also remove the database's attribute flag.
                    if currAttr[:len(attrID)] == attrID:
                        data[currAttr[len(attrID):]] = \
                                        json.loads(hdf[key].attrs[currAttr])
                except IOError:
                    # Ignore attirbutes that are empty.
                    # See above comment.
                    pass
                
        return data
    
    def put(self, database, key, **kwargs):
        """Puts the data into the database.
        
        Parameters
        ----------
        database : str
            String containing the path to a B-Store HDF database.
        key      : str
            The HDF key pointing to the dataset location in the HDF database.
            
        """
        attrFlag = config.__HDF_AtomID_Prefix__
        mdFlag   = config.__HDF_Metadata_Prefix__
        print(key)
        try:
            hdf = h5py.File(database, mode = 'a')
                
            # Loop through metadata and write each attribute to the key
            for currKey in self.data.keys():
                attrKey = '{0:s}{1:s}'.format(mdFlag, currKey)
                attrVal = json.dumps(self.data[currKey])
                hdf[key].attrs[attrKey] = attrVal
                
            # Used for identification during database queries
            attrKey = ('{0:s}{1:s}datasetType').format(mdFlag, attrFlag)
            attrVal = json.dumps('locMetadata')
            hdf[key].attrs[attrKey] = attrVal
            
        except KeyError:
            # Raised when the hdf5 key does not exist in the database.
            ids = json.dumps(self.getInfoDict())
            raise LocResultsDoNotExist(('Error: Cannot not append metadata. '
                                        'No localization results exist with '
                                        'these atomic IDs: ' + ids))
        finally:
            hdf.close()
    
    @staticmethod        
    def readFromFile(filePath, **kwargs):
        """Read a file on disk containing the DatasetType.
        
        Parameters
        ----------
        filePath : Path
            A pathlib object pointing towards the file to open.
            
        Returns
        -------
        Pandas DataFrame
            
        """
        with open(str(filePath), 'r') as file:
            return json.load(file)

"""Exceptions
-------------------------------------------------------------------------------
"""        
class LocResultsDoNotExist(Exception):
    """Attempting to attach locMetadata to non-existing locResults.
    
    """
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)