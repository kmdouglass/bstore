__bstore_Version__ = '0.3.0-dev'

"""__HDF_AtomID_Prefix__ : str
    String that precedes all attributes marking database atom
    identifiers in an HDF database.

"""
__HDF_AtomID_Prefix__ = 'SMLM_'

"""___HDF_Metadata_Prefix : str
    String that precedes all attributes marking metadata elements in
    an HDF database.

"""
__HDF_Metadata_Prefix__ = __HDF_AtomID_Prefix__ + 'Metadata_'

"""__Channel_Identifier___ : dict
    Dictionary containing shorthand names for common fluorophores.
       
"""
__Channel_Identifier__ = {'A488' : 'AlexaFluor 488',
                          'A647' : 'AlexaFluor 647',
                          'A750' : 'AlexaFluor 750',
                          'DAPI' : 'DAPI',
                          'Cy5'  : 'Cy5'}

"""FormatDefault : dict
    The default mapping for converting between column header names
    when using the ConvertHeader processor.
       
"""
__Format_Default__                       = {}
__Format_Default__['x [nm]']             = 'x'
__Format_Default__['y [nm]']             = 'y'
__Format_Default__['z [nm]']             = 'z'
__Format_Default__['frame']              = 'frame'
__Format_Default__['uncertainty [nm]']   = 'precision'
__Format_Default__['intensity [photon]'] = 'photons'
__Format_Default__['offset [photon]']    = 'background'
__Format_Default__['loglikelihood']      = 'loglikelihood'
__Format_Default__['sigma [nm]']         = 'sigma'
__Format_Default__['dx [nm]']            = 'dx'
__Format_Default__['dy [nm]']            = 'dy'
__Format_Default__['length [frames]']    = 'length'

"""__Path_To_Test_Data__ : str
    Path relative to the bstore project root directory that
    contains the data for running the automated tests.
       
"""
__Path_To_Test_Data__ = '../bstore_test_files/'

"""__Types_Of_Atoms__ : tuple
    Strings identifying the types of atoms understood by the software.
    
    locMetadata must follow locResults in the list.
       
"""
__Types_Of_Atoms__ = [
                      'locResults',
                      'locMetadata',
                      'widefieldImage',
                      'generic'
                     ]

"""__MM_PixelSize__ : str
    Name of the field in the Micro-Manager metadata containing the pixel size.

"""                     
__MM_PixelSize__ = 'PixelSize_um'

"""__Registered_Generics__ : list of str
    The list of generic datasetTypes currently recognized by B-Store.

"""
__Registered_Generics__ = []