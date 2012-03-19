from method_call import clean_content,call_api
import method_call
import sys,os

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
        method = info.pop("method")
        conv(method)
        method["requiredperms"] = __perms__[method["requiredperms"]]
        method["needslogin"] = bool(method.pop("needslogin"))
        method["needssigning"] = bool(method.pop("needssigning"))
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

def write_doc(output_path,exclude = ["flickr_keys","methods"]):
    import flickr_api
    exclude.append("__init__")
    modules = ['flickr_api']
    dir = os.path.dirname(flickr_api.__file__)
    modules += [ "flickr_api."+f[:-3] for f in os.listdir(dir) if f.endswith(".py") and f[:-3] not in exclude]
    sys.path.insert(0,dir+"../")
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    os.chdir(output_path)
    for m in modules :
        os.system("pydoc -w "+m)

    
    
    
