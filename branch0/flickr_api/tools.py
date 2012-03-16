from base import FlickrError,dict_converter
from method_call import clean_content,call_api
import method_call

def load_methods():
    """
        Loads the list of all methods
    """
    r = call_api(method = "flickr.reflection.getMethods")
    return r["methods"]["method"]

__perms__ = { 0 : 'none', '1' : 'read', '2' : 'write' , '3' : 'delete' }

def methods_info():
    methods = {}
    for m in load_methods():
        info = call_api(method = "flickr.reflection.getMethodInfo",method_name = m)
        info.pop("stat")
        conv = dict_converter(["needslogin","needssigning"],bool)
        method = info.pop("method")
        conv(method)
        method["requiredperms"] = __perms__[method["requiredperms"]]
        info.update(method)
        info["arguments"] = info["arguments"]["argument"]
        info["errors"] = info["errors"]["error"]
        methods[m] = info
    return methods

def write_reflection(path,template,methods = None):
    if methods is None :
        methods = methods_info()
    with open(template,"r") as t :
        templ = t.read()
    with open(path,"w") as f:
        f.write(templ%str(methods))

