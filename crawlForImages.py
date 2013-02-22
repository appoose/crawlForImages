# script to download content using various apis
import urllib
import sys
import time
import os
import requests

# following imports are specific to 500px
# get it from https://github.com/akirahrkw/python-500px
from fivehundredpx.client import FiveHundredPXAPI
from fivehundredpx.auth   import *
import getpass
import datetime

# for flickr
import flickrapi
import simplejson
import re

class CrawlData():
	def __init__(self,searchEngine):
		self.searchEngine = searchEngine
		self.count = 0
		if searchEngine == 'google':
			self.baseDir = 'googleImageResults'
			self.rootUrl = 'https://ajax.googleapis.com/ajax/services/search/images?v=1.0&q='
			self.apiKey = 'replace your api key here' # not needed if want < 64 images. Have not implemented the paid account version
			self.opUrlKey = 'unescapedUrl'
		elif searchEngine == 'bing':
			self.baseDir = 'bingImageResults'
			self.rootUrl = 'https://api.datamarket.azure.com/Bing/Search/v1/Image?Query='
			self.apiKey = 'replace your api key here'
			self.opUrlKey = 'MediaUrl'
		elif searchEngine == '500px':
			self.baseDir = '500pxImageResults'
			self.CONSUMER_KEY = 'your consumer key here'
			self.CONSUMER_SECRET = 'your consumer secret here'
			self.opUrlKey = 'image_url'
			# oauth details
			self.handler = OAuthHandler(self.CONSUMER_KEY,self.CONSUMER_SECRET)
			self.requestToken = self.handler.get_request_token()
			self.handler.set_request_token(self.requestToken.key,self.requestToken.secret)
			username = raw_input("Input your username: ").strip()
			password = getpass.getpass()
			self.token = self.handler.get_xauth_access_token(username,password)
			self.api = FiveHundredPXAPI(self.handler)
		elif searchEngine == 'flickr':
			self.baseDir = 'FlickrResults'
			self.api_key = 'your api key'
			self.api_secret = 'your api secert'
			self.api =flickrapi.FlickrAPI(self.api_key, self.api_secret)
			(self.token, self.frob) = self.api.get_token_part_one(perms='write')
			if not self.token:
				raw_input("Press Enter")
			self.api.get_token_part_two((self.token,self.frob))
			# self.cc_licenses = '1, 2, 3, 4, 5, 6, 7' for cc license search
			self.cc_licenses = ''

	# you have to generate the urls yourself for flickr
	def grabDataFlickr(self,dataInfo):
		for j in range(len(dataInfo)):
			currFlickrMeta = dataInfo[j]
			currUrl = 'http://farm1.staticflickr.com/{0}/{1}_{2}_z.jpg'.format(
				currFlickrMeta['server'],
				currFlickrMeta['id'],
				currFlickrMeta['secret'])
			opFileName = '{0}/Image_{1:010d}.jpg'.format(self.opDir,self.count)
			print opFileName
			urllib.urlretrieve(currUrl,opFileName)
			self.count = self.count + 1


	def grabData(self,dataInfo):
		for j in range(len(dataInfo)):
			currUrl = dataInfo[j][self.opUrlKey]
			opFileName = '{0}/Image_{1:010d}.jpg'.format(self.opDir,self.count)
			print opFileName
			urllib.urlretrieve(currUrl,opFileName)
			self.count = self.count + 1

	def doSearch(self,queryTerm,pageNumber):

		self.opDir = self.baseDir + '/' + queryTerm
		if not os.path.exists(self.opDir):
			os.makedirs(self.opDir)
	
		if self.searchEngine == 'google':
			searchUrl = self.rootUrl + urllib.quote(queryTerm) +'&start='+str(pageNumber*8)+'&userip=MyIP&rsz=8&imgtype=photo'
			try:
				response = requests.get(searchUrl).json()
				dataInfo = response['responseData']['results']
			except (IndexError,TypeError,ValueError,NameError):  
				print 'skipping'
				return 

		elif self.searchEngine == 'bing':
			searchUrl = self.rootUrl + '%27' + urllib.quote(queryTerm) + '%27&$format=json&$skip=' + str(pageNumber*10)
			try:
				response = requests.get(searchUrl, auth=(self.apiKey,self.apiKey)).json()
				dataInfo = response['d']['results']	
			except (IndexError,TypeError,ValueError,NameError):  
				print 'skipping'
				return 

		elif self.searchEngine == 'flickr':
			# documentation available at http://www.flickr.com/services/api/flickr.photos.search.html
			try:
				if not self.cc_licenses:
					responseUnStripped = self.api.photos_search(text=queryTerm, 
						content_type=1,
						page=(pageNumber+1),
						format='json')
				else:
					responseUnStripped = self.api.photos_search(text=queryTerm, 
						content_type=1, 
						page =(pageNumber+1),
						license=self.cc_licenses,
						format='json')
				response = simplejson.loads(re.search(r'jsonFlickrApi\(>?(.+)\)', responseUnStripped).group(1))
				self.grabDataFlickr(response['photos']['photo'])
			except (IndexError,TypeError,ValueError,NameError):  
				print 'skipping'
				return 

		elif self.searchEngine == '500px':
			try:
				response = self.api.photos_search(require_auth=True,
					tag=queryTerm,
					page=(pageNumber+1),
					image_size=5)
				dataInfo = response['photos']
			except (IndexError,TypeError,ValueError,NameError):  
				print 'skipping'
				return 

		self.grabData(dataInfo)
		

	def doSearchPopular(self,pageNumber):
		self.opDir = self.baseDir + '/popular on ' + datetime.datetime.now().strftime('%d-%m-%Y')
		if not os.path.exists(self.opDir):
			os.makedirs(self.opDir)

		if self.searchEngine == '500px':
			try:
				currPage = pageNumber+1
				response = self.api.photos(require_auth=True, 
					feature='popular',
					sort='rating',
					image_size=5,
					page=currPage)
				dataInfo = response['photos']				
			except (IndexError,TypeError,ValueError,NameError):  
				print 'skipping'
				return 

		self.grabData(dataInfo)

def searchImage(searchTerm,searchEngine):
	currSearch = CrawlData(searchEngine)
	numPages = 10	
	for i in range(numPages):
		currSearch.doSearch(searchTerm,i)
		time.sleep(0.5) # for throttling

def searchPopular(searchEngine):
	currPopularSearch = CrawlData(searchEngine)
	numPages = 3000
	for i in range(numPages):
		currPopularSearch.doSearchPopular(i)



if __name__ == '__main__':
	print len(sys.argv)
	if len(sys.argv) > 2:
		searchTerm = ''
		if sys.argv[len(sys.argv)-1] == 'google' \
		or sys.argv[len(sys.argv)-1] == 'bing' \
		or sys.argv[len(sys.argv)-1] == 'flickr' \
		or sys.argv[len(sys.argv)-1] == '500px':
			searchEngine = sys.argv[len(sys.argv)-1]
			searchQueryRange = len(sys.argv)-1			
		else:
			print 'using default search engine'
			searchEngine = 'google' # default one
			searchQueryRange = len(sys.argv)
		for i in range(1,searchQueryRange):
			searchTerm = searchTerm + sys.argv[i] + " "
	elif len(sys.argv) == 2:
		print sys.argv[1]
		if sys.argv[1] == 'popular500px':
			searchPopular('500px')
			sys.exit(1)
		else:
			searchTerm = sys.argv[1]
	else: 
		print 'fdsfsd'
		searchEngine = 'google'
		searchTerm = 'rothko'

	searchImage(searchTerm.strip(),searchEngine)




