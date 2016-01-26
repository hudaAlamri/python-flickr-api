As complete as possible implementation of Flickr API.

The project provides an almost exhaustive access to the Flickr API, through an **object oriented** Python interface.

The project is still at an early stage and requires a lot of testing.
Any help including bug reports is appreciated.

Main features :
  * Object Oriented implementation
  * (Almost) comprehensive implementation
  * uses OAuth for authentication
  * context sensitive objects (depending on the query context, objects may exhibit different attributes)
  * An interface for direct seamless calls to the Flickr API.
  * A (django-complient) caching mechanism

requires:
  * python 2.6+
  * python-oauth (or the python module from http://code.google.com/p/oauth/)


**The development activity has moved to GitHub**. You can download the development version from GitHub with:
```
git clone git://github.com/alexis-mignon/python-flickr-api.git
```

You should post issues or comments on GitHub also:
http://github.com/alexis-mignon/python-flickr-api/

The svn repository at least for a while will be kept up-to-date, so that if you want to go on using svn you can do it from:
```
svn checkout http://python-flickr-api.googlecode.com/svn/trunk/ python-flickr-api
```

I have been recently working on a new version of the api using different programming paradigms. It uses meta classes and decorators to implement the api calls and generate the documentation dynamically from Flickr documentation. The result is a much more compact code which stresses the ways the object API is bound to Flickr API. Since a lot of code has been modified it can be unstable and some minor compatibility issues might have appear.

The current 'stable' (should be frozen) version is available on the downloads page with under the name python-flickr-api\_0.1.zip


If you prefer using the previous version of the project please download it from :
```
svn checkout http://python-flickr-api.googlecode.com/svn/branches/init/ python-flickr-api
```
or download the archive python-flickr-api\_xxxx.zip on the download page.
If requested this branch can be maintained for little while, since the new version becomes stable.