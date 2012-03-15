# -*- encoding: utf8 -*-
"""
    Object Oriented implementation of Flickr API.
    
    Important notes:
    - For consistency, the naming of methods might differ from the name
      in the official API. Please check the method "docstring" to know
      what is the implemented method.
      
    - For methods which expect an object "id", either the 'id' string
      or the object itself can be used as argument. Similar consideration
      holds for lists of id's. 
      
      For instance if "photo_id" is expected you can give call the function
      with named argument "photo = PhotoObject" or with the id string 
      "photo_id = id_string".

    Author : Alexis Mignon (c)
    email  : alexis.mignon_at_gmail.com
    Date   : 05/08/2011
"""
import method_call
from  base import FlickrDictObject,FlickrError,dict_converter
from decorators import caller
import urllib2
from UserList import UserList

try :
    import Image
    import cStringIO
except ImportError : pass

PERSON_TOKENS = {}

try :
    from reflection import make_docstring
    import inspect
    class FlickrAutoDoc(type):
        def __new__(meta,classname,bases,classDict):
            self_name = classDict.get("__self_name__",None)
            for k,v in classDict.iteritems() :
                if hasattr(v,'flickr_method'):
                    ignore_arguments = ["api_key",self_name]
                    if inspect.isfunction(v) and self_name :
                        ignore_arguments.append(self_name)
                        v.__self_name__ = self_name
                    v.__doc__ = make_docstring(v.flickr_method,ignore_arguments,show_errors = False)
            return type.__new__(meta,classname,bases,classDict)

except ImportError:
    FlickrAutoDoc = type

class FlickrObject(object):
    """
        Base Object for Flickr API Objects
    """
    __converters__ = []
    __display__ = []
    __metaclass__ = FlickrAutoDoc

    def __init__(self,**params):
        params["loaded"] = False
        self._set_properties(**params)

    def _set_properties(self,**params):
        for c in self.__class__.__converters__ :
            c(params)
        self.__dict__.update(params)
    
    def setToken(self,filename = None, token = None, token_key = None, token_secret = None):
        if token is None :
            token = auth.token_factory(filename = filenam, token_key = token_key, token_secret = token_secret)
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


class FlickrList(UserList):
    def __init__(self,data = [],info = None):
        UserList.__init__(self,data)
        self.info = info
    
    def __str__(self):
        return '%s;%s'%(str(self.data),str(self.info))
    
    def __repr__(self):
        return '%s;%s'%(repr(self.data),repr(self.info))

class Activity(FlickrObject):
    @staticmethod
    @caller("flickr.activity.userPhotos")
    def userPhotos(**args):
        return args,_extract_activity_list

    @staticmethod
    @caller("flickr.activity.userComments")
    def userComments(**args):
        return args,_extract_activity_list
        
class Blog(FlickrObject):
    __display__ = ["id","name"]
    __converters__ = [
        dict_converter(["needspassword"],bool),
    ]
    __self_name__ = "blog_id"
    
    @caller("flickr.blogs.postPhoto")
    def postPhoto(self,**args):
        return _format_id("photo",args),lambda r : None

class BlogService(FlickrObject):
    __display__ = ["id","text"]
    __self_name__ = ["service"]

    @caller("flickr.blogs.getList")
    def getList(self,**args):
        try :
            args["service"] = args["service"].id
        except (KeyError,AttributeError): pass
        
        def format_result(r,token = None) :
            return [ Blog(token = token, **b) for b in _check_list(r["blogs"]["blog"])]

        return args,format_result

    @caller("flickr.blogs.postPhoto")
    def postPhoto(self,**args):
        return _format_id(args),lambda r : None
        
    @staticmethod    
    @caller("flickr.blogs.getServices")
    def getServices():
        return {},lambda r : [ BlogService(**s) for s in _check_list(r["services"]["service"]) ]    

class Collection(FlickrObject):
    __display__ = ["id","title"]
    __self_name__ = ["collection_id"]

    @caller("flickr.collections.getInfo")
    def getInfo(self):
        def format_result(r):
            collection = r["collection"]
            icon_photos = _check_list(collection["iconphotos"]["photo"])
            photos = []
            for p in photos :
                p["owner"] = Person(p["owner"])
                photos.append(Photo(**p))
            collection["iconphotos"] = photos
            return collection
        return args,format_result

    @caller("flickr.stats.getCollectionStats")
    def getStats(self,date):
        return {'date':date}, lambda r : int(r["stats"]["views"])

    @caller("flickr.collections.getTree")
    def getTree(**args):
        def format_result(r,token = None):
            collections = _check_list(r["collections"])
            collections_ = []
            for c in collections :
                sets = _check_list(c.pop("set"))
                sets_ = [ Photoset(token = token,**s) for s in sets]
                collections_.append(Collection(token = token,sets = sets_,**c))
            return collections_
        return _format_id("user",args),format_result

class CommonInstitution(FlickrObject) :
    __display__ = ["id","name"]
    
    @staticmethod
    @caller("flickr.commons.getInstitutions")
    def getInstitutions():
        def format_result(r):
            institutions = _check_list(r["institutions"]["institution"])
            institutions_ = []
            for i in institutions :
                urls = _check_list(i['urls']['url'])
                urls_ = []
                for u in urls :
                    u["url"] = u.pop("text")
                    urls_.append(CommonInstitutionUrl(**u))
                i["urls"] = urls_
                institutions_.append(CommonInstitution(id = i["nsid"],**i))
            return institutions_
        return {},format_result

class CommonInstitutionUrl(FlickrObject):
    pass

class Contact :
    @staticmethod
    @caller("flickr.contacts.getList")
    def getList(self,**args):
        def format_result(r):
            info = r["contacts"]
            contacts = [ Person(id = c["nsid"],**c) for c in _check_list(info["contact"])]
            return FlickrList(contacts,Info(**info))
        return args,format_result

class Gallery(FlickrObject):
    __display__ = [ "id","title"]
    __converters__ = [
        dict_converter(["date_create","date_update","count_photos","count_videos"],int),
    ]
    __self_name__ = "gallery_id"
    
    @caller("flickr.galleries.addPhoto")
    def addPhoto(self,**args):
        return _format_id("photo",args),lambda r : None

    @staticmethod
    @caller("flickr.galleries.create")
    def create(**args):
        return _format_id("primary_photo"), lambda r : Gallery(**r["gallery"])

    def editMedia(self,**args):
        """ method: flickr.galleries.editMeta
            
            Modify the meta-data for a gallery.
        
        Authentication:

            This method requires authentication with 'write' permission.

            Note: This method requires an HTTP POST request.
        
        Arguments:
            title (Required)
                The new title for the gallery.
            description (Optional)
                The new description for the gallery.         
        """
        r = method_call.call_api(method = "flickr.galleries.editMeta",auth_handler = self.getToken(),**args)
    
    def editPhoto(self,**args):
        """ method: flickr.galleries.editPhoto
            
            Edit the comment for a gallery photo.
        
        Authentication:

            This method requires authentication with 'write' permission.

            Note: This method requires an HTTP POST request.
        
        Arguments:
            photo_id (Required)
                The photo ID to add to the gallery.
            comment (Required)
                The updated comment the photo. 
        
        """
        if "photo" in args : args["photo_id"] = args.pop("photo").id
        r = method_call.call_api(method = "flickr.galleries.editPhoto",auth_handler = self.getToken(),**args)

    def editPhotos(self,**args):
        """ method: flickr.galleries.editPhotos
        
            Modify the photos in a gallery. Use this method to add, remove and re-order photos.
        
        Authentication:

            This method requires authentication with 'write' permission.

            Note: This method requires an HTTP POST request.
        
        Arguments:
            primary_photo_id (Required)
                The id of the photo to use as the 'primary' photo for the gallery. This id must also be passed along in photo_ids list argument.
            photo_ids (Required)
                A comma-delimited list of photo ids to include in the gallery. They will appear in the set in the order sent. This list must contain the primary photo id. This list of photos replaces the existing list. 
        
        """
        if "photos" in args : args["photo_ids"] = [ p.id for p in args.pop("photos") ]
        photo_ids = args["photo_ids"]
        if isinstance(photo_ids,list):
            args["photo_ids"] = ",".join(photo_ids)
        if "primary_photo" in args : args["primary_photo_id"] = args.pop("primary_photo").id
        
        r = method_call.call_api(method = "flickr.galleries.editPhotos",auth_handler = self.getToken(),**args)

    @staticmethod
    def getByUrl(url):
        """ method: flickr.urls.lookupGallery
            Returns gallery info, by url.
        
        Authentication:

            This method does not require authentication.
            
        """
        r = method_call.call_api(method = "flickr.urls.lookupGallery",url = url)
        gallery = r["gallery"]
        gallery["owner"] = Person(id = gallery["owner"])
        return Gallery(**gallery)
        
    def getInfo(self):
        """ method: flickr.galleries.getInfo
        
        Authentication:

            This method does not require authentication.
        """
        r = method_call.call_api(method = "flickr.galleries.getInfo")
        gallery = r["gallery"]
        
        gallery["owner"] = Person(gallery["owner"])
        pp_id = gallery.pop("primary_photo_id")
        pp_secret = gallery.pop("primary_photo_secret")
        pp_farm = gallery.pop("primary_photo_farm")
        pp_server = gallery.pop("primary_photo_server")
        
        gallery["primary_photo"] = Photo(id = pp_id, secret = pp_secret, server = pp_server, farm = pp_farm)
        
        return gallery
    
    def getPhotos(self,**args):
        """ method: flickr.galleries.getPhotos
        
            Return the list of photos for a gallery
        
        Authentication:

            This method does not require authentication.
        
        Arguments:
            extras (Optional)
                A comma-delimited list of extra information to fetch for 
                each returned record. Currently supported fields are: 
                description, license, date_upload, date_taken, owner_name, 
                icon_server, original_format, last_update, geo, tags, 
                machine_tags, o_dims, views, media, path_alias, url_sq, 
                url_t, url_s, url_m, url_z, url_l, url_o
            per_page (Optional)
                Number of photos to return per page. If this argument is 
                omitted, it defaults to 100. The maximum allowed value is 500.
            page (Optional)
                The page of results to return. If this argument is omitted, 
                it defaults to 1. 
        
        """
        try :
            extras = args["extras"]
            if isinstance(extras,list):
                args["extras"] = ",".join(extras)
        except KeyError : pass
        signed = args.pop("signed",True)
        token = self.getToken() if signed else None
        r = method_call.call_api(method = "flickr.galleries.getPhotos",auth_handler = token,gallery_id = self.id,**args)
        return _extract_photo_list(r)


class Category(FlickrObject):
    __display__ = ["id","name"]
    
    


class Info(FlickrObject):
    __converters__ = [
        dict_converter(["page","perpage","pages","total","count"],int)
    
    ]
    __display__ = ["page","perpage","pages","total","count"]
    pass

class Favorite :
    @staticmethod
    def remove(**args):
        """ method: flickr.favorites.remove
        
            Removes a photo from a user's favorites list.
        
        Authentication:

            This method requires authentication with 'write' permission.

            Note: This method requires an HTTP POST request.
        
        Arguments:
            photo_id (Required)
                The id of the photo to remove from the user's favorites. 
        
        """
        
        if "photo" in args : args["photo_id"] = args.pop("photo").id
        r = method_call.call_api(method = "flickr.favorites.remove",auth_handler = self.getToken(),**args)
    
    def getContext(self,**args):
        """ method: flickr.favorites.getContext
            
            Returns next and previous favorites for a photo in a user's favorites.
        
        Authentication:

            This method does not require authentication.
        
        Argument : 
            photo_id (Required)
                The id of the photo to fetch the context for.
            user_id (Required)
                The user who counts the photo as a favorite. 
                    
        """
        if "photo" in args : args["photo_id"] = args.pop("photo").id
        if "user" in args : args["user_id"] = args.pop("user").id
        r = method_call.call_api(method = "flickr.favorites.remove",auth_handler = self.getToken(),**args)
        return FlickrList(Photo(**r["prevphoto"]),Photo(**r["nextphoto"])),Info(count = r["count"])

class Group(FlickrObject):
    __converters__ = [
        dict_converter(["members","privacy"],int),
        dict_converter(["admin","eighteenplus","invistation_only"],bool)
    ]
    __display__ = ["id","name"]
    
    @staticmethod
    def browse(**args):
        """ method: flickr.groups.browse

            Browse the group category tree, finding groups and sub-categories.
        
        Authentication:

            This method requires authentication with 'read' permission.
        
        Arguments:
            cat_id (Optional)
                The category id to fetch a list of groups and sub-categories for. If not 
                specified, it defaults to zero, the root of the category tree. 
                    
        """
        if "cat" in args : args["cat_id"] = args.pop("cat")
        r = method_call.call_api(method = "flickr.groups.browse",auth_handler = self.getToken(),**args)
        
        cat = r["category"]
        subcats = [ Category(**c) for c in _check_list(cat.pop("subcats"))]
        groups = [ Group(id = g["nsid"], **g) for g in _check_list(cat.pop("group"))]
        
        return Category(id = args["cat_id"], subcats = subcats, groups = groups, **cat)

    def getInfo(self,**args):
        """ method: flickr.groups.getInfo
            Get information about a group.
        
        Authentication:

            This method does not require authentication.
        
        Arguments:.
            lang (Optional)
                The language of the group name and description to fetch. If the language 
                is not found, the primary language of the group will be returned. Valid 
                values are the same as in feeds. 
        
        """
        
        r = method_call.call_api(method = "flickr.groups.getInfo",**args)
        group = r["group"]
        return group
    
    def getUrl(self):
        """ method: flickr.urls.getGroup

            Returns the url to a group's page.
        
        Authentication:

            This method does not require authentication.

        """
        r = method_call.call_api(method = "flickr.urls.getGroup",group_id = self.id)
        return r["group"]["url"]
    
    @staticmethod
    def getByUrl(url):
        """ method: flickr.urls.lookupGroup

            Returns a group NSID, given the url to a group's page or photo pool.
        
        Authentication:

            This method does not require authentication.
        
        """
        r = method_call.call_api(method = "flickr.urls.lookupGroup",url = url)
        group = r["group"]
        group["name"] = group.pop("groupname")
        return Group(**group)
        
    
    @staticmethod
    def search(**args):
        """ method: flickr.groups.search -> (groups,info)
            
            Search for groups. 18+ groups will only be returned for 
            authenticated calls where the authenticated user is over 18.
        
        Authentication:

            This method does not require authentication.
        
        Arguments:
            text (Required)
                The text to search for.
            per_page (Optional)
                Number of groups to return per page. If this argument is 
                ommited, it defaults to 100. The maximum allowed value is 500.
            page (Optional)
                The page of results to return. If this argument is ommited, 
                it defaults to 1. 
        
        
        """
        r = method_call.call_api(method = "flickr.groups.search",**args)
        info = r["groups"]
        groups = [Group(**g) for g in info.pop("group")]
        return FlickrList(groups,Info(**info))
        
    def getMembers(self,**args):
        """ method: flickr.groups.members.getList
        
            Get a list of the members of a group. The call must be signed on behalf of a Flickr member, and the ability to see the group membership will be determined by the Flickr member's group privileges.
        Authentication:

            This method requires authentication with 'read' permission.
        
        Arguments:
            membertypes (Optional)
                Comma separated list of member types

                    2: member
                    3: moderator
                    4: admin

                By default returns all types. (Returning super rare member 
                type "1: narwhal" isn't supported by this API method)
                
            per_page (Optional)
                Number of members to return per page. If this argument is 
                omitted, it defaults to 100. The maximum allowed value is 500.
            page (Optional)
                The page of results to return. If this argument is omitted, 
                it defaults to 1. 
        
        """
        try :
            membertypes = args["membertypes"]
            if isinstance(membertypes,list):
                args["membertypes"] = ", ".join([str(i) for i in membertypes])
        except KeyError : pass
        r = method_call.call_api(method = "flickr.groups.members.getList", group_id = self.id,auth_handler = self.getToken(),**args)
        info = r["members"]
        return FlickrList([ Person(**p) for p in _check_list(info.pop("member"))],Info(**info))

    def addPhoto(self,**args):
        """ method: flickr.groups.pools.add
            Add a photo to a group's pool.
        
        Authentication:

            This method requires authentication with 'write' permission.

            Note: This method requires an HTTP POST request.
        
        Arguments:
            photo_id (Required)
                The id of the photo to add to the group pool. The photo 
                must belong to the calling user.        
        """
        if "photo" in args : args["photo_id"] = args.pop("photo").id
        r = method_call.call_api(method = "flickr.groups.pools.add",group_id = self.id, auth_handler = self.getToken(),**args)

    def getPoolContext(self,**args):
        """ method: flickr.groups.pools.getContext

            Returns next and previous photos for a photo in a group pool.
        
        Authentication:

            This method does not require authentication.
        
        Arguments:
            photo_id (Required)
                The id of the photo to fetch the context for.
        """
        if "photo" in args : args["photo_id"] = args.pop("photo").id
        r = method_call.call_api(method = "flickr.groups.pools.getContext",group_id = self.id,**args)
    
        return Photo(**r["prevphoto"]),Photo(r["nextphoto"])
    
    @staticmethod
    def getGroups(**args):
        """ method: flickr.groups.pools.getGroups
       
        Returns a list of groups to which you can add photos.
    
    Authentication:

        This method requires authentication with 'read' permission.
    
    Arguments:
        page (Optional)
            The page of results to return. If this argument is omitted, 
            it defaults to 1.
        per_page (Optional)
            Number of groups to return per page. If this argument is omitted, 
            it defaults to 400. The maximum allowed value is 400. 
        """
        r = method_call.call_api(method = "flickr.groups.pools.getGroups", auth_handler = self.getToken(),**args)
        info = r["groups"]
        return FlickrList([ Group(id = g["nsid"], **g) for g in info.pop("group") ],Info(**info))

    def getPhotos(self,**args):
        """ method: flickr.groups.pools.getPhotos
            
            Returns a list of pool photos for a given group, based on the permissions of the group and the user logged in (if any).
        
        Authentication:

            This method does not require authentication.
        
        Arguments:
            tags (Optional)
                A tag to filter the pool with. At the moment only one tag 
                at a time is supported.
            user_id (Optional)
                The nsid of a user. Specifiying this parameter will retrieve 
                for you only those photos that the user has contributed to 
                the group pool.
            extras (Optional)
                A comma-delimited list of extra information to fetch for 
                each returned record. Currently supported fields are: description, 
                license, date_upload, date_taken, owner_name, icon_server, 
                original_format, last_update, geo, tags, machine_tags, o_dims, 
                views, media, path_alias, url_sq, url_t, url_s, url_m, url_z, 
                url_l, url_o
            per_page (Optional)
                Number of photos to return per page. If this argument is 
                omitted, it defaults to 100. The maximum allowed value is 500.
            page (Optional)
                The page of results to return. If this argument is omitted, 
                it defaults to 1.       
        
        """
        try :
            extras = args["extras"]
            if isinstance(extras,list):
                args["extras"] = ",".join(extras)
        except KeyError : pass
        
        r = method_call.call_api(method = "flickr.groups.pools.getPhotos",group_id = self.id,**args)
        return _extract_photo_list(r)
    
    def removePhoto(self,**args):
        """ method: flickr.groups.pools.remove
        
            Remove a photo from a group pool.
        
        Authentication:

            This method requires authentication with 'write' permission.

            Note: This method requires an HTTP POST request.
        
        Arguments:
            photo_id (Required)
                The id of the photo to remove from the group pool. The photo 
                must either be owned by the calling user of the calling user 
                must be an administrator of the group.        
        """
        if "photo" in args : args["photo_id"] = args.pop("photo").id
        r = method_call.call_api(method = "flickr.groups.pools.remove",group_id = self.id, auth_handler = self.getToken(),**args)

