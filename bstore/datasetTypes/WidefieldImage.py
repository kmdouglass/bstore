# © All rights reserved. ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Switzerland, Laboratory of Experimental Biophysics, 2016
# See the LICENSE.txt file for more details.

import bstore.config
__version__ = bstore.config.__bstore_Version__

# Be sure not to use the from ... import syntax to avoid cyclical imports!
import bstore.database
import h5py
from matplotlib.pyplot import imread
from tifffile import TiffFile

class WidefieldImage(bstore.database.Dataset,
                     bstore.database.DatasetType):
    """Contains the average trajectory of many fiducial markers.
    
    """
    def __init__(self, prefix, acqID, datasetType, data,
                 channelID = None, dateID = None,
                 posID = None, sliceID = None):
        super(WidefieldImage, self).__init__(prefix, acqID, datasetType, data,
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
        return 'WidefieldImage'
    
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
        data : NumPy array
            The image data contained in the database.
        """
        try:
            key += '/image_data'
            file = h5py.File(self._dbName, mode = 'r')
            img  = file[key].value
            return img
        finally:
            file.close()
    
    def put(self, database, key, **kwargs):
        """Puts the data into the database.
        
        Parameters
        ----------
        database           : str
            String containing the path to a B-Store HDF database.
        key                : str
            The HDF key pointing to the dataset location in the HDF database.
        widefieldPixelSize : 2-tuple of float or None
            The x- and y-size of a widefield pixel in microns. This
            informationis used to write attributes to the widefield image for
            opening with other software libraries.
            
        """
        key += '/image_data'
        
        try:
            hdf = h5py.File(database, mode = 'a')
            
            hdf.create_dataset(key,
                               self.data.shape,
                               data = self.data)
                               
            if ('widefieldPixelSize' in kwargs) \
                and (kwargs['widefieldPixelSize']):
                # Write element_size_um attribute for HDF5 Plugin for ImageJ
                # Note that this takes pixel sizes in the format zyx
                elementSize = (1,
                               kwargs['widefieldPixelSize'][1],
                               kwargs['widefieldPixelSize'][0])
                hdf[key].attrs['element_size_um'] = elementSize
                
        finally:
            hdf.close()
    
    @staticmethod        
    def readFromFile(filePath, **kwargs):
        """Read a file on disk containing the DatasetType.
        
        Parameters
        ----------
        filePath : Path
            A pathlib object pointing towards the file to open.
        readTiffTags : bool
            Determines whether the tags of a Tiff file are read.
            
        Returns
        -------
        img : NumPy Array or TiffFile
            
        """
        if ('readTiffTags') in kwargs and kwargs['readTiffTags']:
            with TiffFile(str(filePath)) as img:
                return img
        else:
            # Read image data as a NumPy array
            img = imread(str(filePath))
            return img