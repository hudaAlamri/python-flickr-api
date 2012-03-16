import re
import inspect
from functools import wraps
import method_call
import auth

try :
    from methods import __methods__
    def make_docstring(method,ignore_arguments = [],show_errors = True):
        info = __methods__[method]
        context = {'method':method}
        
        doc = """
        flickr method: %(method)s

        Authentication:
            %(authentication)s
        
        Arguments:
    %(arguments)s
    """
        needs_login = info["needslogin"]
        required = info["requiredperms"]
        if needs_login :
            if required == 'none' :
                authentication = "This method requires authentication"
            elif required == 'read' :
                authentication = "This method requires authentication with 'read' permission"
            elif required == 'write' :
                authentication = "This method requires authentication with 'write' permission"
            elif required == 'delete' :
                authentication = "This method requires authentication with 'delete' permission"
            else : raise ValueError("Unexpected permision value: %s"%required)
        else :
            authentication = "This method does not require authentication"
        context["authentication"] = authentication
        arguments = []
        argument = """        %(argument_name)s (%(argument_required)s):
    %(argument_descr)s"""
        for a in info["arguments"] :
            aname = a["name"]
            if aname in ignore_arguments :
                continue
            argument_context = {
                'argument_name' : aname,
                'argument_required' : 'optional' if a["optional"] else 'required',
                'argument_descr' : format_block(a["text"],80," "*12)
            }
            arguments.append(argument%argument_context)
        context["arguments"] = "\n".join(arguments)

        if show_errors :
            doc += """
        Errors:
    %(errors)s
    """
            errors = []
            error = """        code %(code)s :
    %(message)s"""
            for e in info["errors"] :
                error_context = {
                    'code' : e["code"],
                    'message': format_block(e["message"],80," "*12)
                }
                errors.append(error%error_context)
            context["errors"] = "\n".join(errors)
        return doc%context

except ImportError :
    __methods__ = {}
    def make_docstring(method,ignore_arguments = [],show_errors = True):
        return None

LIST_REG = re.compile(r'<ul>(.*?)</ul>',re.DOTALL|re.UNICODE|re.MULTILINE)
LIST_ITEM_REG = re.compile(r'<li>(.*?)</li>',re.DOTALL|re.UNICODE)

class FlickrAutoDoc(type):
    """
        Meta class that adds documentation to methods that bind
        to a flickr method, which are called 'caller methods'.
        
        It basically adds two attributes to each caller methods:
        * __doc__ : the docstring is set from the documentation
            returned by flickr.reflection.getMethodInfo. If the method
            is not static, the entry related to the object itself is
            removed from the docstring, using the __self_name__ class
            attribute.
            For instance, Person.__self_name__ = "user_id". This means
            the for a bound (not static) method, the entry corresponding
            to "user_id" in the docstring is removed.
        * __self_name__ : for non static method, a '__self_name__' attribute
            is added to the method. This is used by the 'caller' 
            decorator to know how to refer to the calling object.

    """
    def __new__(meta,classname,bases,classDict):
        self_name = classDict.get("__self_name__",None)
        isstatic = False
        for k,v in classDict.iteritems() :
            if isinstance(v,staticmethod):
                v = v.__get__(0) # __get__ ignores its arguments and returns the function it wraps
                isstatic = True
            if hasattr(v,'flickr_method'):
                ignore_arguments = ["api_key",self_name]
                if not isstatic and self_name :
                    ignore_arguments.append(self_name)
                    v.__self_name__ = self_name # this is used by the decorator caller
                                                # to know the arument name to use to refer
                                                # to the current object.
                v.__doc__ = make_docstring(v.flickr_method,ignore_arguments,show_errors = False)
        return type.__new__(meta,classname,bases,classDict)

def format_block(text,width,prefix = ""):
    text = text.replace(r"<br />",r"<br/>")
    text = text.replace(r"<br/><br/>",r" <br/> ")
    text = text.replace('<strong>',"").replace("</strong>","")
    text = text.replace("<code>","'").replace("</code>","'")
    text.replace("&mdash;","--")
    text = text.split()
    lines = []
    line = prefix
    start = True

    for word in text :
        if word == "<br/>" :
            lines.append(line)
            line = prefix
            start = True
            continue

        line_length = len(line) + len(word)
        if start : line_length += 1
        if line_length > width :
            if start : #if the word is too big we still concatenate it.
                line+=word
                start = False
            else :
                lines.append(line)
                line = prefix+word
                start = False
        else :
            if not start : line+=' '
            line += word
            start = False
    if not start :
        lines.append(line)
    res = "\n".join(lines)+"\n"
    
    list_blocks = LIST_REG.findall(res)
    for block in list_blocks :
        block.replace("\n"," ")
        items = "\n" + "".join([format_block("* %s"%i.strip(),width,prefix) for i in LIST_ITEM_REG.findall(block)])+prefix
        res = LIST_REG.sub(items,res)
    return res


def caller(flickr_method):
    """
        This decorator binds a method to the flickr method given 
        by 'flickr_method'.
        The wrapped method should return the argument dictionnary
        and a function that format the result of method_call.call_api.
    """
    def decorator(method) :
        @wraps(method)
        def call(*args,**kwargs):
            if hasattr(call,'__self_name__'):
                self = args[0]
                kwargs[call.__self_name__] = self.id
            not_signed = kwargs.pop("not_signed",False)
            if not_signed :
                token = None
            else :
                token = kwargs.pop("token",None)
                if token is None :
                    try :
                        self = args[0]
                        token = self.getToken()
                        if not token : token = auth.AUTH_HANDLER
                    except (AttributeError,IndexError): pass
            method_args,format_result = method(*args,**kwargs)
            if token : method_args["auth_handler"] = token
            r = method_call.call_api(method = flickr_method,**method_args)
            return format_result(r)
        call.flickr_method = flickr_method
        return call
    return decorator
