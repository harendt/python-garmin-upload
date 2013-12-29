#!/usr/bin/python
#
# Copyright (c) 2010, Chmouel Boudjnah <chmouel@chmouel.com>
# Copyright (c) 2012, David Lotton <yellow56@gmail.com>
# Copyright (c) 2013, Bastian Harendt <b.harendt@gmail.com>
# 
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
# 1. Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
# 
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
# 
# 3. The names of the copyright holders and contributors may not be used to
# endorse or promote products derived from this software without specific prior
# written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""Upload activities to Garmin Connect."""

import urllib2
import urllib
import MultipartPostHandler
try:
	import simplejson
except ImportError:
	import json as simplejson
import json
import os.path
import datetime
import re
import pytz

# just for testing
from pprint import pprint

BaseUrl = 'https://connect.garmin.com/'
UserService = BaseUrl + 'proxy/user-service-1.0/json/'
UploadService = BaseUrl + 'proxy/upload-service-1.1/json/'
ActivitySearchService = BaseUrl + 'proxy/activity-search-service-1.2/json/'
ActivityService = BaseUrl + 'proxy/activity-service-1.3/json/'

class Activity:

	def __init__(self, activityId = None, activityData = None):
		# retrieve activity data from activity id
		if activityData is None:
			output = urllib2.urlopen(ActivitySearchService + 'activities?activityId=%d&limit=1&start=0' % activityId)
			output = json.loads(output.read())
			if len(output['results']['activities']) == 0:
				raise Exception('Could not retrieve data for activity id %d' % activityId)
			activityData = output['results']['activities'][0]['activity']

		# general information
		self.activityId   = int(activityData['activityId'])
		self.activityType = activityData['activityType']['key']
		self.name         = activityData['activityName']

		# begin and end time
		self.beginTime = self.extractTime(activityData, 'begin')
		self.endTime   = self.extractTime(activityData, 'end'  )

		# begin and end coordinates (latitude and longitude)
		self.beginCoordinates = self.extractCoordinates(activityData, 'begin')
		self.endCoordinates   = self.extractCoordinates(activityData, 'end')

		# distance in kilometers and duration in seconds
		self.distance = float(activityData['activitySummary']['SumDistance']['value'])
		self.duration = float(activityData['activitySummary']['SumDuration']['value'])


	@classmethod
	def getFromData(cls, activityData):
		return cls(activityData = activityData)


	@classmethod
	def getFromId(cls, activityId):
		return cls(activityId = activityId)

	def __str__(self):
		return '%s\n\tId = %d\n\tType = %s\n\tTime = %s\n\tDistance = %.2f km\n\tDuration: %.0f min\n\tCoordinates = (%5.5f, %5.5f)' % (
				self.name,
				self.activityId,
				self.activityType,
				self.beginTime,
				self.distance,
				self.duration / 60,
				self.beginCoordinates[0],
				self.beginCoordinates[1])


	@staticmethod
	def extractTime(data, prefix):
		prefix = prefix.capitalize()
		if prefix not in ['Begin', 'End']:
			raise Exception('invalid prefix specified')
		timestamp = data['activitySummary'][prefix + 'Timestamp']
		items = re.match(
				'(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2}).(\d{3})Z',
				timestamp['value'])
		time = datetime.datetime(
				year        = int(items.group(1)),
				month       = int(items.group(2)),
				day         = int(items.group(3)),
				hour        = int(items.group(4)),
				minute      = int(items.group(5)),
				second      = int(items.group(6)),
				microsecond = int(items.group(7))*1000,
				tzinfo      = pytz.utc)
		time = time.astimezone(pytz.timezone(timestamp['uom']))
		return time


	@staticmethod
	def extractCoordinates(data, prefix):
		prefix = prefix.capitalize()
		if prefix not in ['Begin', 'End']:
			raise Exception('invalid prefix specified')
		latitude  = float(data['activitySummary'][prefix+'Latitude']['value'])
		longitude = float(data['activitySummary'][prefix+'Longitude']['value'])
		return (latitude, longitude)


	def update(self):
		self.__init__(activityId = self.activityId)


	def rename(self, name):
		"""Rename an activity.

		@ivar name: New activity name
		@type name: str
		"""
		params = {
			'value' : name
		}
		params = urllib.urlencode(params)
		output = urllib2.urlopen(ActivityService + 'name/%d' % self.activityId, params)
		output = json.loads(output.read())
		if output['display']['value'] != name:
			raise Exception('Naming activity has failed')
		self.update()


	def getUrl(self):
		"""Get the activity's URL."""
		return 'https://connect.garmin.com/activity/%d' % self.activityId



