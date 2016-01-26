# Introduction #
From my point of the the original code of the Object API was extremely redundant and difficult to browse because of its large size. A big part of its size was due to the documentation which I had manually copied from the Flickr API documentation.

In the new version of the Object API, most of the repetitive code has been removed and replace either by some helper function or more interestingly by an extensive use
of decorators and meta programming.

This gives a more compact code and I hope easier to maintain.


# 'caller' and 'static\_caller' decorators #
Since an object methods is an abstraction of the call to a Flickr API method, I wanted the code to reflect this relation. Now an Object method bound to a Flickr API method is explicitly indicated as such through the use of the 'caller' decorator.

For instance this is the code of the 'Photo.search' method:
```
    @static_caller("flickr.photos.search")
    def search(**args):        
        args = _format_id("user",args)
        args = _format_extras(args)
        return args,_extract_photo_list
```

Since this is a static method we use the 'static\_caller' decorator which take as argument the Flickr API method it uses internally. The body of the function does two things:
  1. It pre-format the arguments that we be use for the api call
  1. It returns a function that will process the result from Flickr API and reformat it into Objects.

Written this way the code makes explicit the way the binding is done:
  1. Which api method is called ?
  1. Do the arguments need to be pre-formated ?
  1. How to interpret the respsonse from Flickr servers ?

Note that `static_caller` inherits from `staticmethod` so you must not add the
static method decorator.

# Where is the documentation ? #

This is a controversial point. The code is generated dynamically from the method descriptions given by Flickr through the `flickr.reflection.getMethodInfo` api method.

Since make calls to flickr servers for all methods can take time it has been done once for all and the result is saved as a dictionnary into the 'methods' module which is automatically generated using the `write_reflection` function from the `tools` module. You have two ways to have access to the documentation of a method:
  1. in the interactive console (by using either help(method) or print method.doc)
  1. or using pydoc which generates the documentation automatically, so you have a nice browsable html documentation.

# How does reflection work ? #

First the documentation for all flickr method has be downloaded using `flickr.reflection.getMethods` to get the list of Flickr API methods, and then
`flickr.reflection.methodInfo` to get the documentation of each method. The result is stored as a dictionnary in the `flickr_api.methods` module.

The reflection mechanism for the object api (available from `flickr_api.objects`) is then implemented in the `flickr_api.reflection` module and consists in two main components:
  1. The `caller` and `static_caller` decorators.
  1. The `FlickrAutoDoc` meta class.

Both components act together to add the reflection capabilities. The `caller` and `static_caller` decorators add a `flickr_method` as well as a `isstatic` attribtues to each method. This allows the user to know which Flickr method is used
to access Flickr's servers. It is also used by the meta class `FlickrAutoDoc` to dynamically add the documentation of the method.
`FlickrAutoDoc` also keep tracks of the bindings between Flickr methods and object methods so you can know which object methods are bound to a given Flickr method using the `bindings_to` function:

```
>>> from flickr_api import reflection
>>> reflection.bindings_to("flickr.people.getPhotos")
['Person.getPhotos']
```