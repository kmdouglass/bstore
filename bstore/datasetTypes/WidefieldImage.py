# © All rights reserved. ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Switzerland, Laboratory of Experimental Biophysics, 2016
# See the LICENSE.txt file for more details.

import bstore.config
__version__ = bstore.config.__bstore_Version__

# Be sure not to use the from ... import syntax to avoid cyclical imports!
import bstore.database
import h5py
import re
import json
from matplotlib.pyplot import imread
from tifffile import TiffFile
from numpy import array

"""Decorators
-------------------------------------------------------------------------------
"""


def putWidefieldImageWithMicroscopyTiffTags(writeImageData):
    """Decorator for writing OME-XML and Micro-Manager metadata + image data.

    This decorator allows the Datastore to work with both NumPy arrays and
    TiffFile objects, the latter of which holds the Tiff metadata as well as
    image data.

    Parameters
    ----------
    writeImageData        : function
        Used to write image data into the datastore.

    Returns
    -------
    writeImageDataAndTags : function
        Function for writing image data and Tiff tags.

    References
    ----------
    1. https://pypi.python.org/pypi/tifffile

    """

    def writeImageDataAndTags(self, datastore, key, **kwargs):
        """Separates image data from Tiff tags and writes them separately.

        Parameters
        ----------
        datastore : str
            String containing the path to a B-Store HDF datastore.
        key : str
            The HDF key pointing to the dataset location in the HDF datastore.

        """
        MM_PixelSize = bstore.config.__MM_PixelSize__

        if isinstance(self.data, TiffFile):
            # Write the TiffFile metadata to the HDF file; otherwise do nothing
            # First, get the Tiff tags; pages[0] assumes there is only one
            # image in the Tiff file.
            tags = dict(self.data.pages[0].tags.items())
            widefieldPixelSize = None
            with h5py.File(datastore, mode='a') as hdf:
                dt = h5py.special_dtype(vlen=str)

                # Start by writing just the OME-XML
                # Note: omexml data is a byte string; the text is UTF-8 encoded
                # See http://docs.h5py.org/en/latest/strings.html for more info
                if 'image_description' in tags:
                    keyName = key + '/OME-XML'
                    omexml = tags['image_description'].value

                    hdf.create_dataset(keyName, (1,), dtype=dt, data=omexml)

                    try:
                        # Write the element_size_um tag if its present in the
                        # OME-XML metadata.
                        ome = omexml.decode('utf-8', 'strict')
                        stringX = re.search('PhysicalSizeX="(\d*\.?\d*)"',
                                            ome).groups()[0]
                        stringY = re.search('PhysicalSizeY="(\d*\.?\d*)"',
                                            ome).groups()[0]
                        pxSizeX = float(stringX)
                        pxSizeY = float(stringY)

                        # Ensure that the units is microns
                        pxUnitsX = re.search('PhysicalSizeXUnit="(\D\D?)"',
                                             ome).groups()[0].encode()
                        pxUnitsY = re.search('PhysicalSizeYUnit="(\D\D?)"',
                                             ome).groups()[0].encode()
                        assert pxUnitsX == b'\xc2\xb5m', 'OME-XML units not um'
                        assert pxUnitsY == b'\xc2\xb5m', 'OME-XML units not um'

                        widefieldPixelSize = (pxSizeX, pxSizeY)

                    except (AttributeError, AssertionError):
                        # When no PhysicalSizeX,Y XML tags are found, or the
                        # the units are not microns, move on to looking inside
                        # the MM metadata.
                        pass

                # Micro-Manager device states metadata is a JSON string
                if 'micromanager_metadata' in tags:
                    keyName = key + '/MM_Metadata'
                    mmmd = json.dumps(tags['micromanager_metadata'].value)

                    hdf.create_dataset(keyName, (1,), dtype=dt, data=mmmd)

                # Micro-Manager summary metadata in JSON string
                if self.data.is_micromanager:
                    keyName = key + '/MM_Summary_Metadata'
                    metaDict = self.data.micromanager_metadata
                    mmsmd = json.dumps(metaDict)

                    hdf.create_dataset(keyName, (1,), dtype=dt, data=mmsmd)

                    # Write the element_size_um tag if its present in the
                    # Micro-Manager metadata (this has priority over OME-XML
                    # due to its position here)
                    if MM_PixelSize in metaDict['summary']:
                        pxSize = metaDict['summary'][MM_PixelSize]
                        widefieldPixelSize = (pxSize, pxSize)

            # Convert atom.data to a NumPy array before writing image data
            self.data = self.data.asarray()

            # Send widefieldPixelSize to the image writer; if a size was not
            # found in the metadata, fall back on whatever is in kwargs.
            if widefieldPixelSize:
                kwargs['widefieldPixelSize'] = widefieldPixelSize

        writeImageData(self, datastore, key, **kwargs)

    return writeImageDataAndTags

"""Concrete classes
-------------------------------------------------------------------------------
"""


class WidefieldImage(bstore.database.Dataset):
    """Contains the average trajectory of many fiducial markers.

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
        return 'WidefieldImage'

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
        data : NumPy array
            The image data contained in the datastore.
        """
        key += '/image_data'
        with h5py.File(datastore, mode='r') as file:
            img = array(file[key])
            return img

    @putWidefieldImageWithMicroscopyTiffTags
    def put(self, datastore, key, **kwargs):
        """Puts the data into the datastore.

        Parameters
        ----------
        datastore           : str
            String containing the path to a B-Store HDF datastore.
        key                : str
            The HDF key pointing to the dataset location in the HDF datastore.
        widefieldPixelSize : 2-tuple of float or None
            The x- and y-size of a widefield pixel in microns. This
            informationis used to write attributes to the widefield image for
            opening with other software libraries.

        """
        key += '/image_data'

        with h5py.File(datastore, mode='a') as hdf:
            hdf.create_dataset(key,
                               self.data.shape,
                               data=self.data)

            if ('widefieldPixelSize' in kwargs) \
                    and (kwargs['widefieldPixelSize']):
                # Write element_size_um attribute for HDF5 Plugin for ImageJ
                # Note that this takes pixel sizes in the format zyx
                elementSize = (1,
                               kwargs['widefieldPixelSize'][1],
                               kwargs['widefieldPixelSize'][0])
                hdf[key].attrs['element_size_um'] = elementSize

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
