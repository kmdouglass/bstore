from bstore.parsers import FormatMap

# Built-in default column name conversions
FormatDefault                       = FormatMap()
FormatDefault['x [nm]']             = 'x'
FormatDefault['y [nm]']             = 'y'
FormatDefault['z [nm]']             = 'z'
FormatDefault['frame']              = 'frame'
FormatDefault['uncertainty [nm]']   = 'precision'
FormatDefault['intensity [photon]'] = 'photons'
FormatDefault['offset [photon]']    = 'background'      # formerly bg
FormatDefault['loglikelihood']      = 'loglikelihood'
FormatDefault['sigma [nm]']         = 'sigma'
FormatDefault['dx [nm]']            = 'dx'
FormatDefault['dy [nm]']            = 'dy'
FormatDefault['length [frames]']    = 'length'
FormatDefault['cluster_id']         = 'cluster_id'
FormatDefault['particle']           = 'particle'