class UploadGarmin:
	"""Interface to upload activities to Garmin Connect."""

	userId = -1
	userName = ''

	def __init__(self):
		# see: http://docs.python.org/2/library/urllib2.html#urllib2.build_opener
		self.opener = urllib2.build_opener(
				urllib2.HTTPCookieProcessor(),
				MultipartPostHandler.MultipartPostHandler)
		# see: http://docs.python.org/2/library/urllib2.html#urllib2.install_opener
		urllib2.install_opener(self.opener)

	def signIn(self, user, password):
		"""Sign in to Garmin Connect.

		This is required to upload activities.

		@ivar username: Garmin User Name
		@type username: str
		@ivar password: Garmin Password
		@type password: str
		"""
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

		try:
			# open the sign in page once (required for a successful login)
			self.opener.open(BaseUrl + 'signin').read()

			# send login parameters
			self.opener.open(BaseUrl + 'signin', params)

			# read the current username (if login succeeds this returns a JSON with
			# the username -- something like {"username":"fred"}; otherwise this
			# returns {"username":""})
			output = self.opener.open(BaseUrl + 'user/username')
			output = json.loads(output.read())

			# get account information (username and user ID)
			if output['username'] != '':
				output = self.opener.open(UserService + 'account')
				output = json.loads(output.read())
				self.userId = int(output['account']['userId'])
				self.userName = output['account']['username']
			else:
				self.userId = -1
				self.userName = ''

		except Exception as e:
			print 'Sign in failed unexpectedly: %s' % str(e)
			return False

		if self.userId > 0:
			print 'Signed in as user "%s" (ID: %d)' % (self.userName, self.userId)
			return True
		else:
			print 'Sign in as user "%s" failed' % user
			return False


	def uploadFile(self, filename):
		"""Upload a file to Garmin Connect.

		You need to be signed in already.

		@ivar uploadFile: The TCX, GPX, or FIT file name to upload
		@type uploadFile: str
		"""
		# Split the filename into root and extension
		# see: http://docs.python.org/2/library/os.path.html#os.path.splitext
		fileExtension = os.path.splitext(filename)[1].lower()

		# Valid file extensions are .tcx, .fit, and .gpx
		if fileExtension not in ['.tcx', '.fit', '.gpx']:
			raise Exception('Invalid file extension "%s"' % fileExtension)

		if fileExtension == '.fit':
			openMode = 'rb'
		else:
			openMode = 'r'

		params = {
			'data' : open(filename, openMode)
		}

		print 'Uploading file "%s"' % filename
		try:
			output = self.opener.open(UploadService + 'upload/' + fileExtension, params)
			output = simplejson.loads(output.read())
			successes = output['detailedImportResult']['successes']
			failures  = output['detailedImportResult']['failures']
		except Exception as e:
			print 'Upload failed unexpectedly: %s' % str(e)
			return False, -1

		if len(successes) > 0 and 'internalId' in successes[0]:
			activityId = int(successes[0]['internalId'])
			print 'Upload succeeded (activity ID: %d)' % activityId
			return True, activityId

		if len(failures) > 0 and 'internalId' in failures[0]:
			activityId = int(failures[0]['internalId'])
			# get failure code (code #202 stands for 'duplicate activity')
			try:
				errorCode = int(failures[0]['messages'][0]['code'])
			except Exception:
				errorCode = -1
			if errorCode == 202:
				print 'Activity already exists (activity ID: %d)' % activityId
				return False, activityId

		print 'Upload failed unexpectedly'
		return False, -1

	def getActivities(self):
		"""Retrieve a list of activities."""
		activities = []
		limit = 50
		start = 0
		while True:
			output = self.opener.open(ActivitySearchService + 'activities?limit=%d&start=%d' % (limit, start))
			output = json.loads(output.read())
			if len(output['results']['activities']) > 0:
				for item in output['results']['activities']:
#					pprint(item['activity'])
					activities.append(Activity.getFromData(item['activity']))
			else:
				break
			start += limit
		return activities

	def printActivities(self):
		activities = self.getActivities()
		for (index, activity) in enumerate(activities):
			print '%d: %s' % (index, activity)
