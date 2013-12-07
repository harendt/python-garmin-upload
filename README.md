Python Garmin Upload
====================

This simple python library allows you to upload *fit* and *tcx* files to Garmin Connect


License
-------

See the headers of the respective files for details about licensing.

* UploadGarmin.py: BSD license
* MultipartPostHandler.py: LGPL


Requirements
------------

pytz


Example
-------

```python
# Make sure you have MultipartPostHandler.py in your path as well
import UploadGarmin

# Create object
g = UploadGarmin.UploadGarmin()

# Sign in
g.signIn("username", "password")

# Upload file
wId = g.upload_ctx('/tmp/a.ctx')

# Name last workout
g.name_workout(wId, "TestWorkout")
```
