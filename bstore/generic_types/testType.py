# © All rights reserved. ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Switzerland, Laboratory of Experimental Biophysics, 2016
# See the LICENSE.txt file for more details.

from bstore import database as db

class testType(db.Dataset, db.GenericDatasetType):
    def __init__(self, prefix, acqID, datasetType, data,
                 channelID = None, dateID = None,
                 posID = None, sliceID = None):
        super(testType, self).__init__(prefix, acqID, datasetType, data,
                                       channelID = channelID,
                                       dateID    = dateID,
                                       posID     = posID,
                                       sliceID   = sliceID)
    
    @property
    def genericTypeName(self):
        return 'testType'
    
    def get(self):
        pass
    
    def put(self):
        pass