class Interestingness:
    @staticmethod
    def getList(**args):
        """ method: flickr.interestingness.getList
            
            Returns the list of interesting photos for the most recent day or a user-specified date.
        
        Authentication:

            This method does not require authentication.
        
        Arguments:
            date (Optional)
                A specific date, formatted as YYYY-MM-DD, to return interesting photos for.
            extras (Optional)
                A comma-delimited list of extra information to fetch for each returned record. Currently supported fields are: description, license, date_upload, date_taken, owner_name, icon_server, original_format, last_update, geo, tags, machine_tags, o_dims, views, media, path_alias, url_sq, url_t, url_s, url_m, url_z, url_l, url_o
            per_page (Optional)
                Number of photos to return per page. If this argument is omitted, it defaults to 100. The maximum allowed value is 500.
            page (Optional)
                The page of results to return. If this argument is omitted, it defaults to 1. 
        
        """
        try :
            extras = args["extras"]
            if isinstance(extras,list):
                args["extras"] = ",".join(extras)
        except KeyError : pass

        r = method_call.call_api(method = "flickr.interestingness.getList",**args)
        return _extract_photo_list(r)
        
        

class Licence(FlickrObject):
    __display__ = ["id","name"]
    
    @staticmethod
    def getList():
        """ method: flickr.photos.licenses.getInfo
        
        Fetches a list of available photo licenses for Flickr.
        
    Authentication:
        This method does not require authentication.
        """

        r = method_call.call_api(method = "flickr.photos.licences.getInfo")
        licences = r["licences"]["licence"]
        if not isinstance(licences):
            licences = [licences]
        return [Licence(**l) for l in licences]

class Location(FlickrObject):
    __display__ = ["latitude","longitude","accuracy"]
    __converters__ = [
        dict_converter(["latitude","longitude"],float),
        dict_converter(["accuracy"],int),
    ]

class MachineTag(FlickrObject):
    class Namespace(FlickrObject):
        __display__ = ["text","usage","predicate"]
    
    class Pair(FlickrObject):
        __display__ = ["namespace","text","usage","predicate"]
    
    class Predicate(FlickrObject):
        __display__ = ["usage","text","namespaces"]
    
    class Value(FlickrObject):
        __display__ = ["usage","namespace","predicate","text"]
    
    @staticmethod
    def getNamespaces(**args):
        """ method: flickr.machinetags.getNamespaces
          
            Return a list of unique namespaces, optionally limited by a given predicate, in alphabetical order.
        
        Authentication:

            This method does not require authentication.
        
        Arguments:
            predicate (Optional)
                Limit the list of namespaces returned to those that have the following predicate.
            per_page (Optional)
                Number of photos to return per page. If this argument is omitted, it defaults to 100. The maximum allowed value is 500.
            page (Optional)
                The page of results to return. If this argument is omitted, it defaults to 1. 
        
        """
        r = method_call.call_api(method = "flickr.machinetags.getNamespaces",**args)
        info = r["namespaces"]
        return FlickrList([ Namespace(**ns) for ns in _check_list(info.pop("namespace"))],Info(info))
    
    @staticmethod
    def getPairs(**args):
        """ method: flickr.machinetags.getPairs
        
            Return a list of unique namespace and predicate pairs, optionally limited by predicate or namespace, in alphabetical order.
        
        Authentication:

            This method does not require authentication.
        
        Arguments:
            namespace (Optional)
                Limit the list of pairs returned to those that have the following namespace.
            predicate (Optional)
                Limit the list of pairs returned to those that have the following predicate.
            per_page (Optional)
                Number of photos to return per page. If this argument is omitted, it defaults to 100. The maximum allowed value is 500.
            page (Optional)
                The page of results to return. If this argument is omitted, it defaults to 1. 
        
        """
        r = method_call.call_api(method = "flickr.machinetags.getPairs",**args)
        info = r["pairs"]
        return FlickrList([ Pair(**p) for ns in _check_list(info.pop("pair"))],Info(info))

    def getPredicates(**args):
        """ method: flickr.machinetags.getPredicates
            
            Return a list of unique predicates, optionally limited by a given namespace.
        
        Authentication:

            This method does not require authentication.
        
        Arguments:
            namespace (Optional)
                Limit the list of predicates returned to those that have 
                the following namespace.
            per_page (Optional)
                Number of photos to return per page. If this argument is 
                omitted, it defaults to 100. The maximum allowed value is 500.
            page (Optional)
                The page of results to return. If this argument is omitted, 
                it defaults to 1.
        """
        r = method_call.call_api(method = "flickr.machinetags.getPredicates",**args)
        info = r["predicates"]
        return FlickrList([ Predicate(**p) for p in _check_list(info.pop("predicate"))],Info(info))
    
    @staticmethod
    def getRecentValues(**args):
        """ method: flickr.machinetags.getRecentValues
        
            Fetch recently used (or created) machine tags values.
        
        Authentication:

            This method does not require authentication.
        
        Arguments:

            namespace (Optional)
                A namespace that all values should be restricted to.
            predicate (Optional)
                A predicate that all values should be restricted to.
            added_since (Optional)
                Only return machine tags values that have been added since 
                this timestamp, in epoch seconds. 
        """
        r = method_call.call_api(method = "flickr.machinetags.getRecentValues",**args)
        info = r["values"]
        return FlickrList([ Value(**v) for v in _check_list(info.pop("value"))],Info(info))

    @staticmethod
    def getValues(**args):
        """ method: flickr.machinetags.getValues
            Return a list of unique values for a namespace and predicate.
        
        Authentication:

            This method does not require authentication.
        
        Arguments:
            namespace (Required)
                The namespace that all values should be restricted to.
            predicate (Required)
                The predicate that all values should be restricted to.
            per_page (Optional)
                Number of photos to return per page. If this argument is omitted, it defaults to 100. The maximum allowed value is 500.
            page (Optional)
                The page of results to return. If this argument is omitted, it defaults to 1. 
        
        """
        r = method_call.call_api(method = "flickr.machinetags.getRecentValues",**args)
        info = r["values"]
        return FlickrList([ Value(**v) for v in _check_list(info.pop("value"))],Info(info))


class Panda(FlickrObject):
    __display__ = ["name"]
    
    @staticmethod
    def getList():
        """ method: flickr.panda.getList
            Return a list of Flickr pandas, from whom you can request photos using the flickr.panda.getPhotos API method.

            More information about the pandas can be found on the dev blog.

        Authentication:

            This method does not require authentication.
        """
        r = method_call.call_api(method = "flickr.panda.getList")
        return [ Panda(name=p) for p in r["pandas"]["panda"] ]

    def getPhotos(self,**args):
        """ method: flickr.panda.getPhotos
            Ask the Flickr Pandas for a list of recent public (and "safe") photos.

            More information about the pandas can be found on the dev blog.
        
        Authentication:

            This method does not require authentication.
            
        You can fetch a list of all the current pandas using the flickr.panda.getList API method.
        Arguments:
                
            extras (Optional)
                A comma-delimited list of extra information to fetch for each returned record. Currently supported fields are: description, license, date_upload, date_taken, owner_name, icon_server, original_format, last_update, geo, tags, machine_tags, o_dims, views, media, path_alias, url_sq, url_t, url_s, url_m, url_z, url_l, url_o
            per_page (Optional)
                Number of photos to return per page. If this argument is omitted, it defaults to 100. The maximum allowed value is 500.
            page (Optional)
                The page of results to return. If this argument is omitted, it defaults to 1. 
        
        """
        try :
            extras = args["extras"]
            if isinstance(extras,list):
                args["extras"] = ",".join(extras)
        except KeyError : pass
        
        r = method_call.call_api(method = "flickr.panda.getPhotos",panda_name = self.name,**args)
        return _extract_photo_list(r)

class Person(FlickrObject):
    __converters__ = [
        dict_converter(["ispro"],bool),
    ]
    __display__ = ["id","username"]
    __self_name__ = "user_id"
    
    def __init__(self,**params):
        if not params.has_key("id"):
            if params.has_key("nsid"):
                params["id"] = params["nsid"]
            else : raise ValueError("The 'id' or 'nsid' parameter is required")
        FlickrObject.__init__(self,**params)

    @staticmethod
    def getFromToken(token = None, filename = None,token_key = None,token_secret = None):
        if token is None :
            if filename is not None :
                token = auth.AuthHandler.load(filename)
            elif token_key is None :
                raise ValueError("Either a token filename or token informations must be given")
            elif token_secret is None :
                raise ValueError("Missing token secret")
            else :
                token = auth.AuthHandler(API_KEY,API_SECRET,token_key,token_secret)
        return test.login(token)


    @staticmethod
    @caller("flickr.people.findByUsername")
    def findByEmail(find_email):
        return {'find_email':find_email},lambda r : Person(**r["user"])
        
    @staticmethod
    @caller("flickr.people.findByUsername")
    def findByUserName(username):
        return {'username':username},lambda r : Person(**r["user"])
        
    @staticmethod
    @caller("flickr.urls.lookupUser")
    def findByUrl(url):
        return {'url':url}, lambda r : Person(**r["user"])

    @caller("flickr.favorites.getContext")
    def getFavoriteContext(self,**args):
        def format_result(r,token = None):
            return FlickrList([Photo(token = token,**r["prevphoto"]),Photo(token = token,**r["nextphoto"])],Info(count = r["count"]))
        return _format_id("photo",args),format_result
    
    @caller("flickr.favorites.getPublicList")
    def getFavorites(self,**args):
        return _format_extras(args),_extract_photo_list

    @caller("flickr.favorites.getPublicList")
    def getPhotosets(self):
        def format_result(r,token = None):
            info = r["photosets"]
            photosets = info.pop("photoset")
            if not isinstance(photosets,list): phototsets = [photosets]
            return FlickrList([ Photoset(token = token,**ps) for ps in photosets ],Info(**info))
        return args,format_result

    @caller("flickr.favorites.getPublicList")
    def getPublicFavorites(self,**args):
        return _format_extras(args),_extract_photo_list

    @caller("flickr.people.getInfo")
    def getInfo(self,**args):      
        def format_result(r):
            user = r["person"]
            user["photos"] = FlickrDictObject("person",user["photos"])
            return user
        return args,format_result

    @caller("flickr.galleries.getList")
    def getGalleries(self,**args):
        def format_result(r,token = True):
            info = r["galleries"]
            galleries = _check_list(info.pop("gallery"))
            galleries_ = []
            
            for g in galleries_ :
                g["owner"] = Person(gallery["owner"])
                pp_id = g.pop("primary_photo_id")
                pp_secret = g.pop("primary_photo_secret")
                pp_farm = g.pop("primary_photo_farm")
                pp_server = g.pop("primary_photo_server")
                g["primary_photo"] = Gallery(id = pp_id, secret = pp_secret, server = pp_server, farm = pp_farm,token = token)
                galleries_.append(g)
            return FlickrList(galleries_,Info(**info))
        return args,format_result

    @caller("flickr.people.getPhotos")
    def getPhotos(self,**args):
        return args,_extract_photo_list

    @caller("flickr.urls.getUserPhotos")
    def getPhotosUrl(self):
        return args,lambda r : r["user"]["url"]
    
    @caller("flickr.urls.getUserProfile")
    def getProfileUrl(self):       
        return args,lambda r : r["user"]["url"] 

    @caller("flickr.people.getPublicPhotos")
    def getPublicPhotos(self,**args):
        return args,_extract_photo_list

    @caller("flickr.people.getPhotosOf")
    def getPhotosOf(self,**args):
        return _format_id("owner",_format_extras(args)),_extract_photo_list(r,token = self.Token())

    @caller("flickr.contacts.getPublicList")
    def getPublicContacts(self,**args):
        def format_result(r,token = None) :
            info = r["contacts"]
            contacts = [ Person(id = c["nsid"],token = token,**c) for c in _check_list(info["contact"])]
            return FlickrList(contacts,Info(**info))
        return args,format_result

    @caller("flickr.people.getPublicGroups")
    def getPublicGroups(self,**args):
        def format_result(r,token = None):
            groups = r["groups"]["group"]
            groups_ = []
            for gr in groups :
                gr["id"] = gr["nsid"]
                groups_.append(Group(token = token,**gr))
            return groups_
        return args,format_result

    @caller("flickr.people.getUploadStatus")
    def getUploadStatus(self,**args):
        return args,lambda r : r["user"]

    @caller("flickr.collections.getTree")
    def getCollectionTree(**args):
        def format_result(r,token = None):
            collections = _check_list(r["collections"])
            collections_ = []
            for c in collections :
                sets = _check_list(c.pop("set"))
                sets_ = [ Photoset(token = token,**s) for s in sets]
                collections_.append(Collection(token = token,sets = sets_,**c))
            return collections_
        return _format_id("collection",args),format_result

    @caller("flickr.photos.getContactsPublicPhotos")
    def getContactsPublicPhotos(self,**args):
        return _format_extras(args),_extract_photo_list(r,token = self.getToken())

    @caller("flickr.tags.getListUser")
    def getTags(self):
        return {}, lambda r : [Tag(**t) for t in r["who"]["tags"]["tag"]]

    @caller("flickr.tags.getListUserPopular")
    def getPopularTags(**args):
        return args,lambda r : [Tag(**t) for t in r["who"]["tags"]["tag"]]

