"""
    Some base objects for the Flickr API.
    
    Author : Alexis Mignon (c)
    e-mail : alexis.mignon@gmail.com
    Date   : 05/08/2011

"""
import method_call

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

def me(attribute_name = None):
    def decorator(method):
        def call(self,*args,**kwargs):
            name = self.__class__.__self_name__ if attribute_name is None else attribute_name 
            kwargs[name] = self.id
            return method(self,*args,**kwargs)
        return call
    return decorator

def caller(method_name):
    def decorator(method) :
        def call(self,*args,**kwargs):
            not_signed = kwargs.pop("not_signed",False)
            if not_signed :
                token = None
            else :
                token = kwargs.pop("token",None)
                if token is None : token = self.getToken()

            kwargs["auth_handler"] = token
            method_args,format_result = method(self,*args,**kwargs)
            r = method_call.call_api(method = method_name,**method_args)
            return format_result(r)
        return call
    return decorator

class FlickrObject(object):
    """
        Base Object for Flickr API Objects
    """
    __converters__ = []
    __display__ = []
    


    def __init__(self,**params):
        params["loaded"] = False
        self._set_properties(**params)

    def _set_properties(self,**params):
        for c in self.__class__.__converters__ :
            c(params)
        self.__dict__.update(params)
    
    def setToken(self,token):
        self.__dict__["token"] = token
    
    def getToken(self):
        return self.__dict__.get("token",None)
    
    def __getattr__(self,name):
        if name not in self.__dict__ :
            if not self.loaded :
                self.load()
        try :
            return self.__dict__[name]
        except KeyError :
            raise AttributeError("'%s' object has no attribute '%s'"%(self.__class__.__name__,name))
    
    def __setattr__(self,name,values):
        raise FlickrError("Readonly attribute")
    
    def get(self,key,*args,**kwargs):
        return self.__dict__.get(key,*args,**kwargs)
    
    def __getitem__(self,key):
        return self.__dict__[key]
    
    def __setitem__(self,key,value):
        raise FlickrError("Read-only attribute")

    def __str__(self):
        vals = []
        for k in self.__class__.__display__ :
            val_found = False
            try :
                value = self.__dict__[k]
                val_found = True
            except KeyError :
                self.load()
                try :
                    value = self.__dict__[k]
                    val_found = True
                except KeyError : pass
            if not val_found : continue
            if isinstance(value,unicode):
                value = value.encode("utf8")
            if isinstance(value,str):
                value = "'%s'"%value
            else : value = str(value)
            if len(value) > 20: value = value[:20]+"..."
            vals.append("%s = %s"%(k,value))
        return "%s(%s)"%(self.__class__.__name__,", ".join(vals))
    
    def __repr__(self): return str(self)

    def getInfo(self):
        """
            Returns object information as a dictionnary.
            Should be overriden.
        """
        return {}

    def load(self):
        props = self.getInfo()
        self.__dict__["loaded"] = True
        self._set_properties(**props)

def dict_converter(keys,func):
    def convert(dict_) :
        for k in keys :
            try :
                dict_[k] = func(dict_[k])
            except KeyError : pass
    return convert
