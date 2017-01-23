# © All rights reserved. ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Switzerland, Laboratory of Experimental Biophysics, 2016
# See the LICENSE.txt file for more details.

import bstore.config
__version__ = bstore.config.__bstore_Version__

# Be sure not to use the from ... import syntax to avoid cyclical imports!
import bstore.database
import pandas as pd
import sys
import traceback

class FiducialTracks(bstore.database.Dataset):
    """Contains the individual trajectories of many fiducial markers.
    
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self):
        return self.datasetType + ': ' + self.datasetIDs.__repr__()

    @property
    def attributeOf(self):
        """The other DatasetType that this DatasetType describes.
        
        If the DatasetType is an attribute of another type, return the name of
        this other DatasetType. An attribute means that it simply contains
        metadata and attributes that more fully describe another datasetType.
        If this DatasetType is not an attribute, return None.

        Returns
        -------
        None
        
        """
        return None  
    
    @property
    def datasetType(self):
        """This should be set to the same name as the class.
        
        """
        return 'FiducialTracks'
    
    def get(self, datastore, key, **kwargs):
        """Returns a dataset from the datastore.
        
        Parameters
        ----------
        datastore : str
            String containing the path to a B-Store HDF datastore.
        key      : str
            The HDF key pointing to the dataset location in the HDF datastore.
        
        Returns
        -------
        data : Pandas DataFrame
            The data retrieved from the HDF file.
        """
        data = pd.read_hdf(datastore, key = key)
            
        return data
    
    def put(self, datastore, key, **kwargs):
        """Puts the data into the datastore.
        
        Parameters
        ----------
        datastore : str
            String containing the path to a B-Store HDF datastore.
        key      : str
            The HDF key pointing to the dataset location in the HDF datastore.
            
        """
        # Writes the data in the dataset to the HDF file.
        try:
            hdf = pd.HDFStore(datastore)
            hdf.put(key, self.data, format = 'table',
                    data_columns = True, index = False)
        except:
            print("Unexpected error in put():", sys.exc_info()[0])
            
            if bstore.config.__Verbose__:
                print(traceback.format_exc())
        finally:
            hdf.close()
    
    @staticmethod        
    def readFromFile(filePath, **kwargs):
        """Read a file on disk containing the generic type.
        
        Parameters
        ----------
        filePath : Path
            A pathlib object pointing towards the file to open.
            
        """
        return pd.read_csv(str(filePath))