class Photo(FlickrObject):
    __converters__ = [
        dict_converter(["isfamily","ispublic","isfriend","cancomment","canaddmeta","permcomment","permmeta","isfavorite"],bool),
        dict_converter(["posted","lastupdate"],int),
        dict_converter(["views","comments"],int),
    ]
    __display__ = ["id","title"]
    
    class Comment(FlickrObject):
        __display__ = ["id","author"]
        def delete(self):
            """ method: flickr.photos.comments.deleteComment
                Delete a comment as the currently authenticated user.
            
            Authentication:
                This method requires authentication with 'write' permission.

                Note: This method requires an HTTP POST request.
            """
            r = method_call.call_api(method = "flickr.photos.comments.deleteComment",comment_id = self.id, auth_handler = self.getToken())

        def edit(self, comment_text):
            """ method: flickr.photos.comments.editComment
                Edit the text of a comment as the currently authenticated user.
            
            Authentication:
                This method requires authentication with 'write' permission.

                Note: This method requires an HTTP POST request.
            
            Arguments:
                comment_text (Required)
                    Update the comment to this text.
            """
            r = method_call.call_api(method = "flickr.photos.comments.editComment",comment_id = self.id, comment_text = comment_text, auth_handler = self.getToken())

        @staticmethod
        def getRecentForContacts(**args):
            """ method: flickr.photos.comments.getRecentForContacts
            
                Return the list of photos belonging to your contacts that have been commented on recently.
            
            Authentication:
                This method requires authentication with 'read' permission.
            
            Arguments:
                date_lastcomment (Optional)
                    Limits the resultset to photos that have been commented on since this date. The date should be in the form of a Unix timestamp.

                    The default, and maximum, offset is (1) hour. 
                contacts_filter (Optional)
                    A comma-separated list of contact NSIDs to limit the scope of the query to.
                extras (Optional)
                    A comma-delimited list of extra information to fetch for each returned record. Currently supported fields are: description, license, date_upload, date_taken, owner_name, icon_server, original_format, last_update, geo, tags, machine_tags, o_dims, views, media, path_alias, url_sq, url_t, url_s, url_m, url_z, url_l, url_o
                per_page (Optional)
                    Number of photos to return per page. If this argument is omitted, it defaults to 100. The maximum allowed value is 500.
                page (Optional)
                    The page of results to return. If this argument is omitted, it defaults to 1. 
            """
            r = method_call.call_api(method = "flickr.photos.comments.getRecentForContacts", auth_handler = self.getToken(),**args)
            return _extract_photo_list(r)

    class Exif(FlickrObject):
        __display__ = ["tag","raw"]

    class Note(FlickrObject):
        __display__ = ["id","text"]
        def edit(self,**args):
            """ method: flickr.photos.notes.edit
                Edit a note on a photo. Coordinates and sizes are in pixels, based on the 500px image size shown on individual photo pages.
                
            Authentication:
                This method requires authentication with 'write' permission.

                Note: This method requires an HTTP POST request.
        
            Arguments:
                note_x (Required)
                    The left coordinate of the note
                note_y (Required)
                    The top coordinate of the note
                note_w (Required)
                    The width of the note
                note_h (Required)
                    The height of the note
                note_text (Required)
                    The description of the note 
            
            """
            r = method_call.call_api(method = "flickr.photos.notes.edit",node_id = self.id,auth_handler = self.getToken(),**args)
            return r
        
        def delete(self):
            """ method :flickr.photos.notes.delete
                Delete a note from a photo.
            
            Authentication:
                This method requires authentication with 'write' permission.

                Note: This method requires an HTTP POST request.
            """
            r = method_call.call_api(method = "flickr.photos.notes.delete",node_id = self.id,auth_handler = self.getToken(),**args)
            return r

    class Person(Person):
        __converters__ = [
            dict_converter(["x","y","h","w"],int)
        ]
        __display__ = ["id","photo","username","x","y","h","w"]
        
        def delete(self):
            """ method: flickr.photos.people.delete
                Remove a person from a photo.
                
            Authentication:
                This method requires authentication with 'write' permission.
                Note: This method requires an HTTP POST request.
            """
            r = method_call.call_api(method = "flickr.photos.people.delete", user_id = self.id, photo_id = self.photo.id,auth_handler = self.getToken())
            return r
        
        def deleteCoords(self):
            """ method: flickr.photos.people.deleteCoords
                Remove the bounding box from a person in a photo
                
            Authentication:
                This method requires authentication with 'write' permission.

                Note: This method requires an HTTP POST request.
            """
            r = method_call.call_api(method = "flickr.photos.people.deleteCoords", user_id = self.id, photo_id = self.photo.id,auth_handler = self.getToken())
            return r

        def editCoords(self,**args):
            """ method: flickr.photos.people.editCoords
                Edit the bounding box of an existing person on a photo.
                
            Authentication:
                This method requires authentication with 'write' permission.
                Note: This method requires an HTTP POST request.
            
            Arguments:
                person_x (Required)
                    The left-most pixel co-ordinate of the box around the person.
                person_y (Required)
                    The top-most pixel co-ordinate of the box around the person.
                person_w (Required)
                    The width (in pixels) of the box around the person.
                person_h (Required)
                    The height (in pixels) of the box around the person. 
            """
            r = method_call.call_api(method = "flickr.photos.people.deleteCoords", user_id = self.id, photo_id = self.photo.id,auth_handler = self.getToken(),**args)
            return r

    def addComment(self,**args):
        """ method: flickr.photos.comments.addComment
        
            Add comment to a photo as the currently authenticated user.
        
        Authentication:

            This method requires authentication with 'write' permission.

            Note: This method requires an HTTP POST request.

        Arguments:
            comment_text (Required)
                Text of the comment 
        """

        r = method_call.call_api(method = "flickr.photos.comments.addComment", photo_id = self.id,auth_handler = self.getToken(),**args)
        args["id"] = r["comment"]["id"]
        args["photo"] = self
        return Photo.Comment(**args)

    def addNote(self,**args):
        """ method: flickr.photos.notes.add
            Add a note to a photo. Coordinates and sizes are in pixels, 
            based on the 500px image size shown on individual photo pages.
            
        Authentication:
            This method requires authentication with 'write' permission.

            Note: This method requires an HTTP POST request.
        
        Arguments:
            note_x (Required)
                The left coordinate of the note
            note_y (Required)
                The top coordinate of the note
            note_w (Required)
                The width of the note
            note_h (Required)
                The height of the note
            note_text (Required)
                The description of the note 
        """
        r = method_call.call_api(method = "flickr.photos.notes.add", photo_id = self.id,auth_handler = self.getToken(),**args)
        args["id"] = r["note"]["id"]
        args["photo"] = self
        return Photo.Note(**args)

    def addPerson(self,**args):
        """ method: flickr.photos.people.add
        
            Add a person to a photo. Coordinates and sizes of boxes are 
            optional; they are measured in pixels, based on the 500px image 
            size shown on individual photo pages.
            
        Authentication:
            This method requires authentication with 'write' permission.

            Note: This method requires an HTTP POST request.
        
        Arguments:
            user or user_id (Required)
                The NSID of the user to add to the photo.
            person_x (Optional)
                The left-most pixel co-ordinate of the box around the person.
            person_y (Optional)
                The top-most pixel co-ordinate of the box around the person.
            person_w (Optional)
                The width (in pixels) of the box around the person.
            person_h (Optional)
                The height (in pixels) of the box around the person. 
        """
        try :
            user_id = args.pop("user_id").id
        except KeyError :
            user_id = args["user_id"]

        r = method_call.call_api(method = "flickr.photos.people.add", photo_id = self.id, user_id = user_id,auth_handler = self.getToken(),**args)
        return Photo.Person(id = user_id,**args)

    def addTags(self,tags):
         """ method : flickr.photos.addTags
                Add tags to a photo.
                
            Authentication:
                This method requires authentication with 'write' permission.

                Note: This method requires an HTTP POST request.
                
            Arguments:
                tags (Required)
                    The tags to add to the photo. 
                         
         """
         
         if isintance(tags,list):
             tags = ",".join(tags)
         
         r = method_call.call_api(method = "flickr.photos.addTags", photo_id = self.id, tags = tags,auth_handler = self.getToken())
         return r

    @staticmethod
    def batchCorrectLocation(**args):
        """ method: flickr.photos.geo.batchCorrectLocation
            Correct the places hierarchy for all the photos for a user at 
            a given latitude, longitude and accuracy.

            Batch corrections are processed in a delayed queue so it may 
            take a few minutes before the changes are reflected in a user's 
            photos.
        
        Authentication:
            This method requires authentication with 'write' permission.

            Note: This method requires an HTTP POST request.
        
        Arguments:
            lat (Required)
                The latitude of the photos to be update whose valid range 
                is -90 to 90. Anything more than 6 decimal places will 
                be truncated.
            lon (Required)
                The longitude of the photos to be updated whose valid range 
                is -180 to 180. Anything more than 6 decimal places will 
                be truncated.
            accuracy (Required)
                Recorded accuracy level of the photos to be updated. World 
                level is 1, Country is ~3, Region ~6, City ~11, Street ~16. 
                Current range is 1-16. Defaults to 16 if not specified.
            place_id (Optional)
                A Flickr Places ID. (While optional, you must pass either 
                a valid Places ID or a WOE ID.)
            woe_id (Optional)
                A Where On Earth (WOE) ID. (While optional, you must pass 
                either a valid Places ID or a WOE ID.)                     
        """
        
        try :
            place = args.pop("place")
            if isinstance(place,Place):
                args["place_id"] = place.id
            else :
                args["place_id"] = place
        except KeyError : pass
        r = method_call.call_api(method = "flickr.photos.geo.batchCorrectLocation", photo_id = self.id, auth_handler = self.getToken(),**args)

    def correctLocation(self,**args):
        """ method: flickr.photos.geo.correctLocation
        
        Authentication:
            This method requires authentication with 'write' permission.

            Note: This method requires an HTTP POST request.
        
        Arguments:
            place_id (Optional)
                A Flickr Places ID. (While optional, you must pass either 
                a valid Places ID or a WOE ID.)
            woe_id (Optional)
                A Where On Earth (WOE) ID. (While optional, you must pass 
                either a valid Places ID or a WOE ID.)
      
        """
        try :
            place = args.pop("place")
            if isinstance(place,Place):
                args["place_id"] = place.id
            else :
                args["place_id"] = place
        except KeyError : pass
        r = method_call.call_api(method = "flickr.photos.geo.batchCorrectLocation", photo_id = self.id, auth_handler = self.getToken(),**args)

    @staticmethod
    def checkUploadTickets(self,tickets):
        """ method: flickr.photos.upload.checkTickets
        
            Checks the status of one or more asynchronous photo upload tickets.
        
        Authentication:

            This method does not require authentication.
        
        Arguments:
            tickets (Required)
                A comma-delimited list of ticket ids
        """
        if isinstance(tickets,list):
            tickets = [ t.id if isinstance(t,UploadTicket) else t for t in tickets]
        tickets = ",".joint(tickets)
        
        r = method_call.call_api(method = "flickr.photos.upload.checkTickets")
        tickets = r["wrapper"]["uploader"]["ticket"]
        if not isinstance(tickets,list):
            tickets = [tickets]
        return [UploadTicket(**t) for t in tickets]

    def delete(self):
        """ method: flickr.photos.delete
            Delete a photo from flickr.
        
        Authentication:
            This method requires authentication with 'delete' permission.
            Note: This method requires an HTTP POST request.
        """
        r = method_call.call_api(method = "flickr.photos.delete", photo_id = self.id,auth_handler = self.getToken())
        return r

    def getAllContexts(self):
        """ method: flickr.photos.getAllContexts
            Returns all visible sets and pools the photo belongs to.
        
        Authentication
            This method does not require authentication.

        """
        r = method_call.call_api(method = "flickr.photos.getAllContexts", photo_id = self.id,auth_handler = self.getToken())
        photosets = []
        if r.has_key("set"):
            for s in r["set"]:
                photosets.append(Photoset(**s))
        pools = []
        if r.has_key("pool"):
            for p in r["pool"]:
                pools.append(Pool(**p))

        return photosets,pools
    
    def getComments(self,**args):
        """ method: flickr.photos.comments.getList
            Returns the comments for a photo
        
        Authentication:
            This method does not require authentication.
        
        Arguments:
            min_comment_date (Optional)
                Minimum date that a a comment was added. The date should 
                be in the form of a unix timestamp.
            max_comment_date (Optional)
                Maximum date that a comment was added. The date should be 
                in the form of a unix timestamp. 
        """
        r = method_call.call_api(method = "flickr.photos.comments.getList", photo_id = self.id,auth_handler = self.getToken(),**args)
        try :
            comments = r["comments"]["comment"]
        except KeyError :
            comments = []

        comments_ = []
        if not isinstance(comments,list):
            comments = [comments]
        for c in comments :
            author = c["author"]
            authorname = c.pop("authorname")
            c["author"] = Person(id = author,username = authorname)
            comments_.append(Photo.Comment(photo = self,**c))
        return comments_

    @staticmethod
    def getContactsPhotos(**args):
        """ method: flickr.photos.getContactsPhotos
            Fetch a list of recent photos from the calling users' contacts.
            
        Authentication:
            This method requires authentication with 'read' permission.
        
        Arguments:
            count (Optional)
                Number of photos to return. Defaults to 10, maximum 50. 
                This is only used if single_photo is not passed.
            just_friends (Optional)
                set as 1 to only show photos from friends and family 
                (excluding regular contacts).
            single_photo (Optional)
                Only fetch one photo (the latest) per contact, instead of 
                all photos in chronological order.
            include_self (Optional)
                Set to 1 to include photos from the calling user.
            extras (Optional)
                A comma-delimited list of extra information to fetch for 
                each returned record. Currently supported fields 
                include: license, date_upload, date_taken, owner_name, 
                icon_server, original_format, last_update. For more
                information see extras under flickr.photos.search. 
        """
        r = method_call.call_api(method = "flickr.photos.getContactsPhotos", auth_handler = self.getToken(),**args)
        photos = r["photos"]["photo"]
        photos_ = []
        for p in photos :
            photos_.append(Photo(**p))
        return photos_
    
    def getInfo(self):
        """
            method : flickr.photos.getInfo
        """
    
        r = method_call.call_api(method = "flickr.photos.getInfo", photo_id = self.id)
        photo = r["photo"]
        
        owner = photo["owner"]
        owner["id"] = owner["nsid"]
        photo["owner"] = Person(**owner)
        
        photo.update(photo.pop("usage"))
        photo.update(photo.pop("visibility"))
        photo.update(photo.pop("publiceditability"))
        photo.update(photo.pop("dates"))
        
        tags = []
        for t in _check_list(photo["tags"]["tag"])  :
            t["author"] = Person(id = t.pop("author"))
            tags.append(Tag(**t))
            
        photo["tags"] = tags        
        photo["notes"] = [Photo.Note(**n) for n in _check_list(photo["notes"]["note"])]
        
        return photo

    def getContext(self):
        """ method: flickr.photos.getContext
            Returns next and previous photos for a photo in a photostream.
        
        Authentication:
            This method does not require authentication.
        """
        r = method_call.call_api(method = "flickr.photos.getContext", photo_id = self.id,auth_handler = self.getToken())

        return Photo(**r["prevphoto"]),Photo("",**r["nextphoto"])

    @staticmethod
    def getCounts(**args):
        """ method: flickr.photos.getCounts
            Gets a list of photo counts for the given date ranges for 
            the calling user.
            
        Authentication:
            This method requires authentication with 'read' permission.
        
        Arguments:
            dates (Optional)
                A comma delimited list of unix timestamps, denoting the 
                periods to return counts for. They should be specified 
                smallest first.
            taken_dates (Optional)
                A comma delimited list of mysql datetimes, denoting the 
                periods to return counts for. They should be specified 
                smallest first. 
                    
        """
        r = method_call.call_api(method = "flickr.photos.getCounts", auth_handler = self.getToken(), **args)
        return r["photocounts"]["photocount"]

    def getExif(self):
        """ method: flickr.photos.getExif
            Retrieves a list of EXIF/TIFF/GPS tags for a given photo. 
            The calling user must have permission to view the photo.
            
        Authentication:
            This method does not require authentication.
        """
        
        if hasattr(self,"secret"):
            r = method_call.call_api(method = "flickr.photos.getExif", photo_id = self.id, secret = self.secret)            
        else :
            r = method_call.call_api(method = "flickr.photos.getExif", photo_id = self.id, auth_handler = self.getToken())
        try :
            return [Photo.Exif(**e) for e in r["photo"]["exif"]]
        except KeyError :
            return []
    
    def getFavoriteContext(self,**args):
        """ method: flickr.favorites.getContext
            
            Returns next and previous favorites for a photo in a user's favorites.
            
        Authentication:

            This method does not require authentication.
        
        Arguments:
            user_id (Required)
                The user who counts the photo as a favorite.
        
        """

        if "user" in args : args["user_id"] = args.pop("user")
        r = method_call.call_api(method = "flickr.photos.getFavoriteContext", photo_id = self.id,**args)
        return FlickrList( [Photo(**r["prevphoto"]),Photo(**r["nextphoto"])],Info(count = r["count"]) )
    
    def getFavorites(self,**args):
        """ method: flickr.photos.getFavorites
            Returns the list of people who have favorited a given photo.
            
        Authentication:
            This method does not require authentication.
        
        Arguments:
            page (Optional)
                The page of results to return. If this argument is omitted, 
                it defaults to 1.
            per_page (Optional)
                Number of users to return per page. If this argument is 
                omitted, it defaults to 10. The maximum allowed value is 50.
        """

        r = method_call.call_api(method = "flickr.photos.getFavorites", photo_id = self.id,auth_handler = self.getToken(),**args)
        
        
        photo = r["photo"]
        persons = photo.pop("person")
        persons_ = []
        if not isinstance(persons,list):
            persons = [persons]

        for p in persons :
            p["id"] = p["nsid"]
            persons_.append(Person(**p))
        infos = Info(**photo)
        return FlickrList( persons_,infos )
    
    def getGalleries(self,**args):
        """ method: flickr.galleries.getListForPhoto
        
            Return the list of galleries to which a photo has been added. 
            Galleries are returned sorted by date which the photo was added 
            to the gallery.
        
        Authentication:

            This method does not require authentication.
        
        Arguments:
            per_page (Optional)
                Number of galleries to return per page. If this argument 
                is omitted, it defaults to 100. The maximum allowed value 
                is 500.
            page (Optional)
                The page of results to return. If this argument is omitted, 
                it defaults to 1. 
        
        """
        r = method_call.call_api(method = "flickr.galleries.getListForPhoto", photo_id = self.id,**args)
        info = r["galleries"]
        galleries = _check_list(info.pop("gallery"))
        galleries_ = []
        
        for g in galleries_ :
            g["owner"] = Person(gallery["owner"])
            pp_id = g.pop("primary_photo_id")
            pp_secret = g.pop("primary_photo_secret")
            pp_farm = g.pop("primary_photo_farm")
            pp_server = g.pop("primary_photo_server")
            
            g["primary_photo"] = Gallery(id = pp_id, secret = pp_secret, server = pp_server, farm = pp_farm)
            
            galleries_.append(g)
        
        return FlickrList(galleries_,Info(**info))
    
    def getGeoPerms(self):
        """ method: flickr.photos.geo.getPerms
        
            Get permissions for who may view geo data for a photo.
        
        Authentication:
            This method requires authentication with 'read' permission.
        """
        
        r = method_call.call_api(method = "flickr.photos.geo.getPerms", photo_id = self.id,auth_handler = self.getToken())
        return GeoPerms(r["perms"])

    def getLocation(self):
        """ method: flickr.photos.geo.getLocation
            Get the geo data (latitude and longitude and the accuracy 
            level) for a photo.
            
        Authentication:
            This method does not require authentication.
        
        """
        r = method_call.call_api(method = "flickr.photos.geo.getLocation", photo_id = self.id)
        loc = r["photo"]["location"]
        return Location(photo = self, **loc)
    
    def getNotes(self):
        """
            Returns the list of notes for a photograph
        """
        
        return self.notes

    @staticmethod
    def getNotInSet(**args):
        """ method: flickr.photos.getNotInSet
            Returns a list of your photos that are not part of any sets.
            
        Authentication:
            This method requires authentication with 'read' permission.
        
        Arguments:
            max_upload_date (Optional)
                Maximum upload date. Photos with an upload date less than
                or equal to this value will be returned. The date can be
                in the form of a unix timestamp or mysql datetime.
            min_taken_date (Optional)
                Minimum taken date. Photos with an taken date greater 
                than or equal to this value will be returned. The date
                can be in the form of a mysql datetime or unix timestamp.
            max_taken_date (Optional)
                Maximum taken date. Photos with an taken date less than 
                or equal to this value will be returned. The date can be
                in the form of a mysql datetime or unix timestamp.
            privacy_filter (Optional)
                Return photos only matching a certain privacy level. Valid 
                values are:

                    1 public photos
                    2 private photos visible to friends
                    3 private photos visible to family
                    4 private photos visible to friends & family
                    5 completely private photos

            media (Optional)
                Filter results by media type. Possible values are all 
                (default), photos or videos
            min_upload_date (Optional)
                Minimum upload date. Photos with an upload date greater 
                than or equal to this value will be returned. The date 
                can be in the form of a unix timestamp or mysql datetime.
            extras (Optional)
                A comma-delimited list of extra information to fetch for 
                each returned record. Currently supported fields are: 
                description, license, date_upload, date_taken, owner_name, 
                icon_server, original_format, last_update, geo, tags, 
                machine_tags, o_dims, views, media, path_alias, url_sq, 
                url_t, url_s, url_m, url_z, url_l, url_o
            per_page (Optional)
                Number of photos to return per page. If this argument is 
                omitted, it defaults to 100. The maximum allowed value is 
                500.
            page (Optional)
                The page of results to return. If this argument is 
                omitted, it defaults to 1. 
        """
        
        r = method_call.call_api(method = "flickr.photos.getNotInSet", auth_handler = self.getToken(),**args)

        return _extract_photo_list(r)



    @staticmethod
    def getRecent(**args):
        """ method: flickr.photos.getRecent -> photos,infos

            Returns a list of the latest public photos uploaded to flickr.
            
        Authentication:
            This method does not require authentication.
        
        Arguments:
            extras (Optional)
                A comma-delimited list of extra information to fetch for 
                each returned record. Currently supported fields are: 
                description, license, date_upload, date_taken, owner_name, 
                icon_server, original_format, last_update, geo, tags, 
                machine_tags, o_dims, views, media, path_alias, url_sq, 
                url_t, url_s, url_m, url_z, url_l, url_o
            per_page (Optional)
                Number of photos to return per page. If this argument is 
                omitted, it defaults to 100. The maximum allowed value is 
                500.
            page (Optional)
                The page of results to return. If this argument is omitted, 
                it defaults to 1. 
                    
        """
        r = method_call.call_api(method = "flickr.photos.getRecent", auth_handler = self.getToken(),**args)
        
        return _extract_photo_list(r)
     

    def getSizes(self):
        """ method: flickr.photos.getSizes

            Returns the available sizes for a photo. The calling user must 
            have permission to view the photo.
        
        Authentication:
            This method does not require authentication.
        """
        if "sizes" not in self.__dict__ :
            r = method_call.call_api(method = "flickr.photos.getSizes", photo_id = self.id, auth_handler = self.getToken())
            self.__dict__["sizes"] = dict( [(s["label"],s) for s in r["sizes"]["size"]])
        return self.sizes

    def getStats(self,date):
        """ method: flickr.stats.getPhotosStats
        
            Get the number of views on a photo for a given date.
        
        Authentication:

            This method requires authentication with 'read' permission.
        
        Arguments:
            date (Required)
                Stats will be returned for this date. This should be in 
                either be in YYYY-MM-DD or unix timestamp format. A day 
                according to Flickr Stats starts at midnight GMT for all 
                users, and timestamps will automatically be rounded down 
                to the start of the day.
        """
        r = method_call.call_api(method = "flickr.stats.getPhotoStats",photo_id = self.id, auth_handler = self.getToken(), date = date)
        return dict([(k,int(v)) for k,v in r["stats"].iteritems()])
    
    def getTags(self):
        """ method: flickr.tags.getListPhoto

            Get the tag list for a given photo.
        
        Authentication:

            This method does not require authentication.
        """
        r = method_call.call_api(method = "flickr.tags.getListPhoto", photo_id = self.id)
        return [Tag(**t) for t in r["photo"]["tags"]["tag"]]
        
    def getPageUrl(self):
        """
            returns the URL to the photo's page.
        """
        return "http://www.flickr.com/photos/%s/%s"%(self.owner.id,self.id)
    
    def getPhotoUrl(self,size_label = 'Large'):
        """
            returns the URL to the photo page corresponding to the
            given size.
            
        Arguments :
            size_label : The label corresponding to the photo size 
            
                'Square' : 75x75
                'Thumbnail' : 100 on longest side
                'Small' : 240 on  longest side
                'Medium' : 500 on longest side
                'Medium 640' : 640 on longest side
                'Large' : 1024 on longest side
                'Original' : original photo (not always available)
        """
        try :
            return self.getSizes()[size_label]["url"]
        except KeyError :
            raise FlickrError("The requested size is not available")
            
    def getPhotoFile(self,size_label = 'Large'):
        """
            returns the URL to the photo file corresponding to the
            given size.
            
        Arguments :
            size_label : The label corresponding to the photo size 
            
                'Square' : 75x75
                'Thumbnail' : 100 on longest side
                'Small' : 240 on  longest side
                'Medium' : 500 on longest side
                'Medium 640' : 640 on longest side
                'Large' : 1024 on longest side
                'Original' : original photo (not always available)
        """
        try :
            return self.getSizes()[size_label]["source"]
        except KeyError :
            raise FlickrError("The requested size is not available")
        
    def save(self,filename,size_label = 'Large'):
        """
            saves the photo corresponding to the
            given size.
            
        Arguments :
            filename : target file name
            
            size_label : The label corresponding to the photo size 
            
                'Square' : 75x75
                'Thumbnail' : 100 on longest side
                'Small' : 240 on  longest side
                'Medium' : 500 on longest side
                'Medium 640' : 640 on longest side
                'Large' : 1024 on longest side
                'Original' : original photo (not always available)
        """
        r = urllib2.urlopen(self.getPhotoFile(size_label))
        with open(filename,'w+') as f:
            f.write(r.read())
    
    def show(self,size_label = 'Large'):
        """
            Shows the photo corresponding to the
            given size.
            
        Note: This methods uses PIL 
            
        Arguments :
            filename : target file name
            
            size_label : The label corresponding to the photo size 
            
                'Square' : 75x75
                'Thumbnail' : 100 on longest side
                'Small' : 240 on  longest side
                'Medium' : 500 on longest side
                'Medium 640' : 640 on longest side
                'Large' : 1024 on longest side
                'Original' : original photo (not always available)
        """
        
        r = urllib2.urlopen(self.getPhotoFile(size_label))
        b = cStringIO.StringIO(r.read())
        Image.open(b).show()

    @staticmethod
    def getUntagged(**args):
        """ method: flickr.photos.getUntagged -> photos,infos

            Returns a list of your photos with no tags.
            
        Authentication:
            This method requires authentication with 'read' permission.
        
        Arguments:
            min_upload_date (Optional)
                Minimum upload date. Photos with an upload date greater 
                than or equal to this value will be returned. The date 
                can be in the form of a unix timestamp or mysql datetime.
            max_upload_date (Optional)
                Maximum upload date. Photos with an upload date less than 
                or equal to this value will be returned. The date can be 
                in the form of a unix timestamp or mysql datetime.
            min_taken_date (Optional)
                Minimum taken date. Photos with an taken date greater than 
                or equal to this value will be returned. The date should 
                be in the form of a mysql datetime or unix timestamp.
            max_taken_date (Optional)
                Maximum taken date. Photos with an taken date less than 
                or equal to this value will be returned. The date can be 
                in the form of a mysql datetime or unix timestamp.
            privacy_filter (Optional)
                Return photos only matching a certain privacy level. Valid 
                values are:

                    1 public photos
                    2 private photos visible to friends
                    3 private photos visible to family
                    4 private photos visible to friends & family
                    5 completely private photos

            media (Optional)
                Filter results by media type. Possible values are all 
                (default), photos or videos
            extras (Optional)
        
        
        """
        r = method_call.call_api(method = "flickr.photos.getUntagged", auth_handler = self.getToken(),**args)
            
        return _extract_photo_list(r)

    @staticmethod
    def getWithGeoData(**args):
        """ method: flickr.photos.getWithGeoData
            Returns a list of your geo-tagged photos.
            
        Authentication:
            This method requires authentication with 'read' permission.
        
        Arguments:
            min_upload_date (Optional)
                Minimum upload date. Photos with an upload date greater 
                than or equal to this value will be returned. The date 
                should be in the form of a unix timestamp.
            max_upload_date (Optional)
                Maximum upload date. Photos with an upload date less than 
                or equal to this value will be returned. The date should 
                be in the form of a unix timestamp.
            min_taken_date (Optional)
                Minimum taken date. Photos with an taken date greater 
                than or equal to this value will be returned. The date 
                should be in the form of a mysql datetime.
            max_taken_date (Optional)
                Maximum taken date. Photos with an taken date less than 
                or equal to this value will be returned. The date should 
                be in the form of a mysql datetime.
            privacy_filter (Optional)
                Return photos only matching a certain privacy level. Valid 
                values are:

                    1 public photos
                    2 private photos visible to friends
                    3 private photos visible to family
                    4 private photos visible to friends & family
                    5 completely private photos

            sort (Optional)
                The order in which to sort returned photos. Deafults to 
                date-posted-desc. The possible values are: date-posted-asc, 
                date-posted-desc, date-taken-asc, date-taken-desc, 
                interestingness-desc, and interestingness-asc.
            media (Optional)
                Filter results by media type. Possible values are all 
                (default), photos or videos
            extras (Optional)
                A comma-delimited list of extra information to fetch for 
                each returned record. Currently supported fields are: 
                description, license, date_upload, date_taken, owner_name, 
                icon_server, original_format, last_update, geo, tags, 
                machine_tags, o_dims, views, media, path_alias, url_sq, 
                url_t, url_s, url_m, url_z, url_l, url_o
            per_page (Optional)
                Number of photos to return per page. If this argument is 
                omitted, it defaults to 100. The maximum allowed value is 
                500.
            page (Optional)
                The page of results to return. If this argument is 
                omitted, it defaults to 1.         
        """
        r = method_call.call_api(method = "flickr.photos.getWithGeoData", auth_handler = self.getToken(),**args)
            
        return _extract_photo_list(r)

    @staticmethod
    def getWithoutGeoData(**args):
        """ method: flickr.photos.getWithoutGeoData
            Returns a list of your photos which haven't been geo-tagged.
        
        Authentication:
            This method requires authentication with 'read' permission.
        
        Arguments:
            max_upload_date (Optional)
                Maximum upload date. Photos with an upload date less than 
                or equal to this value will be returned. The date should 
                be in the form of a unix timestamp.
            min_taken_date (Optional)
                Minimum taken date. Photos with an taken date greater 
                than or equal to this value will be returned. The date 
                can be in the form of a mysql datetime or unix timestamp.
            max_taken_date (Optional)
                Maximum taken date. Photos with an taken date less than 
                or equal to this value will be returned. The date can be 
                in the form of a mysql datetime or unix timestamp.
            privacy_filter (Optional)
                Return photos only matching a certain privacy level. 
                Valid values are:

                    1 public photos
                    2 private photos visible to friends
                    3 private photos visible to family
                    4 private photos visible to friends & family
                    5 completely private photos

            sort (Optional)
                The order in which to sort returned photos. Deafults to 
                date-posted-desc. The possible values are: date-posted-asc, 
                date-posted-desc, date-taken-asc, date-taken-desc, 4
                interestingness-desc, and interestingness-asc.
            media (Optional)
                Filter results by media type. Possible values are all 
                (default), photos or videos
            min_upload_date (Optional)
                Minimum upload date. Photos with an upload date greater 
                than or equal to this value will be returned. The date 
                can be in the form of a unix timestamp or mysql datetime.
            extras (Optional)
                A comma-delimited list of extra information to fetch for 
                each returned record. Currently supported fields are: 
                description, license, date_upload, date_taken, owner_name, 
                icon_server, original_format, last_update, geo, tags, 
                machine_tags, o_dims, views, media, path_alias, url_sq, 
                url_t, url_s, url_m, url_z, url_l, url_o
            per_page (Optional)
                Number of photos to return per page. If this argument is 
                omitted, it defaults to 100. The maximum allowed value is 
                500.
            page (Optional)
                The page of results to return. If this argument is omitted, 
                it defaults to 1.

        """
        r = method_call.call_api(method = "flickr.photos.getWithoutGeoData", auth_handler = self.getToken(),**args)
            
        return _extract_photo_list(r)

    def getPeople(self,**args):
        """ method: flickr.photos.people.getList
            Get a list of people in a given photo.
            
        Authentication:
            This method does not require authentication.
        """
        r = method_call.call_api(method = "flickr.photos.people.getList",photo_id = self.id, auth_handler = self.getToken(),**args)
        
        info = r["people"]
        people = info.pop("person")
        people_ = []
        if isinstance(people,Person):
            people = [people]
        for p in people :
            p["id"] = p["nsid"]
            p["photo"] = self
            people_.append(Photo.Person(**p))
        return people_

    @staticmethod
    def recentlyUpdated(**args):
        """ method: flickr.photos.recentlyUpdated

            Return a list of your photos that have been recently created 
            or which have been recently modified.

            Recently modified may mean that the photo's metadata (title, 
            description, tags) may have been changed or a comment has been 
            added (or just modified somehow :-)
        
        Authentication:
            This method requires authentication with 'read' permission.
        
        Arguments:
            min_date (Required)
                A Unix timestamp or any English textual datetime 
                description indicating the date from which modifications 
                should be compared.
            extras (Optional)
                A comma-delimited list of extra information to fetch for 
                each returned record. Currently supported fields are: 
                description, license, date_upload, date_taken, owner_name, 
                icon_server, original_format, last_update, geo, tags, 
                machine_tags, o_dims, views, media, path_alias, url_sq, 
                url_t, url_s, url_m, url_z, url_l, url_o
            per_page (Optional)
                Number of photos to return per page. If this argument is 
                omitted, it defaults to 100. The maximum allowed value 
                is 500.
            page (Optional)
                The page of results to return. If this argument is omitted, 
                it defaults to 1. 
        """
        r = method_call.call_api(method = "flickr.photos.recentlyUpdated", auth_handler = self.getToken(),**args)
            
        return _extract_photo_list(r)
    
    def removeLocation(self):
        """ method: flickr.photos.geo.removeLocation
            Removes the geo data associated with a photo.
        
        Authentication:
            This method requires authentication with 'write' permission.

            Note: This method requires an HTTP POST request.
        """
        r = method_call.call_api(method = "flickr.photos.geo.removeLocation",photo_id = self.id, auth_handler = self.getToken(),**args)

    def rotate(self,degrees):
        """ method:flickr.photos.transform.rotate
            Rotate a photo.
        
        Authentication:

            This method requires authentication with 'write' permission.

            Note: This method requires an HTTP POST request.
        
        Arguments:
            degrees (Required)
                The amount of degrees by which to rotate the photo (clockwise)
                from it's current orientation. Valid values are 90, 180 and 270.
        """

        r = method_call.call_api(method = "flickr.photos.geo.removeLocation",photo_id = self.id, degrees = degrees, auth_handler = self.getToken())
        photo_id  = r["photo_id"]["_content"]
        photo_secret = r["photo_id"]["secret"]
        return Photo(id = photo_id, secret = photo_secret)

    @staticmethod
    def search(**args):
        """ method: flickr.photos.search
            Return a list of photos matching some criteria. Only photos visible to 
            the calling user will be returned. To return private or semi-private photos, the caller must be authenticated with 'read' permissions, and have permission to view the photos. Unauthenticated calls will only return public photos.
            
        Authentication:
            This method does not require authentication.
        
        Arguments:
            user_id (Optional)
                The NSID of the user who's photo to search. If this 
                parameter isn't passed then everybody's public photos 
                will be searched. A value of "me" will search against the 
                calling user's photos for authenticated calls.
            tags (Optional)
                A comma-delimited list of tags. Photos with one or more 
                of the tags listed will be returned. You can exclude results 
                that match a term by prepending it with a - character.
            tag_mode (Optional)
                Either 'any' for an OR combination of tags, or 'all' for 
                an AND combination. Defaults to 'any' if not specified.
            text (Optional)
                A free text search. Photos who's title, description or 
                tags contain the text will be returned. You can exclude 
                results that match a term by prepending it with a - character.
            min_upload_date (Optional)
                Minimum upload date. Photos with an upload date greater 
                than or equal to this value will be returned. The date can 
                be in the form of a unix timestamp or mysql datetime.
            max_upload_date (Optional)
                Maximum upload date. Photos with an upload date less than 
                or equal to this value will be returned. The date can be 
                in the form of a unix timestamp or mysql datetime.
            min_taken_date (Optional)
                Minimum taken date. Photos with an taken date greater 
                than or equal to this value will be returned. The date 
                can be in the form of a mysql datetime or unix timestamp.
            max_taken_date (Optional)
                Maximum taken date. Photos with an taken date less than 
                or equal to this value will be returned. The date can be 
                in the form of a mysql datetime or unix timestamp.
            license (Optional)
                The license id for photos (for possible values see the 
                flickr.photos.licenses.getInfo method). Multiple licenses 
                may be comma-separated.
            sort (Optional)
                The order in which to sort returned photos. Deafults to 
                date-posted-desc (unless you are doing a radial geo query, 
                in which case the default sorting is by ascending distance 
                from the point specified). The possible values are: 
                date-posted-asc, date-posted-desc, date-taken-asc, 
                date-taken-desc, interestingness-desc, interestingness-asc, 
                and relevance.
            privacy_filter (Optional)
                Return photos only matching a certain privacy level. This 
                only applies when making an authenticated call to view 
                photos you own. Valid values are:

                    1 public photos
                    2 private photos visible to friends
                    3 private photos visible to family
                    4 private photos visible to friends & family
                    5 completely private photos

            bbox (Optional)
                A comma-delimited list of 4 values defining the Bounding 
                Box of the area that will be searched.

                The 4 values represent the bottom-left corner of the box 
                and the top-right corner, minimum_longitude, minimum_latitude, 
                maximum_longitude, maximum_latitude.

                Longitude has a range of -180 to 180 , latitude of -90 
                to 90. Defaults to -180, -90, 180, 90 if not specified.

                Unlike standard photo queries, geo (or bounding box) 
                queries will only return 250 results per page.

                Geo queries require some sort of limiting agent in order 
                to prevent the database from crying. This is basically 
                like the check against "parameterless searches" for queries 
                without a geo component.

                A tag, for instance, is considered a limiting agent as 
                are user defined min_date_taken and min_date_upload 
                parameters — If no limiting factor is passed we return 
                only photos added in the last 12 hours (though we may 
                extend the limit in the future).

            accuracy (Optional)
                Recorded accuracy level of the location information. 
                Current range is 1-16 :

                    World level is 1
                    Country is ~3
                    Region is ~6
                    City is ~11
                    Street is ~16

                Defaults to maximum value if not specified.
            safe_search (Optional)
                Safe search setting:

                    1 for safe.
                    2 for moderate.
                    3 for restricted.

                (Please note: Un-authed calls can only see Safe content.)
            content_type (Optional)
                Content Type setting:

                    1 for photos only.
                    2 for screenshots only.
                    3 for 'other' only.
                    4 for photos and screenshots.
                    5 for screenshots and 'other'.
                    6 for photos and 'other'.
                    7 for photos, screenshots, and 'other' (all).

            machine_tags (Optional)
                Aside from passing in a fully formed machine tag, there 
                is a special syntax for searching on specific properties :

                    Find photos using the 'dc' namespace : "machine_tags" => "dc:"
                    Find photos with a title in the 'dc' namespace : "machine_tags" => "dc:title="
                    Find photos titled "mr. camera" in the 'dc' namespace : "machine_tags" => "dc:title=\"mr. camera\"
                    Find photos whose value is "mr. camera" : "machine_tags" => "*:*=\"mr. camera\""
                    Find photos that have a title, in any namespace : "machine_tags" => "*:title="
                    Find photos that have a title, in any namespace, whose value is "mr. camera" : "machine_tags" => "*:title=\"mr. camera\""
                    Find photos, in the 'dc' namespace whose value is "mr. camera" : "machine_tags" => "dc:*=\"mr. camera\""

                Multiple machine tags may be queried by passing a 
                comma-separated list. The number of machine tags you can 
                pass in a single query depends on the tag mode (AND or OR) 
                that you are querying with. "AND" queries are limited to 
                (16) machine tags. "OR" queries are limited to (8).
        
            machine_tag_mode (Optional)
                Either 'any' for an OR combination of tags, or 'all' for 
                an AND combination. Defaults to 'any' if not specified.
            group_id (Optional)
                The id of a group who's pool to search. If specified, 
                only matching photos posted to the group's pool will be 
                returned.
            contacts (Optional)
                Search your contacts. Either 'all' or 'ff' for just friends 
                and family. (Experimental)
            woe_id (Optional)
                A 32-bit identifier that uniquely represents spatial entities. 
                (not used if bbox argument is present).

                Geo queries require some sort of limiting agent in order 
                to prevent the database from crying. This is basically 
                like the check against "parameterless searches" for queries 
                without a geo component.

                A tag, for instance, is considered a limiting agent as 
                are user defined min_date_taken and min_date_upload 
                parameters — If no limiting factor is passed we return 
                only photos added in the last 12 hours (though we may e
                xtend the limit in the future).
        
            place_id (Optional)
                A Flickr place id. (not used if bbox argument is present).

                Geo queries require some sort of limiting agent in order 
                to prevent the database from crying. This is basically 
                like the check against "parameterless searches" for queries 
                without a geo component.

                A tag, for instance, is considered a limiting agent as 
                are user defined min_date_taken and min_date_upload 
                parameters — If no limiting factor is passed we return 
                only photos added in the last 12 hours (though we may extend 
                the limit in the future).
                
            media (Optional)
                Filter results by media type. Possible values are all 
                (default), photos or videos
            has_geo (Optional)
                Any photo that has been geotagged, or if the value is "0" 
                any photo that has not been geotagged.

                Geo queries require some sort of limiting agent in order 
                to prevent the database from crying. This is basically 
                like the check against "parameterless searches" for queries 
                without a geo component.

                A tag, for instance, is considered a limiting agent as 
                are user defined min_date_taken and min_date_upload 
                parameters — If no limiting factor is passed we return 
                only photos added in the last 12 hours (though we may 
                extend the limit in the future).
                
            geo_context (Optional)
                Geo context is a numeric value representing the photo's 
                geotagginess beyond latitude and longitude. For example, 
                you may wish to search for photos that were taken "indoors" 
                or "outdoors".

                The current list of context IDs is :

                    0, not defined.
                    1, indoors.
                    2, outdoors.

                Geo queries require some sort of limiting agent in order 
                to prevent the database from crying. This is basically 
                like the check against "parameterless searches" for queries 
                without a geo component.

                A tag, for instance, is considered a limiting agent as 
                are user defined min_date_taken and min_date_upload 
                parameters — If no limiting factor is passed we return 
                only photos added in the last 12 hours (though we may 
                extend the limit in the future).
                
            lat (Optional)
                A valid latitude, in decimal format, for doing radial geo 
                queries.

                Geo queries require some sort of limiting agent in order 
                to prevent the database from crying. This is basically like 
                the check against "parameterless searches" for queries 
                without a geo component.

                A tag, for instance, is considered a limiting agent as 
                are user defined min_date_taken and min_date_upload 
                parameters — If no limiting factor is passed we return 
                only photos added in the last 12 hours (though we may 
                extend the limit in the future).
                
            lon (Optional)
                A valid longitude, in decimal format, for doing radial 
                geo queries.

                Geo queries require some sort of limiting agent in order 
                to prevent the database from crying. This is basically 
                like the check against "parameterless searches" for queries 
                without a geo component.

                A tag, for instance, is considered a limiting agent as 
                are user defined min_date_taken and min_date_upload 
                parameters — If no limiting factor is passed we return 
                only photos added in the last 12 hours (though we may 
                extend the limit in the future).
                
            radius (Optional)
                A valid radius used for geo queries, greater than zero 
                and less than 20 miles (or 32 kilometers), for use with 
                point-based geo queries. The default value is 5 (km).
            radius_units (Optional)
                The unit of measure when doing radial geo queries. Valid 
                options are "mi" (miles) and "km" (kilometers). The default 
                is "km".
            is_commons (Optional)
                Limit the scope of the search to only photos that are part 
                of the Flickr Commons project. Default is false.
            in_gallery (Optional)
                Limit the scope of the search to only photos that are in 
                a gallery? Default is false, search all photos.
            is_getty (Optional)
                Limit the scope of the search to only photos that are for 
                sale on Getty. Default is false.
            extras (Optional)
                A comma-delimited list of extra information to fetch for 
                each returned record. Currently supported fields are: 
                description, license, date_upload, date_taken, owner_name, 
                icon_server, original_format, last_update, geo, tags, 
                machine_tags, o_dims, views, media, path_alias, url_sq, 
                url_t, url_s, url_m, url_z, url_l, url_o
            per_page (Optional)
                Number of photos to return per page. If this argument is 
                omitted, it defaults to 100. The maximum allowed value is 
                500.
            page (Optional)
                The page of results to return. If this argument is omitted, 
                it defaults to 1. 
                    
        """
        try :
            args['user_id'] = args['user_id'].id
        except KeyError : pass
        try :
            extras = args["extras"]
            if isinstance(extras,list):
                args["extras"] = ",".join(extras)
        except KeyError : pass
        try :
            tags = args["tags"]
            if isinstance(tags,list):
                args["tags"] = ",".join(tags)
        except KeyError : pass
        r = method_call.call_api(method = "flickr.photos.search", **args)            
        return _extract_photo_list(r)

    def setContext(self,context):
        """ method: flickr.photos.geo.setContext
            Indicate the state of a photo's geotagginess beyond latitude 
            and longitude.

            Note : photos passed to this method must already be geotagged 
            (using the "flickr.photos.geo.setLocation" method).
            
        Authentication:

            This method requires authentication with 'write' permission.
            Note: This method requires an HTTP POST request.
        
        Arguments:
            context (Required)
                Context is a numeric value representing the photo's 
                geotagginess beyond latitude and longitude. For example, 
                you may wish to indicate that a photo was taken "indoors" 
                or "outdoors".

                The current list of context IDs is :

                    * 0, not defined.
                    * 1, indoors.
                    * 2, outdoors.

        """
        r = method_call.call_api(method = "flickr.photos.search", photo_id = self.id, context = context, auth_handler = self.getToken())
    
    def setContentType(self,**args):
        """ method: flickr.photos.setContentType
            Set the content type of a photo.
        
        Authentication:
            This method requires authentication with 'write' permission.

            Note: This method requires an HTTP POST request.
        
        Arguments:
            content_type (Required)
                The content type of the photo. Must be one of: 1 for Photo, 
                2 for Screenshot, and 3 for Other.        
        """
        r = method_call.call_api(method = "flickr.photos.setContentType", photo_id = self.id, auth_handler = self.getToken(),**args)            
        return r

    def setDates(self,**args):
        """ method: flickr.photos.setDates
            Set one or both of the dates for a photo.
        
        Authentication:

            This method requires authentication with 'write' permission.

            Note: This method requires an HTTP POST request.
        
        Arguments:
            date_posted (Optional)
                The date the photo was uploaded to flickr (see the dates 
                documentation)
            date_taken (Optional)
                The date the photo was taken (see the dates documentation)
            date_taken_granularity (Optional)
                The granularity of the date the photo was taken (see the 
                dates documentation) 
        
        """
        r = method_call.call_api(method = "flickr.photos.setDates", photo_id = self.id, auth_handler = self.getToken(),**args)
    
    def setGeoPerms(self,**args):
        """ method: flickr.photos.geo.setPerms

            Set the permission for who may view the geo data associated 
            with a photo.
        
        Authentication:
            This method requires authentication with 'write' permission.

            Note: This method requires an HTTP POST request.
        
        Arguments:
            is_public (Required)
                1 to set viewing permissions for the photo's location data 
                to public, 0 to set it to private.
            is_contact (Required)
                1 to set viewing permissions for the photo's location data 
                to contacts, 0 to set it to private.
            is_friend (Required)
                1 to set viewing permissions for the photo's location data 
                to friends, 0 to set it to private.
            is_family (Required)
                1 to set viewing permissions for the photo's location data 
                to family, 0 to set it to private.
        """
        r = method_call.call_api(method = "flickr.photos.geo.setPerms", photo_id = self.id, auth_handler = self.getToken(),**args)

    def setLicence(self,license):
        """ method: flickr.photos.licenses.setLicense
            Sets the license for a photo.
        
        Authentication:
            This method requires authentication with 'write' permission.

            Note: This method requires an HTTP POST request.
        
        Arguments:
            license_id (Required)
                The license to apply, or 0 (zero) to remove the current 
                license. Note : as of this writing the "no known copyright
                restrictions" license (7) is not a valid argument. 
        """
        if isinstance(license,License):
            license_id = license.id
        else :
            license_id = license

        r = method_call.call_api(method = "flickr.photos.licenses.setLicense", photo_id = self.id, license_id = license_id , auth_handler = self.getToken())         

    def setLocation(self,**args):
        """ method: flickr.photos.geo.setLocation
    
            Sets the geo data (latitude and longitude and, optionally, the 
            accuracy level) for a photo. Before users may assign location
            data to a photo they must define who, by default, may view that
            information. Users can edit this preference at 
            http://www.flickr.com/account/geo/privacy/. If a user has not 
            set this preference, the API method will return an error.
            
        Authentication:
            This method requires authentication with 'write' permission.

            Note: This method requires an HTTP POST request.
        
        Arguments:
            lat (Required)
                The latitude whose valid range is -90 to 90. Anything more 
                than 6 decimal places will be truncated.
            lon (Required)
                The longitude whose valid range is -180 to 180. Anything 
                more than 6 decimal places will be truncated.
            accuracy (Optional)
                Recorded accuracy level of the location information. World 
                level is 1, Country is ~3, Region ~6, City ~11, Street ~16. 
                Current range is 1-16. Defaults to 16 if not specified.
            context (Optional)
                Context is a numeric value representing the photo's 
                geotagginess beyond latitude and longitude. For example, 
                you may wish to indicate that a photo was taken "indoors" 
                or "outdoors".

                The current list of context IDs is :

                    * 0, not defined.
                    * 1, indoors.
                    * 2, outdoors.

                The default context for geotagged photos is 0, or "not defined" 
                    
        """
        r = method_call.call_api(method = "flickr.photos.geo.setLocation", photo_id = self.id, auth_handler = self.getToken(),**args)
        

    def setMeta(self,**args):
        """ method: flickr.photos.setMeta
            Set the meta information for a photo.
            
        Authentication:
            This method requires authentication with 'write' permission.

            Note: This method requires an HTTP POST request.
        
        Arguments:
            title (Required)
                The title for the photo.
            description (Required)
                The description for the photo. 
        """
        r = method_call.call_api(method = "flickr.photos.setMeta", photo_id = self.id, auth_handler = self.getToken(),**args)            
    
    def setPerms(self,**args):
        """ method: flickr.photos.setPerms
            Set permissions for a photo.

        Authentication:
            This method requires authentication with 'write' permission.

            Note: This method requires an HTTP POST request.
        
        Arguments:
            is_public (Required)
                1 to set the photo to public, 0 to set it to private.
            is_friend (Required)
                1 to make the photo visible to friends when private, 0 to not.
            is_family (Required)
                1 to make the photo visible to family when private, 0 to not.
            perm_comment (Required)
                who can add comments to the photo and it's notes. one of:
                0: nobody
                1: friends & family
                2: contacts
                3: everybody
            perm_addmeta (Required)
                who can add notes and tags to the photo. one of:
                0: nobody / just the owner
                1: friends & family
                2: contacts
                3: everybody                     
        """
        r = method_call.call_api(method = "flickr.photos.setPerms", photo_id = self.id, auth_handler = self.getToken(),**args)            
        return r
        
    def setSafetyLevel(self,**args):
        """ method: flickr.photos.setSafetyLevel
            Set the safety level of a photo.
        
        Authentication:
            This method requires authentication with 'write' permission.

            Note: This method requires an HTTP POST request.
        
        Arguments:
            safety_level (Optional)
                The safety level of the photo. Must be one of: 1 for Safe, 
                2 for Moderate, and 3 for Restricted.
            hidden (Optional)
                Whether or not to additionally hide the photo from public
                searches. Must be either 1 for Yes or 0 for No.                     
        """
        r = method_call.call_api(method = "flickr.photos.setSafetyLevel", photo_id = self.id, auth_handler = self.getToken(),**args)            

    def setTags(self,tags):
        """ method: flickr.photos.setTags
            Set the tags for a photo.
        
        Authentication:
            This method requires authentication with 'write' permission.

            Note: This method requires an HTTP POST request.
        
        Arguments:
            tags (Required)
                All tags for the photo (as a single space-delimited string).        
        """
        r = method_call.call_api(method = "flickr.photos.setTags", photo_id = self.id, auth_handler = self.getToken(),tags = tags)


        
