# © All rights reserved. ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Switzerland, Laboratory of Experimental Biophysics, 2016
# See the LICENSE.txt file for more details.

import bstore.config
__version__ = bstore.config.__bstore_Version__

# Be sure not to use the from ... import syntax to avoid cyclical imports!
import bstore.database
import pandas as pd
import sys

class Localizations(bstore.database.Dataset,
                    bstore.database.DatasetType):
    """Contains the average trajectory of many fiducial markers.
    
    """
    def __init__(self, prefix, acqID, datasetType, data,
                 channelID = None, dateID = None,
                 posID = None, sliceID = None):
        super(Localizations, self).__init__(prefix, acqID, datasetType, data,
                                            channelID = channelID,
                                            dateID    = dateID,
                                            posID     = posID,
                                            sliceID   = sliceID)
    
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
    def datasetTypeName(self):
        """This should be set to the same name as the class.
        
        """
        return 'Localizations'
    
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
        data : Pandas DataFrame
            The data retrieved from the HDF file.
        """
        data = pd.read_hdf(database, key = key)
            
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
        # Writes the data in the dataset to the HDF file.
        try:
            hdf = pd.HDFStore(database)
            hdf.put(key, self.data, format = 'table',
                    data_columns = True, index = False)
        except:
            print("Unexpected error in put():", sys.exc_info()[0])
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
        return pd.read_csv(str(filePath))