"""
    Some base objects for the Flickr API.
    
    Author : Alexis Mignon (c)
    e-mail : alexis.mignon@gmail.com
    Date   : 05/08/2011

"""

class FlickrError(Exception):
    pass

class FlickrAPIError(FlickrError):
    def __init__(self,code,message):
        FlickrError.__init__(self,"%i : %s"%(code,message))
        self.code = code
        self.message = message

class FlickrDictObject(object):
    """
        Tranform recursively JSON dictionnaries into objects
    """
    def __init__(self,name,obj_dict):
        self.__name__ = name
        for k,v in obj_dict.iteritems() :
            if isinstance(v,dict) :
                v = FlickrDictObject(k,v)
            if isinstance(v,list) :
                v = [ FlickrDictObject(k,vi) for vi in v ]
            self.__dict__[k] = v

def dict_converter(keys,func):
    def convert(dict_) :
        for k in keys :
            try :
                dict_[k] = func(dict_[k])
            except KeyError : pass
    return convert