class PhotoGeo(object):
    @staticmethod
    def photosForLocation(**args):
        """ method:  flickr.photos.geo.photosForLocation
        
            Return a list of photos for the calling user at a specific 
            latitude, longitude and accuracy
        
        Authentication:
            This method requires authentication with 'read' permission.
        
        Arguments:
            lat (Required)
                The latitude whose valid range is -90 to 90. Anything more 
                than 6 decimal places will be truncated.
            lon (Required)
                The longitude whose valid range is -180 to 180. Anything 
                more than 6 decimal places will be truncated.
            accuracy (Optional)
                Recorded accuracy level of the location information. World 
                level is 1, Country is ~3, Region ~6, City ~11, Street ~16. 
                Current range is 1-16. Defaults to 16 if not specified.
            extras (Optional)
                A comma-delimited list of extra information to fetch for 
                each returned record. Currently supported fields are: 
                description, license, date_upload, date_taken, owner_name, 
                icon_server, original_format, last_update, geo, tags, 
                machine_tags, o_dims, views, media, path_alias, url_sq, 
                url_t, url_s, url_m, url_z, url_l, url_o
            per_page (Optional)
                Number of photos to return per page. If this argument is 
                omitted, it defaults to 100. The maximum allowed value 
                is 500.
            page (Optional)
                The page of results to return. If this argument is omitted, 
                it defaults to 1. 
        """
        r = method_call.call_api(method = "flickr.photos.licences.getInfo",auth_handler = self.getToken(),**args)
        return _extract_photo_list(r)

