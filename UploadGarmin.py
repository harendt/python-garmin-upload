"""
Upload Garmin

Handle the operation to upload to the Garmin Connect Website.

Copyright (c) 2010, Chmouel Boudjnah <chmouel@chmouel.com>
Copyright (c) 2012, David Lotton <yellow56@gmail.com>
Copyright (c) 2013, Bastian Harendt <b.harendt@gmail.com>

All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
this list of conditions and the following disclaimer in the documentation
and/or other materials provided with the distribution.

3. The names of the copyright holders and contributors may not be used to
endorse or promote products derived from this software without specific prior
written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import urllib2
import urllib
import MultipartPostHandler
try:
	import simplejson
except ImportError:
	import json as simplejson
import json
import os.path

BaseUrl = 'https://connect.garmin.com/'
UserService = BaseUrl + 'proxy/user-service-1.0/json/'

"""
Upload Garmin

Handle operation to open to Garmin
"""
class UploadGarmin:

	userId = -1
	userName = ""

	def __init__(self):
		# see: http://docs.python.org/2/library/urllib2.html#urllib2.build_opener
		self.opener = urllib2.build_opener(
				urllib2.HTTPCookieProcessor(),
				MultipartPostHandler.MultipartPostHandler)
		# see: http://docs.python.org/2/library/urllib2.html#urllib2.install_opener
		urllib2.install_opener(self.opener)

	"""
	Login to garmin

	@ivar username: Garmin User Name
	@type username: str
	@ivar password: Garmin Password
	@type password: str
	"""
	def signIn(self, user, password):
		try:
			# it seems that all of the following parameters are required for a
			# successful login
			params = {
					'login' : 'login',
					'login:loginUsernameField' : user,
					'login:password' : password,
					'login:signInButton' : 'Sign In',
					'javax.faces.ViewState' : 'j_id1'
			}
			params = urllib.urlencode(params)

			# open the sign in page once
			self.opener.open(BaseUrl + 'signin').read()

			# send login parameters
			self.opener.open(BaseUrl + 'signin', params)

			# read the current username (if login succeeds this returns a JSON with
			# the username -- something like {"username":"fred"}; otherwise this
			# returns {"username":""})
			output = self.opener.open(BaseUrl + 'user/username')
			output = json.loads(output.read())

			if output['username'] != '':
				output = self.opener.open(UserService + 'account')
				output = json.loads(output.read())
				self.userId = int(output['account']['userId'])
				self.userName = output['account']['username']
				print 'Signed in as user "%s" (ID: %d)' % (self.userName, self.userId)
				return True
			else:
				print 'Sign in as user "%s" failed' % user
				return False

		except BaseException as e:
			print 'Sign in failed unexpectedly: %s' % str(e)
			return False

	"""
	Upload a File

	You need to be logged already

	@ivar uploadFile: The TCX, GPX, or FIT file name to upload
	@type uploadFile: str
	"""
	def upload_file(self, uploadFile):

		extension = os.path.splitext(uploadFile)[1].lower()

		# Valid File extensions are .tcx, .fit, and .gpx
		if extension not in ['.tcx', '.fit', '.gpx']:
			raise Exception("Invalid File Extension")

		if extension == '.fit':
			mode = 'rb'
		else:
			mode = 'r'

		params = {
			"responseContentType" : "text%2Fhtml",
			"data" : open(uploadFile, mode)
		}

		uploadUri='http://connect.garmin.com/proxy/upload-service-1.1/json/upload/'+extension
		# debug:
		#print '\tURI: ' + uploadUri

		output = self.opener.open(uploadUri, params)
		if output.code != 200:
			raise Exception("Error while uploading")
		json = output.read()
		output.close()

		# debug: Helpful info - uncomment the following print statements
		#print '--------------debug-------------'
		#print uploadFile
		#print json
		#print '--------------debug-------------'
		if len(simplejson.loads(json)["detailedImportResult"]["successes"])==0:
			if len(simplejson.loads(json)["detailedImportResult"]["failures"]) != 0:
				# File already exists on Garmin Connect
				return ['EXISTS', simplejson.loads(json)["detailedImportResult"]["failures"][0]["internalId"]]
			else:
				# Don't know what failed
				return ['FAIL', 'Upload Fail']
		else:
			# Upload was successsful
			return ['SUCCESS', simplejson.loads(json)["detailedImportResult"]["successes"][0]["internalId"]]

	def upload_tcx(self, tcx_file):
		"""
		Upload a TCX File

		You need to be logged already

		@ivar tcx_file: The TCX file name to upload
		@type tcx_file: str
		"""
		params = {
			"responseContentType" : "text%2Fhtml",
			"data" : open(tcx_file)
		}

		#dlotton - added '.tcx' to the end of the URI below
		output = self.opener.open('http://connect.garmin.com/proxy/upload-service-1.1/json/upload/.tcx', params)
		if output.code != 200:
			raise Exception("Error while uploading")
		json = output.read()
		output.close()

		return simplejson.loads(json)["detailedImportResult"]["successes"][0]["internalId"]

	"""
	Name a Workout

	Note: You need to be logged already

	@ivar workout_id: Workout ID to rename
	@type workout_id: int
	@ivar workout_name: New workout name
	@type workout_name: str
	"""
	def name_workout(self, workout_id, workout_name):
		params = dict(value=workout_name)
		params = urllib.urlencode(params)
		output = self.opener.open('http://connect.garmin.com/proxy/activity-service-1.0/json/name/%d' % (workout_id), params)
		json = output.read()
		output.close()

		if simplejson.loads(json)["display"]["value"] != workout_name:
			raise Exception("Naming workout has failed")

	"""
	Get the Workout URL

	@ivar workout_id: Workout ID
	@type workout_id: int
	"""
	def workout_url(self, workout_id):
		return "http://connect.garmin.com/activity/" % (int(workout_id))

if __name__ == '__main__':
	g = UploadGarmin()
	g.login("username", "password")
	wId = g.upload_tcx('/tmp/a.tcx')
	wInfo = g.upload_file('/tmp/a.tcx')
	g.name_workout(wId, "TestWorkout")
