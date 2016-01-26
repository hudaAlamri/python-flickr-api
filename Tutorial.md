# Introduction #

This document tries to show some basic usage of flickr\_api.

# Flickr keys #

Any application using the Flickr API needs to have a api key and a secret key. Both are provided by Flickr. Please refer to the Flickr instructions to learn how to get thoses keys.

To be able to use these keys in your application you have two ways:
  1. Set the key information using the 'set\_keys' function. so any application using this API should start with something like:
```
import flickr_api
flickr_api.set_keys(api_key = 'my_api_key', api_secret = 'my_secret')
```
  1. provide a flickr\_keys.py setting module with the keys information. It should look like:
```
API_KEY =  'my_api_key'
API_SECRET = 'my_secret'
```
This module should be located in your flickr\_api directory or available from your PYTHON\_PATH.

# Authentication #

If your application needs to modify data or to access non public material, it will require an authentication token. The AuthHandler object is designed to deal with the authentication process.

To get an authentication token, the AuthHandler will ask an authorisation request. It will then provide an url at which the user should be redirected so he can grant the required permissions. At the end of the authorisation process a verifier code will be provided. This code must be given to the AuthHandler object which will then be able to get the authentication token.

Here is an example of how to get this authentication token.

```
>>> import flickr_api
>>> a = flickr_api.auth.AuthHandler() #creates the AuthHandler object
>>> perms = "read" # set the required permissions
>>> url = a.get_authorization_url(perms)
>>> print url
```

At this time you should copy and paste the printed url in your favorite web browser. Login to Flickr if it is needed and accept the requested permissions.
You will be redirected to an xml page in which there is a "oauth\_verifier" tag. The content of this tag is the verifier that needs to be given to the AuthHandler.

Note that the url you you are redirected to after you have seccessfully granted the permissions is called the "callback" url. The xml page you have seen corresponds to the default callback url. Within a web application you are supposed to redirect the user to Flickr for the authorisation process. Once it is completed you would like the user to be redirected to a url on your own website which will read automatically the verifier code in the query part of the url. This can be done through the "callback" argument of the AuthHandler constructor. In this case you will want to replace the second line above by something like:

```
a = flickr_api.auth.AuthHandler(callback = "http://www.mysite.com/get_verifier/")
```

Let's come back to our example. In the xml page, copy the content of the "oauth\_verifier" tag and give it to the AuthHandler object.

```
>>> a.set_verifier("the verifier code")
>>> flickr_api.set_auth_handler(a) # set the AuthHandler for the session
```

That's it! You are ready to play with your account. The authorisation process is supposed to be done only once so you might want to save the Authentication token:
```
>>> a.save(filename)
```
Next time you want to access your account you just need to reload it:
```
>>> a = flickr_api.auth.AuthHandler.load(filename)
>>> flickr_api.set_auth_handler(a)
```
Actually there is a shortcut for that:
```
>>> flickr_api.set_auth_handler(filename)
```

# Direct API methods calls #

You can access the flickr api in two different ways the first one directly calls the api methods with a syntax close to the one that you will find on the api documentation on Flickr's site.

The answers are xml strings or JSON strings and you will have to parse them yourself. This method is recommended for experimented users only. For other users please refer to the Object Oriented api.

Here is an example of method call:
```
>>> from flickr_api.api import flickr
>>> print flickr.reflection.getMethodInfo(method_name = "flickr.photos.getInfo")
```
```
<?xml version="1.0" encoding="utf-8" ?>
<rsp stat="ok">
<method name="flickr.photos.getInfo" needslogin="0" needssigning="0" requiredperms="0">
	<description>Get information about a photo. The calling user must have permission to view the photo.</description>
	<response>...</response>
	<explanation>...</explanation>
</method>
<arguments>
	<argument name="api_key" optional="0">Your API application key. &lt;a href=&quot;/services/api/misc.api_keys.html&quot;&gt;See here&lt;/a&gt; for more details.</argument>
        ...
</arguments>
<errors>
	<error code="1" message="Photo not found.">The photo id was either invalid or was for a photo not viewable by the calling user.</error>
	...
</errors>
</rsp>
```

# Object Oriented interface usage #
## Retrieving a user ##

To have direct access to user you have 3 methods
  1. by username
```
>>> user = flickr_api.Person.findByUsername(username)
```
  1. by email
```
>>> user = flickr_api.Person.findByEmail(email)
```
  1. If an authentication handlier is set, you can retrieve the authenticated user with  :
```
>>> user = flickr_api.test.login()
```

## Managing Photos ##

  * Get photos from a user
```
>>> photos = user.getPhotos()       # if authenticated
>>> photos = user.getPublicPhotos() # otherwise
```
Some information about the response from the server, e.g. pagination information, are available in the `info` attribute of the `photos` list:
```
>>> print photos.info.pages # the number of available pages of results
>>> print photos.info.page  # the current page number
>>> print photos.info.total # total number of photos
```

  * Download a photo
```
>>> p.save(filename, size_label = 'Medium 640') # downloading the photo file
```
  * Upload a photo
```
>>> flickr_api.upload(photo_file = "path_to_the_photo_file", title = "My title")
```
  * Add/Delete a comment
```
>>> comment = photo.addComment(comment_text = "A comment") # adding a comment
>>> comment.delete() # deleting the comment
```
  * Retrieve the comments
```
>>> comments = photo.getComments()
>>> for comment in comments : print comment.text
```

## Managing Photosets (aka Albums) ##
  * Get the photosets of a user
```
>>> photosets = user.getPhotosets()
```
  * Create a photoset
```
>>> photoset = flickr_api.Photoset.create(title = "The title of the photoset", primary_photo = cover_photo)
```
  * Delete a photoset
```
>>> photoset.delete()
```
  * Get the photos of a photoset
```
>>> photos = photoset.getPhotos()
```
  * Add a photo to a set
```
>>> photoset.addPhoto(photo = a_photo)
```
  * Add a comment to a photoset
```
>>> photoset.addComment(comment_text = "the text of the comment...")
```

## Cache ##

It is possible to cache frequent request to avoid repeated access to Flickr site:
```
import flickr_api
flickr_api.enable_cache()
```

You can also provide customized cache object:
```
import flickr_api
from flickr_api.cache import SimpleCache
flickr_api.enable_cache(SimpleCache(timeout = 300,max_entries = 10)
```

The code for caching comes from the Stuvel's python api. It should then be compliant with Django caching system.

```
import flickr_api
from django.core.cache import cache
flickr_api.enable_cache(cache)
```

To disable the caching system:
```
flickr_api.disable_cache()
```