class PhotoGeoPerms(FlickrObject):
    __converters__ = [
        dict_converter(["ispublic","iscontact","isfamily","isfriend"],bool)
    ]
    __display__ = ["id","ispublic","iscontact","isfamily","isfriend"]

class Photoset(FlickrObject):
    __converters__ = [
        dict_converter(["photos"],int),
    ]
    __display__ = ["id","title"]

    class Comment(FlickrObject):
        __display__ = ["id"]
        def delete(self):
            """ method: flickr.photosets.comments.deleteComment
                Delete a photoset comment as the currently authenticated user.
            
            Authentication:

                This method requires authentication with 'write' permission.

                Note: This method requires an HTTP POST request.
            """
            r = method_call.call_api(method = "flickr.photosets.comments.deleteComment", comment_id = self.id, auth_handler = self.getToken())

        def getToken(self):
            return self.owner.getToken()

        def edit(self,**args):
            """ method: flickr.photosets.comments.editComment
                Edit the text of a comment as the currently authenticated user.
            
            Authentication:

                This method requires authentication with 'write' permission.

                Note: This method requires an HTTP POST request.
            
            Arguments:
                comment_text (Required)
                    Update the comment to this text. 
            
            """
            r = method_call.call_api(method = "flickr.photosets.comments.editComment", comment_id = self.id, auth_handler = self.getToken(),**args)
            self._set_properties(**args)

    def addPhoto(self,**args):
        """ method: flickr.photosets.addPhoto

            Add a photo to the end of an existing photoset.

        Authentication:

            This method requires authentication with 'write' permission.

            Note: This method requires an HTTP POST request.
        Arguments:
            photo or photo_id(Required)        
        """
        try :
            args["photo_id"] = args.pop("photo").id
        except KeyError : pass

        r = method_call.call_api(method = "flickr.photosets.addPhoto",photoset_id = self.id, auth_handler = self.getToken(),**args)

    def addComment(self,**args):
        """ method: flickr.photosets.comments.addComment
        
            Add a comment to a photoset.
        
        Authentication:

            This method requires authentication with 'write' permission.

            Note: This method requires an HTTP POST request.
        
        Arguments:
            comment_text (Required)
                Text of the comment 
        """
        r = method_call.call_api(method = "flickr.photosets.comments.addComment",photoset_id = self.id, auth_handler = self.getToken(),**args)
        return Photoset.Comment(photoset = self,**r)

    @staticmethod
    def create(**args):
        """ method: flickr.photosets.create
            Create a new photoset for the calling user.
        
        Authentication:
            This method requires authentication with 'write' permission.

            Note: This method requires an HTTP POST request.
        
        Arguments:
            title (Required)
                A title for the photoset.
            description (Optional)
                A description of the photoset. May contain limited html.
            primary_photo or primary_photo_id (Required)
                The photo or id of the photo to represent this set. The photo must belong to the calling user. 
        """
        try :
            pphoto = args.pop("primary_photo")
            pphoto_id = pphoto.id
        except KeyError :
            pphoto_id = args.pop("primary_photo_id")
            pphoto = Photo(id = pphoto_id)
        args["primary_photo_id"] = pphoto_id

        r = method_call.call_api(method = "flickr.photosets.create", auth_handler = self.getToken(),**args)
        photoset = r["photoset"]
        photoset["primary"] = pphoto
        return Photoset(**photoset)

    def delete(self):
        """ method: flickr.photosets.delete
            Delete a photoset.
        
        Authentication:

            This method requires authentication with 'write' permission.

            Note: This method requires an HTTP POST request.
        """
        r = method_call.call_api(method = "flickr.photosets.delete", photoset_id = self.id, auth_handler = self.getToken())

    
    def editMeta(self,**args):
        """ method: flickr.photosets.editMeta
                Modify the meta-data for a photoset.
            
            Authentication:

                This method requires authentication with 'write' permission.

                Note: This method requires an HTTP POST request.
            
            Arguments:
                title (Required)
                    The new title for the photoset.
                description (Optional)
                    A description of the photoset. May contain limited html. 
            
        """
        r = method_call.call_api(method = "flickr.photosets.editMeta", photoset_id = self.id, auth_handler = self.getToken(),**args)
    
    def editPhotos(self,**args):
        """ method:flickr.photosets.editPhotos

            Modify the photos in a photoset. Use this method to add, 
            remove and re-order photos.
            
        Authentication:

            This method requires authentication with 'write' permission.

            Note: This method requires an HTTP POST request.
        
        Arguments:
            primary_photo_id (Required)
                The id of the photo to use as the 'primary' photo for the 
                set. This id must also be passed along in photo_ids list 
                argument.
            photo_ids (Required)
                A comma-delimited list of photo ids to include in the set. 
                They will appear in the set in the order sent. This list 
                must contain the primary photo id. All photos must belong 
                to the owner of the set. This list of photos replaces the 
                existing list. Call flickr.photosets.addPhoto to append 
                a photo to a set.
        """
        
        try :
            args["primary_photo_id"] = args.pop("primary_photo").id
        except KeyError : pass
        try :
            args["photo_ids"] = [ p.id for p in args["photos"] ]
        except KeyError : pass
        
        photo_ids = args["photo_ids"]
        if isinstance(photo_ids,list):
            args["photo_ids"] = ", ".join(photo_ids)
            
        r = method_call.call_api(method = "flickr.photosets.editPhotos", photoset_id = self.id, auth_handler = self.getToken(),**args)

    def getComments(self):
        """ method: flickr.photosets.comments.getList
            Returns the comments for a photoset.
        
        Authentication:

            This method does not require authentication.
        """
        r = method_call.call_api(method = "flickr.photosets.comments.getList", photoset_id = self.id)
        
        comments = r["comments"]["comment"]
        comments_ = []
        if not isinstance(comments,list):
            comments = [comments]
        for c in comments :
            author = c["author"]
            authorname = c.pop("authorname")
            c["author"] = Person(id = author,username = authorname)
            comments_.append(Photoset.Comment(photo = self,**c))
        return comments_

    def getContext(self,**args):
        """ method: flickr.photosets.getContext
        
            Returns next and previous photos for a photo in a set.
        
        Authentication:

            This method does not require authentication.
        
        Arguments:
            photo_id (Required)
                The id of the photo to fetch the context for.

        """
        
        try :
            photo_id = args.pop("photo").id
        except KeyError :
            photo_id = args["photo_id"]
        
        r = method_call.call_api(method = "flickr.photosets.getContext", photoset_id = self.id, auth_handler = self.getToken(),**args)
        return Photo(**r["prevphoto"]),Photo(**r["nextphoto"])

    def getInfo(self):
        """ method: flickr.photosets.getInfo
        
            Gets information about a photoset.
            
        Authentication:
            This method does not require authentication.
        """
        r = method_call.call_api(method = "flickr.photosets.getInfo",photoset_id = self.id)
        photoset = r["photoset"]
        photoset["owner"] = Person(id = photoset["owner"])
        return photoset

    def getPhotos(self,**args):
        """ method: flickr.photosets.getPhotos
            Get the list of photos in a set.
        
        Authentication:

            This method does not require authentication.
        
        Arguments:
            extras (Optional)
                A comma-delimited list of extra information to fetch for 
                each returned record. Currently supported fields are: license, 
                date_upload, date_taken, owner_name, icon_server, original_format, 
                last_update, geo, tags, machine_tags, o_dims, views, media, 
                path_alias, url_sq, url_t, url_s, url_m, url_o
            privacy_filter (Optional)
                Return photos only matching a certain privacy level. This 
                only applies when making an authenticated call to view a 
                photoset you own. Valid values are:

                    * 1 public photos
                    * 2 private photos visible to friends
                    * 3 private photos visible to family
                    * 4 private photos visible to friends & family
                    * 5 completely private photos

            per_page (Optional)
                Number of photos to return per page. If this argument is 
                omitted, it defaults to 500. The maximum allowed value is 500.
            page (Optional)
                The page of results to return. If this argument is omitted, 
                it defaults to 1.
            media (Optional)
                Filter results by media type. Possible values are all (default), 
                photos or videos 
        """
        
        try :
            extras = args["extras"]
            if isinstance(extras,list):
                args["extras"] = u",".join(extras)
        except KeyError : pass
        
        r = method_call.call_api(method = "flickr.photosets.getPhotos",photoset_id = self.id, **args)
        ps = r["photoset"]
        return FlickrList([Photo(**p) for p in ps["photo"]],
                           Info(pages = ps["pages"],
                                page = ps["page"],
                                perpage = ps["perpage"],
                                total = ps["total"]))
    
    def getStats(self,date):
        """ method: flickr.stats.getPhotosetStats

            Get the number of views on a photoset for a given date.
        
        Authentication:

            This method requires authentication with 'read' permission.
        
        Arguments:
            date (Required)
                Stats will be returned for this date. This should be in 
                either be in YYYY-MM-DD or unix timestamp format. A day 
                according to Flickr Stats starts at midnight GMT for all 
                users, and timestamps will automatically be rounded down 
                to the start of the day.
        """
        r = method_call.call_api(method = "flickr.stats.getPhotosetStats",photoset_id = self.id, auth_handler = self.getToken(), date = date)
        return dict([(k,int(v)) for k,v in r["stats"].iteritems()])
        
    @staticmethod
    def orderSets(**args):
        """ method:flickr.photosets.orderSets
            Set the order of photosets for the calling user.
        
        Authentication:
            This method requires authentication with 'write' permission.

            Note: This method requires an HTTP POST request.
        
        Arguments:
            photoset_ids (Required)
                A comma delimited list of photoset IDs, ordered with the set to show
                first, first in the list. Any set IDs not given in the list will be 
                set to appear at the end of the list, ordered by their IDs. 
        
        """
        try :
            photosets = args.pop("photosets")
            args["photoset_ids"] = [ ps.id for ps in photosets ]
        except KeyError : pass
        
        photoset_ids = args["photoset_ids"]
        if isinstance(photoset_ids,list):
            args["photoset_ids"] = ", ".join(photoset_ids)
        
        r = method_call.call_api(method = "flickr.photosets.orderSets", auth_handler = self.getToken(),**args)
        
    def removePhoto(self,**args):
        """ method: flickr.photosets.removePhoto
            Remove a photo from a photoset.
        
        Authentication:

            This method requires authentication with 'write' permission.

            Note: This method requires an HTTP POST request.
        
        Arguments:
            photo_id (Required)
                The id of the photo to remove from the set. 
        
        """
        
        try :
            args["photo_id"] = args.pop("photo").id
        except KeyError : pass
        
        r = method_call.call_api(method = "flickr.photosets.removePhoto", photoset_id = self.id, auth_handler = self.getToken(),**args)
        
    def removePhotos(self,**args):
        """ method: flickr.photosets.removePhotos
            Remove multiple photos from a photoset.
        
        Authentication:

            This method requires authentication with 'write' permission.

            Note: This method requires an HTTP POST request.
        
        Arguments:
            photo_ids (Required)
                Comma-delimited list of photo ids to remove from the photoset.
        """
        
        try :
            args["photo_ids"] = [ p.id for p in args.pop("photos") ]
        except KeyError : pass
        
        photo_ids = args["photo_ids"]
        if isinstance(photo_ids,list):
            args["photo_ids"] = u",".join(photo_ids)
        
        r = method_call.call_api(method = "flickr.photosets.removePhotos", photoset_id = self.id, auth_handler = self.getToken(),**args)
    
    def reorderPhotos(self,**args):
        """ method: flickr.photosets.reorderPhotos
        
        Authentication:

            This method requires authentication with 'write' permission.

            Note: This method requires an HTTP POST request.
        
        Arguments:
            photo_ids (Required)
                Ordered, comma-delimited list of photo ids. Photos that are not in the list will keep their original order 
        """

        try :
            args["photo_ids"] = [ p.id for p in args.pop("photos") ]
        except KeyError : pass
        
        photo_ids = args["photo_ids"]
        if isinstance(photo_ids,list):
            args["photo_ids"] = u",".join(photo_ids)
        
        r = method_call.call_api(method = "flickr.photosets.reorderPhotos", photoset_id = self.id, auth_handler = self.getToken(),**args)
       
    def setPrimaryPhoto(self,**args):
        """ method: flickr.photosets.setPrimaryPhoto
            Set photoset primary photo
        
        Authentication:

            This method requires authentication with 'write' permission.

            Note: This method requires an HTTP POST request.
        
        Arguments:
            photo_id (Required)
                The id of the photo to set as primary. 
        """
        try :
            args["photo_id"] = args.pop("photo").id
        except KeyError : pass
        
        r = method_call.call_api(method = "flickr.photosets.setPrimaryPhoto", photoset_id = self.id, auth_handler = self.getToken(),**args)


