class FormatMap(dict):
    """Two-way map for mapping one localization file format to another.
    
    _formatMap subclasses dict and acts like a two-way mapping between
    key-value pairs, unlike dict which provides only a one-way relationship.
    
    To use this class, simply pass a dict to the FormatMap's constructor.
    Alternatively, create a FormatMap, which creates an empty dict. Then add
    fields as you wish.
    
    References
    ----------
    [1] http://stackoverflow.com/questions/1456373/two-way-reverse-map
    
    """
    def __setitem__(self, key, value):
        if key   in self: del self[key]
        if value in self: del self[value]
        dict.__setitem__(self, key, value)
        dict.__setitem__(self, value, key)
        
    def __delitem__(self, key):
        dict.__delitem__(self, self[key])
        dict.__delitem__(self, key)
        
    def __len__(self):
        return dict.__len__(self) // 2
        
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