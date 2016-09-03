# © All rights reserved. ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Switzerland, Laboratory of Experimental Biophysics, 2016
# See the LICENSE.txt file for more details.

# Be sure not to use the from ... import syntax to avoid cyclical imports!
import bstore.database
import pandas as pd
import sys

class averageFiducial(bstore.database.Dataset,
                      bstore.database.GenericDatasetType):
    """Contains the average trajectory of many fiducial markers.
    
    """
    def __init__(self, prefix, acqID, datasetType, data,
                 channelID = None, dateID = None,
                 posID = None, sliceID = None):
        super(averageFiducial, self).__init__(prefix, acqID, datasetType, data,
                                              channelID = channelID,
                                              dateID    = dateID,
                                              posID     = posID,
                                              sliceID   = sliceID)
    
    @property
    def genericTypeName(self):
        """This should be set to the same name as the class.
        
        """
        return 'averageFiducial'
    
    def get(self, database, key):
        """Returns a testType dataset from the database.
        
        Parameters
        ----------
        database : str
            String containing the path to a B-Store HDF database.
        key      : str
            The HDF key pointing to the dataset location in the HDF database.
        
        Returns
        -------
        data : NumPy array
            The data retrieved from the HDF file.
        """
        data = pd.read_hdf(database, key = key)
            
        return data
    
    def put(self, database, key):
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
    def readFromFile(filePath):
        """Prototyping...
        
        Parameters
        ----------
        filePath : Path
            A pathlib object pointing towards the file to open.
            
        """
        return pd.read_csv(str(filePath))