class Place(FlickrObject):
    __display__ = ["id","name","woeid","latitude","longitude"]
    __converters__ = [
        dict_converter(["latitude","longitude"],float),
    ]
    __self_name__ = 'place_id'
    class ShapeData(FlickrObject):
        class Polyline(FlickrObject):
            pass
    
    class Type(FlickrObject):
        __display__ = ["id","text"]
    
    class Tag(FlickrObject):
        __display__ = ["text","count"]
        __converters__ = [
            dict_converter(["count"],int),
        ]

    @staticmethod
    @caller("flickr.places.find")
    def find(**args):
        return args,_extract_place_list

    @staticmethod
    @caller("flickr.places.findByLatLon")
    def findByLatLon(**args):
        return args,_extract_place_list
        
    @caller("flickr.places.getChildrenWithPhotosPublic")
    def getChildrenWithPhotoPublic(self,**args):
        return args,_extract_place_list
       
    @caller("flickr.places.getInfo")
    def getInfo(self,**args):
        def format_result(r):
            return Place.parse_place(r["place"])
        return args,format_result

    @staticmethod
    def parse_shapedata(shape_data_dict):
        shapedata = shape_data_dict.copy()
        shapedata["polylines"] = [ Place.ShapeData.Polyline(coords = p.split(" ")) for p in shapedata["polylines"]["polyline"]]
        if "url" in shapedata :
            shapedata["shapefile"] = shapedata.pop("urls")["shapefile"].text
        return shapedata
        
        
    @staticmethod
    def parse_place(place_dict):
        place = place_dict.copy()
        if "locality" in place :
            place["locality"] = Place(**Place.parse_place(place["locality"]))
            
        if "county" in place :
            place["county"] = Place(**Place.parse_place(place["county"]))
        
        if "region" in place :
            place["region"] = Place(**Place.parse_place(place["region"]))

        if "country" in place :
            place["country"] = Place(**Place.parse_place(place["country"]))
        
        if "shapedata" in place :
            shapedata = Place.parse_shapedata(place["shapedata"])
            place["shapedata"] = Place.ShapeData(**shapedata)
            
        if "text" in place :
            place["name"] = place.pop("text")

        place["id"] = place.pop("place_id")
        return place

    @staticmethod
    @caller("flickr.places.getInfoByUrl")
    def getByUrl(url):
        return {'url' : url}, lambda r : Place(**Place.parse_place(r["place"]))
    
    @staticmethod
    @caller("flickr.places.getPlaceTypes")
    def getPlaceTypes(**args):
        def format_result(r):
            places_types = r["place_types"]["place_type"]
            return [ Place.Type(id = pt.pop("place_type_id"), **pt) for pt in place_types ]
        return args,format_result

    @staticmethod
    @caller("flickr.places.getShapeHistory")
    def getShapeHistory(**args):
        def format_result(r):
            info = r["shapes"]
            return [ Place.ShapeData(**Place.parse_shapedata(sd)) for sd in _check_list(info.pop("shapedata"))]
        return args,format_result

    @caller("flickr.places.getTopPlacesList")
    def getTopPlaces(self,**args):
        return args,_extract_place_list
        
    @staticmethod
    @caller("flickr.places.placesForBoundingBox")
    def placesForBoundingBox(**args):
        def format_result(r):
            info = r["places"]
            return [Place(id = place.pop("place_id"), **place) for place in info.pop("place")]
        return args,format_result
    
    @staticmethod
    @caller("flickr.places.placesForTags")    
    def placesForTags(**args):
        return args,_extract_place_list

    @staticmethod
    @caller("flickr.places.placesForUser")
    def placesForUser(**args):
        return args,_extract_place_list
        
    @staticmethod
    def tagsForPlace(**args):
        """ method: flickr.places.tagsForPlace
            Return a list of the top 100 unique tags for a Flickr Places or Where on Earth (WOE) ID
        
        Authentication:

            This method does not require authentication.
        
        Arguments:
            woe_id (Optional)
                A Where on Earth identifier to use to filter photo clusters.

                (While optional, you must pass either a valid Places ID or a
                 WOE ID.)
            place_id (Optional)
                A Flickr Places identifier to use to filter photo clusters.

                (While optional, you must pass either a valid Places ID or a 
                WOE ID.)
            min_upload_date (Optional)
                Minimum upload date. Photos with an upload date greater than 
                or equal to this value will be returned. The date should be 
                in the form of a unix timestamp.
            max_upload_date (Optional)
                Maximum upload date. Photos with an upload date less than 
                or equal to this value will be returned. The date should be 
                in the form of a unix timestamp.
            min_taken_date (Optional)
                Minimum taken date. Photos with an taken date greater than 
                or equal to this value will be returned. The date should be 
                in the form of a mysql datetime.
            max_taken_date (Optional)
                Maximum taken date. Photos with an taken date less than or 
                equal to this value will be returned. The date should be in 
                the form of a mysql datetime. 
            
        """
        if "place" in args : args["place_id"] = args.pop("place").id
        r = method_call.call_api(method = "flickr.places.tagsForPlace",**args)
        return [Place.Tag(**t) for t in r["tags"]["tag"]]
        
    def tags(self,**args):
        """ method: flickr.places.tagsForPlace
            Return a list of the top 100 unique tags for a Flickr Places
        
        Authentication:

            This method does not require authentication.
        
        Arguments:
            min_upload_date (Optional)
                Minimum upload date. Photos with an upload date greater than 
                or equal to this value will be returned. The date should be 
                in the form of a unix timestamp.
            max_upload_date (Optional)
                Maximum upload date. Photos with an upload date less than 
                or equal to this value will be returned. The date should be 
                in the form of a unix timestamp.
            min_taken_date (Optional)
                Minimum taken date. Photos with an taken date greater than 
                or equal to this value will be returned. The date should be 
                in the form of a mysql datetime.
            max_taken_date (Optional)
                Maximum taken date. Photos with an taken date less than or 
                equal to this value will be returned. The date should be in 
                the form of a mysql datetime. 
            
        """
        r = method_call.call_api(method = "flickr.places.tagsForPlace",place_id = self.id,**args)
        return [Place.Tag(**t) for t in r["tags"]["tag"]]
        

class prefs:
    @staticmethod
    def getContentType():
        """ method: flickr.prefs.getContentType
            Returns the default content type preference for the user.
        
        Authentication:

            This method requires authentication with 'read' permission.
        """
        r = method_call.call_api(method = "flickr.prefs.getContentType",auth_handler = self.getToken())
        return r["person"]["content_type"]
    
    @staticmethod
    def getContentType():
        """ method: flickr.prefs.getGeoPerms
            Returns the default privacy level for geographic information 
            attached to the user's photos and whether or not the user has 
            chosen to use geo-related EXIF information to automatically geotag 
            their photos. Possible values, for viewing geotagged photos, are:

                0 : No default set
                1 : Public
                2 : Contacts only
                3 : Friends and Family only
                4 : Friends only
                5 : Family only
                6 : Private

            Users can edit this preference at http://www.flickr.com/account/geo/privacy/.

            Possible values for whether or not geo-related EXIF information will 
            be used to geotag a photo are:

                0: Geo-related EXIF information will be ignored
                1: Geo-related EXIF information will be used to try and 
                   geotag photos on upload

            Users can edit this preference at http://www.flickr.com/account/geo/exif/?from=privacy
        
        Authentication:

            This method requires authentication with 'read' permission.
        
        
        """
        r = method_call.call_api(method = "flickr.prefs.getGeoPerms",auth_handler = self.getToken())
        p = r["person"]
        p.pop("nsid")
        return p
    
    @staticmethod
    def getHidden():
        """ method: flickr.prefs.getHidden
            Returns the default hidden preference for the user.
        
        Authentication:

            This method requires authentication with 'read' permission.
        
        """
        r = method_call.call_api(method = "flickr.prefs.getHidden",auth_handler = self.getToken())
        return bool(r["person"]["hidden"])
         
    @staticmethod
    def getPrivacy():
        """ method: flickr.prefs.getPrivacy
            Returns the default privacy level preference for the user. Possible values are:

                1 : Public
                2 : Friends only
                3 : Family only
                4 : Friends and Family
                5 : Private

        Authentication:

            This method requires authentication with 'read' permission.
        
        """
        r = method_call.call_api(method = "flickr.prefs.getPrivacy",auth_handler = self.getToken())
        return bool(r["person"]["privacy"])
    
    @staticmethod
    def getSafetyLevel():
        """ method: flickr.prefs.getSafetyLevel
            Returns the default safety level preference for the user.
        
        Authentication:

            This method requires authentication with 'read' permission.
        """
        r = method_call.call_api(method = "flickr.prefs.getSafetyLevel",auth_handler = self.getToken())
        return bool(r["person"]["safety_level"])

class Reflection:
    @staticmethod
    def getMethodInfo(method_name):
        """ method: flickr.reflection.getMethodInfo

            Returns information for a given flickr API method.
        
        Authentication:

            This method does not require authentication.
        
        Arguments:
            method_name (Required)
                The name of the method to fetch information for. 
        
        """
        r = method_call.call_api(method = "flickr.reflection.getMethodInfo",method_name = method_name)
        return r["method"]
    
    @staticmethod
    def getMethods():
        """ method: flickr.reflection.getMethods

            Returns a list of available flickr API methods.
        
        Authentication:

            This method does not require authentication.
        
        """
        r = method_call.call_api(method = "flickr.reflection.getMethods")
        return r["methods"]["method"]

class stats:
    class Domain(FlickrObject):
        __display__ = ["name"]

    class Referrer(FlickrObject):
        __display__ = ["url","views"]
        __converters__ = [
            dict_converter(["views"],int),
        ]
    
    @staticmethod
    def getCollectionDomains(**args):
        """ method: flickr.stats.getCollectionDomains
            Get a list of referring domains for a collection
        
        Authentication:

            This method requires authentication with 'read' permission.
        
        Arguments:
            date (Required)
                Stats will be returned for this date. This should be in either be in YYYY-MM-DD or unix timestamp format. A day according to Flickr Stats starts at midnight GMT for all users, and timestamps will automatically be rounded down to the start of the day.
            collection_id (Optional)
                The id of the collection to get stats for. If not provided, stats for all collections will be returned.
            per_page (Optional)
                Number of domains to return per page. If this argument is omitted, it defaults to 25. The maximum allowed value is 100.
            page (Optional)
                The page of results to return. If this argument is omitted, it defaults to 1. 
        
        """
        if "collection" in args : args["collection_id"] = args.pop("collection").id
        r = method_call.call_api(method = "flickr.stats.getCollectionDomains", auth_handler = self.getToken(),**args)
        info = r["domains"]
        domains = [ stats.Domain(**d) for d in info.pop("domain")]
        return FlickrList(domains,Info(**info))
    
    @staticmethod
    def getCollectionReferrers(**args):
        """ method: flickr.stats.getCollectionReferrers

            Get a list of referrers from a given domain to a collection
        
        Authentication:

            This method requires authentication with 'read' permission.
        
        Arguments:
            date (Required)
                Stats will be returned for this date. This should be in 
                either be in YYYY-MM-DD or unix timestamp format. A day 
                according to Flickr Stats starts at midnight GMT for all 
                users, and timestamps will automatically be rounded down 
                to the start of the day.
            domain (Required)
                The domain to return referrers for. This should be a hostname 
                (eg: "flickr.com") with no protocol or pathname.
            collection_id (Optional)
                The id of the collection to get stats for. If not provided, 
                stats for all collections will be returned.
            per_page (Optional)
                Number of referrers to return per page. If this argument 
                is omitted, it defaults to 25. The maximum allowed value 
                is 100.
            page (Optional)
                The page of results to return. If this argument is omitted, 
                it defaults to 1. 
        
        """
        if "collection" in args : args["collection_id"] = args.pop("collection").id
        r = method_call.call_api(method = "flickr.stats.getCollectionReferrers", auth_handler = self.getToken(),**args)
        info = r["domain"]
        referrers = [ stats.Referrer(**r) for r in info.pop("referrer")]
        return FlickrList(domains,Info(**info))
    
    @staticmethod
    def getCSVFiles():
        """ method: flickr.stats.getCSVFiles

            Returns a list of URLs for text files containing all your stats 
            data (from November 26th 2007 onwards) for the currently auth'd 
            user. Please note, these files will only be available until 
            June 1, 2010 Noon PDT. For more information please check out 
            this FAQ, or just go download your files.
        
        Authentication:

            This method requires authentication with 'read' permission.
        
        """
        r = method_call.call_api(method = "flickr.stats.getCSVFiles", auth_handler = self.getToken())
        return r["stats"]["csvfiles"]["csv"]
    
    @staticmethod
    def getPhotoDomains(**args):
        """ method: flickr.stats.getPhotoDomains
           
            Get a list of referring domains for a photo
        
        Authentication:

            This method requires authentication with 'read' permission.
        
        Arguments:
            date (Required)
                Stats will be returned for this date. This should be in 
                either be in YYYY-MM-DD or unix timestamp format. A day 
                according to Flickr Stats starts at midnight GMT for all 
                users, and timestamps will automatically be rounded down 
                to the start of the day.
            photo_id (Optional)
                The id of the photo to get stats for. If not provided, stats 
                for all photos will be returned.
            per_page (Optional)
                Number of domains to return per page. If this argument is 
                omitted, it defaults to 25. The maximum allowed value is 100.
            page (Optional)
                The page of results to return. If this argument is omitted, 
                it defaults to 1. 
        
        """
        if "photo" in args : args["photo_id"] = args.pop("photo").id
        r = method_call.call_api(method = "flickr.stats.getPhotoDomains", auth_handler = self.getToken(),**args)
        info = r["domains"]
        domains = [ stats.Domain(**d) for d in info.pop("domain")]
        return FlickrList(domains,Info(**info))

    @staticmethod
    def getPhotoReferrers(**args):
        """ method: flickr.stats.getPhotoReferrers

            Get a list of referrers from a given domain to a photo
        
        Authentication:

            This method requires authentication with 'read' permission.
        
        Arguments:
            date (Required)
                Stats will be returned for this date. This should be in 
                either be in YYYY-MM-DD or unix timestamp format. A day 
                according to Flickr Stats starts at midnight GMT for all 
                users, and timestamps will automatically be rounded down 
                to the start of the day.
            domain (Required)
                The domain to return referrers for. This should be a hostname 
                (eg: "flickr.com") with no protocol or pathname.
            photo_id (Optional)
                The id of the photo to get stats for. If not provided, stats 
                for all photos will be returned.
            per_page (Optional)
                Number of referrers to return per page. If this argument is 
                omitted, it defaults to 25. The maximum allowed value is 100.
            page (Optional)
                The page of results to return. If this argument is omitted, 
                it defaults to 1. 
        
        """
        if "photo" in args : args["photo_id"] = args.pop("photo").id
        r = method_call.call_api(method = "flickr.stats.getPhotoReferrers", auth_handler = self.getToken(),**args)
        info = r["domain"]
        referrers = [ stats.Referrer(**r) for r in info.pop("referrer")]
        return FlickrList(domains,Info(**info))

    @staticmethod
    def getPhotosetDomains(**args):
        """ method: flickr.stats.getPhotosetDomains
           
            Get a list of referring domains for a photo
        
        Authentication:

            This method requires authentication with 'read' permission.
        
        Arguments:
            date (Required)
                Stats will be returned for this date. This should be in 
                either be in YYYY-MM-DD or unix timestamp format. A day 
                according to Flickr Stats starts at midnight GMT for all 
                users, and timestamps will automatically be rounded down 
                to the start of the day.
            photoset_id (Optional)
                The id of the photoset to get stats for. If not provided, stats 
                for all sets will be returned.
            per_page (Optional)
                Number of domains to return per page. If this argument is 
                omitted, it defaults to 25. The maximum allowed value is 100.
            page (Optional)
                The page of results to return. If this argument is omitted, 
                it defaults to 1. 
        
        """
        if "photoset" in args : args["photoset_id"] = args.pop("photoset").id
        r = method_call.call_api(method = "flickr.stats.getPhotosetDomains", auth_handler = self.getToken(),**args)
        info = r["domains"]
        domains = [ stats.Domain(**d) for d in info.pop("domain")]
        return FlickrList(domains,Info(**info))

    @staticmethod
    def getPhotosetReferrers(**args):
        """ method: flickr.stats.getPhotoReferrers

            Get a list of referrers from a given domain to a photo
        
        Authentication:

            This method requires authentication with 'read' permission.
        
        Arguments:
            date (Required)
                Stats will be returned for this date. This should be in 
                either be in YYYY-MM-DD or unix timestamp format. A day 
                according to Flickr Stats starts at midnight GMT for all 
                users, and timestamps will automatically be rounded down 
                to the start of the day.
            domain (Required)
                The domain to return referrers for. This should be a hostname 
                (eg: "flickr.com") with no protocol or pathname.
            photoset_id (Optional)
                The id of the photoset to get stats for. If not provided, stats 
                for all sets will be returned.
            per_page (Optional)
                Number of referrers to return per page. If this argument is 
                omitted, it defaults to 25. The maximum allowed value is 100.
            page (Optional)
                The page of results to return. If this argument is omitted, 
                it defaults to 1. 
        
        """
        if "photoset" in args : args["photoset_id"] = args.pop("photoset").id        
        r = method_call.call_api(method = "flickr.stats.getPhotosetReferrers", auth_handler = self.getToken(),**args)
        info = r["domain"]
        referrers = [ stats.Referrer(**r) for r in info.pop("referrer")]
        return FlickrList(domains,Info(**info))

    @staticmethod
    def getPhotostreamDomains(**args):
        """ method: flickr.stats.getPhotostreamStats

            Get the number of views on a user's photostream for a given date.
        
        Authentication:

            This method requires authentication with 'read' permission.
        
        Arguments:
            date (Required)
                Stats will be returned for this date. This should be in either 
                be in YYYY-MM-DD or unix timestamp format. A day according to 
                Flickr Stats starts at midnight GMT for all users, and 
                timestamps will automatically be rounded down to the start 
                of the day.

        """
        r = method_call.call_api(method = "flickr.stats.getPhotostreamDomains", auth_handler = self.getToken(),**args)
        info = r["domains"]
        domains = [ stats.Domain(**d) for d in info.pop("domain")]
        return FlickrList(domains,Info(**info))

    @staticmethod
    def getPhotostreamReferrers(**args):
        """ method: flickr.stats.getPhotostreamReferrers
            
            Get a list of referrers from a given domain to a user's photostream
        
        Authentication:

            This method requires authentication with 'read' permission.
        
        Arguments:
            date (Required)
                Stats will be returned for this date. This should be in 
                either be in YYYY-MM-DD or unix timestamp format. A day 
                according to Flickr Stats starts at midnight GMT for all 
                users, and timestamps will automatically be rounded down 
                to the start of the day.
            domain (Required)
                The domain to return referrers for. This should be a hostname 
                (eg: "flickr.com") with no protocol or pathname.
            per_page (Optional)
                Number of referrers to return per page. If this argument 
                is omitted, it defaults to 25. The maximum allowed value 
                is 100.
            page (Optional)
                The page of results to return. If this argument is omitted, 
                it defaults to 1. 
        
        """
        r = method_call.call_api(method = "flickr.stats.getPhotostreamReferrers", auth_handler = self.getToken(),**args)
        info = r["domain"]
        referrers = [ stats.Referrer(**r) for r in info.pop("referrer")]
        return FlickrList(domains,Info(**info))
    
    @staticmethod
    def getPhotostreamStats(date):
        """ method: flickr.stats.getPhotostreamStats
            Get the number of views on a user's photostream for a given date.
        
        Authentication:

            This method requires authentication with 'read' permission.
        
        Arguments:
            date (Required)
                Stats will be returned for this date. This should be in 
                either be in YYYY-MM-DD or unix timestamp format. A day 
                according to Flickr Stats starts at midnight GMT for all 
                users, and timestamps will automatically be rounded down 
                to the start of the day. 
                    
        """
        r = method_call.call_api(method = "flickr.stats.getPhotostreamStats", auth_handler = self.getToken(),date = date)
        return int(r["stats"]["views"])

    @staticmethod
    def getPopularPhotos():
        """ method: flickr.stats.getPopularPhotos
            
            List the photos with the most views, comments or favorites
        
        Authentication:

            This method requires authentication with 'read' permission.
        
        """
        r = method_call.call_api(method = "flickr.stats.getPopularPhotos", auth_handler = self.getToken())
        info = r["photos"]
        photos = []
        for p in info.pop("photo"):
            pstat = p.pop("stats")
            photos.append((Photo(**p),pstat))
        return FlickrList(photos,Info(**info))
    
    @staticmethod
    def getTotalViews(**args):
        """ method: flickr.stats.getTotalViews

            Get the overall view counts for an account
        
        Authentication:

            This method requires authentication with 'read' permission.
        
        Arguments:
            date (Optional)
                Stats will be returned for this date. This should be in 
                either be in YYYY-MM-DD or unix timestamp format. A day 
                according to Flickr Stats starts at midnight GMT for all 
                users, and timestamps will automatically be rounded down 
                to the start of the day. If no date is provided, all time 
                view counts will be returned.
        """
        r = method_call.call_api(method = "flickr.stats.getTotalViews", auth_handler = self.getToken(),**args)
        return r["stats"]

        
class Tag(FlickrObject):
    __display__ = ["id","text"]
    class Cluster(FlickrObject):
        __display__ = ["total"]
        def getPhotos(self,**args):
            """ method: flickr.tags.getClusterPhotos
            Returns the first 24 photos for a given tag cluster
        
        Authentication:

            This method does not require authentication.
            """
            r = method_call.call_api(method = "flickr.photos.removeTag", tag = self.tag, cluster_id = self.id)
            return _extract_photo_list(r)[0]

    def remove(self):
        r = method_call.call_api(method = "flickr.photos.removeTag", tag_id = self.id)
    
    @staticmethod
    def getClusters(**args):
        """ method: flickr.tags.getClusters
            Gives you a list of tag clusters for the given tag.
        
        Authentication:

            This method does not require authentication.
        
        Arguments:
            tag (Required)
                The tag to fetch clusters for. 
        
        
        """
        r = method_call.call_api(method = "flickr.tags.getClusters", **args)
        clusters = r["clusters"]["cluster"]
        
        return [ Tag.Cluster(tag = args["tag"], tags = [Tag(text = t) for t in c["tag"]],total = c["total"] )for c in clusters ]
    
    @staticmethod
    def getHotList(**args):
        """ method: flickr.tags.getHotList
            Returns a list of hot tags for the given period.
        
        Authentication:

            This method does not require authentication.
        
        Arguments:
            period (Optional)
                The period for which to fetch hot tags. Valid values are 
                day and week (defaults to day).
            count (Optional)
                The number of tags to return. Defaults to 20. Maximum allowed 
                value is 200. 
        
        """
        r = method_call.call_api(method = "flickr.tags.getHotList", **args)
        return [Tag(**t) for t in r["hottags"]["tag"]]

    @staticmethod
    def getListUser(**args):
        """ method:flickr.tags.getListUser

        Get the tag list for a given user (or the currently logged in user).
    
    Authentication:

        This method does not require authentication.
    
    Arguments:
        user_id (Optional)
            The NSID of the user to fetch the tag list for. If this argument 
            is not specified, the currently logged in user (if any) is assumed.  
        """
        if "user" in args: args["user_id"] = args.pop("user").id
        r = method_call.call_api(method = "flickr.tags.getListUser", **args)
        return [Tag(**t) for t in r["who"]["tags"]["tag"]]
        
    @staticmethod
    def getListUserPopular(**args):
        """ method: flickr.tags.getListUserPopular
            
            Get the popular tags for a given user (or the currently logged in user).
        
        Authentication:

            This method does not require authentication.
        
        Arguments:
            user_id (Optional)
                The NSID of the user to fetch the tag list for. If this argument is not specified, the currently logged in user (if any) is assumed.
            count (Optional)
                Number of popular tags to return. defaults to 10 when this argument is not present. 
        
        """
        if "user" in args: args["user_id"] = args.pop("user").id
        r = method_call.call_api(method = "flickr.tags.getListUserPopular", **args)
        return [Tag(**t) for t in r["who"]["tags"]["tag"]]

    @staticmethod
    def getListUserRaw(**args):
        """ method: flickr.tags.getListUserRaw
            Get the raw versions of a given tag (or all tags) for the currently logged-in user.
            
        Authentication:

            This method does not require authentication.
        
        Arguments:
            tag (Optional)
                The tag you want to retrieve all raw versions for. 
        
        """
        r = method_call.call_api(method = "flickr.tags.getListUserRaw", **args)
        tags = r["who"]["tags"]["tag"]
        return [{'clean': t["clean"],"raws": t["raw"]} for t in tags]
    
    @staticmethod
    def getRelated(tag):
        """ method: flickr.tags.getRelated
            Returns a list of tags 'related' to the given tag, based on clustered usage analysis.
        
        Authentication:

            This method does not require authentication.
        
        Arguments:
            tag (Required)
                The tag to fetch related tags for. 
        """
        r = method_call.call_api(method = "flickr.tags.getRelated", tag = tag)
        return r["tags"]["tag"]


        
class test(object):
    @staticmethod
    def echo(**args):
        """ method: flickr.test.echo

            A testing method which echo's all parameters back in the response.
        
        Authentication:

            This method does not require authentication.        
        """
        r = method_call.call_api(method = "flickr.test.echo",**args)
        return r
        
    
    @staticmethod
    def login(token = None):
        """ method: flickr.test.login

            A testing method which checks if the caller is logged in then 
            returns their username.
        
        Authentication:

            This method requires authentication with 'read' permission.
        """
        if token is None : token = AUTH_HANDLER
        r = method_call.call_api(method = "flickr.test.login",auth_handler = token)
        user = Person(**r["user"])
        user.setToken(token)

    @staticmethod
    def null():
        """ method: flickr.test.null
            Null test
        
        Authentication:

            This method requires authentication with 'read' permission.
        """
        r = method_call.call_api(method = "flickr.test.null",auth_handler = AUTH_HANDLER)
        
class UploadTicket(FlickrObject):
    pass

def _extract_activity_list(r):
    items = _check_list(r["items"]["item"])
    activities = []
    for item in items :
        activity = item.pop("activity")
        item_type = item.pop(["type"])
        if item_type == "photo" :
            item = Photo(**item)
        elif item_type == "photoset" :
            item = Photoset(**item)
        events_ = []
        events = _check_list(activity["event"])
        for e in events :
            user = e["user"]
            username = e.pop("username")
            e["user"] = Person(id = user, username = username)
            e_type = e.pop("type")
            if e_type == "comment" :
                if item_type == "photo" :
                    events_.append(Photo.Comment(photo = item, **e))
                elif item_type == "photoset" :
                    events_.append(Photoset.Comment(photoset = item, **e))
            elif e_type == 'note' :
                events_.append(Note(photo = item,**e))
        activities.append( Activity(item = item, events = events) )
    return activities


def _format_id(name,args):
    try: args[name+"_id"] = args.pop(name).id
    except KeyError : pass

def _format_extras(args):
    try :
        extras = args["extras"]
        if isinstance(extras,list):
            args["extras"] = ",".join(extras)
    except KeyError : pass
    return args

def _extract_place_list(r):
    info = r["places"]
    return FlickrList([Place(id = place.pop("place_id"), **place) for place in info.pop("place")],Info(**info))

def _extract_photo_list(r,token = None):
    photos = []
    infos = r["photos"]
    pp = infos.pop("photo")
    if not isinstance(pp,list):
        pp = [pp]
    for p in pp :
        owner = Person(id = p["owner"],token = token)
        p["owner"] = owner
        p["token"] = token
        photos.append( Photo(**p))
    return FlickrList(photos,Info(**infos))

def _check_list(obj):
    if isinstance(obj,list):
        return obj
    else :
        return [obj]

class Walker(object):
    """
        Object to walk along paginated results. This allows
        to loop on all the results corresponding to a query
        regardless pagination.
        
        w = Walker(method,*args,**kwargs)
        
        arguments:
        - method: a method returning a FlickrList object.
        - *args: positional arguments to call 'method' with
        - **kwargs: named arguments to call 'method' with
        
        ex:
        >>> w = Walker(Photo.search,tags = "animals")
        >>> for photo in w :
        >>>     print photo.title

    """
    def __init__(self,method,*args,**kwargs):
        """
            Constructor
            
        arguments:
        - method: a method returning a FlickrList object.
        - *args: positional arguments to call 'method' with
        - **kwargs: named arguments to call 'method' with

        """
        self.method = method
        self.args = args
        self.kwargs = kwargs
        
        self._curr_list = self.method(*self.args,**self.kwargs)
        self._info = self._curr_list.info
        self._curr_index = 0
        self._page = 1
    
    def __len__(self):
        return self._info.total
        
    def __iter__(self):
        return self
    
    def next(self):
        if self._curr_index == len(self._curr_list) :
            if self._page < self._info.pages :
                self._page += 1
                self.kwargs["page"] = self._page
                
                self._curr_list = self.method(*self.args,**self.kwargs)
                self._info = self._curr_list.info
                self._curr_index = 0
                
            else :
                raise StopIteration()

        curr = self._curr_list[self._curr_index]
        self._curr_index += 1
        return curr
