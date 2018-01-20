#!/usr/bin/python

import urllib2, re, os, sys, getopt, string, time, threading
from Queue import Queue

# class AppInfo(object):
	# def __init__(self, link, name, category, publisher, size, lastupdate, version, worksWith, requirements)
	
	#1)app name 2)category 3)publisher 4)download size 5)last updated 6)version 7)workswith 8)apprequires 9)urltodownloadxap 10)localfilelocationxap(when finish downloading, whr ur crawler save it to) 

class Crawl(threading.Thread):

	uniqueurls = set()
	downloaded = set()
	todownload = set()
	killed = False
	
	def __init__(self, threadID, amount, paid, directory, searchstring, category, afterdate, lock):
		threading.Thread.__init__(self)
		self.threadID = threadID
		self.amount = amount
		self.searchstring = searchstring
		self.category = category
		self.count = 0
		self.paid = paid	
		self.afterdate = afterdate
		if not os.path.exists(directory):
			os.makedirs(directory)
		self.directory = directory + "/"
		self.processedurls = set()
		self.lock = lock
		
	def run(self):
		while not Crawl.killed:
			if self.threadID == 0:			
				baseurl = "http://www.windowsphone.com/en-sg/store/"
				if(self.searchstring):
					baseurl = baseurl + "search?q=" + self.searchstring
				
				elif(self.category):
					paidstatus = ""
					categories = self.category.replace("-", "and") #assume user passes in category like "music-video" or "entertainment"			
					if(self.paid == 0):
						paidstatus = "top-free-apps/"
					elif(self.paid == 1):
						paidstatus = "top-paid-apps/"
					else:
						paidstatus = "new-apps/"		
				
					baseurl = baseurl + paidstatus + category + "/" + categories
				self.crawl(baseurl)
				print "Crawler Done!!"
				return
			
			else:
				while True:
					if(len(Crawl.todownload)):
						break
					else:
						time.sleep(5)

				while True:
					downurl = ""
					self.lock.acquire()
					if(len(Crawl.todownload)):
						downurl = Crawl.todownload.pop()
						Crawl.downloaded.add(downurl)			
					self.lock.release()
					
					if(downurl == ""):
						time.sleep(5)
						if(len(Crawl.todownload)):
							continue
						else:
							break
					
					self.download(downurl)	
				return
	
	def getSource(self, url):	
		source = ""
		retry = 5
		while retry:
			try:
				header = {'User-Agent':'Mozilla/5.0'} 
				httprequest = urllib2.Request(url, None, header) 
				response = urllib2.urlopen(httprequest) 
				source = response.read()
				break
			except urllib2.HTTPError:
				print "waiting..."
				time.sleep(1)
				retry -= 1
				
		return source
	
	def checkDownload(self, applink):
		result = False
		source = self.getSource(applink)
		free = re.search("<span.*price.*>Free</span>", source)
		if((paid == 2) or (free and paid == 0) or (not free and paid == 1)):
		
			if(self.afterdate == ""):
				result = True
			
			else:
				date = re.search("<.*>Last updated<.*>[.\s]*<.*>[.\s]*<.*>(\d+)/(\d+)/(\d+)<.*>", source)
				day = int(date.group(1))
				month = int(date.group(2))
				year = int(date.group(3))
				
				after = re.search("(\d+)/(\d+)/(\d+)", afterdate)
				afterday = int(after.group(1))
				aftermonth = int(after.group(2))
				afteryear = int(after.group(3))
							
				if(year > afteryear):
					result = True
				elif(year == afteryear):
					if(month > aftermonth):
						result = True
					elif(month == aftermonth):
						if(date > afterdate):
							result = True
				
		else:
			result = False
		
		
		return result
	
	def crawl(self, baseurl):	
		
		if(self.count >= self.amount and self.amount != 0):
			return
		
		base = "http://www.windowsphone.com/en-sg/store/"
		
		source = self.getSource(baseurl)
		# print baseurl
		
		Crawl.uniqueurls.add(baseurl)
		urls = re.findall(base + "app/[\w-]+/[\w-]+", source) #regex for app page
		for down in set(urls):
			if(down not in self.processedurls):
				if(self.checkDownload(down)):
					self.lock.acquire()
					if(down not in Crawl.downloaded):
						Crawl.todownload.add(down)
						self.count += 1
					self.lock.release()						
					if(self.count >= self.amount and self.amount != 0):
						return
				self.processedurls.add(down)
		
		
		if(self.searchstring):
			
			self.getNextLinks(0, base, baseurl, source)
		
		elif(self.category):
			
			self.getNextLinks(1, base, baseurl, source)		
			
		elif(baseurl == base):
			alphabet = list(string.ascii_lowercase)
		
			for letter in alphabet:
				self.crawl(base + "search?q=" + letter)	
				if(self.count >= self.amount and self.amount != 0):
					return
		
		else:
			for url in set(urls):					
				if(url not in self.uniqueurls):								
					self.crawl(url) #calls recursive function on that url
				
	def getNextLinks(self, searchcategory, base, baseurl, source):
		
		urlregx = ""
		start = ""
		
		if(searchcategory == 0):
			urlregex = "(" + base + "search\?q=[^&]*)(&startIndex=)?(\d+)?"
			start = "&"
		else:
			urlregex = "(" + base + "[^\?]*)(\?startIndex=)?(\d+)?"
			start = "?"
		
		reg = re.compile(urlregex)
		m = reg.search(baseurl)
			
		nextpage = re.compile('<a.*id="nextLink".*</a>')
		if(nextpage.search(source) is not None):
				
			searchbase = m.group(1)
				
			if(m.group(3) is not None):
				nextindex = int(m.group(3)) + 48
				searchbase += m.group(2) + str(nextindex)
			else:
				searchbase += start + "startIndex=48"
			
			self.crawl(searchbase)	
		
	
	def download(self, url):
		
		file = url + "/xap?apptype=regular"
		name = re.search("(?:app/)([\w-]+)(?:/)", file).group(1)
		#self.uniqueurls.add(url)
		#self.count += 1
		destfile = name + ".xap"
		# fh = open(self.directory + destfile, "w")
		print "Downloading %s.xap" % name
		# print "From %s\n" % url	
		# fh.write(urllib2.urlopen(file).read())				
		# fh.close()
		
	def retrieveinfo(self, url):
		
		header = {'User-Agent':'Mozilla/5.0'} 
		httprequest = urllib2.Request(url, None, header) 
		response = urllib2.urlopen(httprequest) 
		source = response.read()
		name = re.search("(?:<h1.*name.*>)(.*)</h1>", source).group(1)
		categories = re.findall("(?:application.*Category.>)([\w +]*)(?:<.*)", source)
		publisher = re.search("(?:<.*>Publisher<.*>[.\s]*<.*>(.*)<.*>)", source).group(1)
		size = re.search("<.*>Download size<.*>[.\s]*<.*>(.*)<.*>", source).group(1)
		lastupdate = re.search("<.*>Last updated<.*>[.\s]*<.*>(.*)<.*>").group(1)
		version = re.search("<.*>Version<.*>[.\s]*<.*>(.*)<.*>", source).group(1)
		worksWith = re.findall("<.*operatingSystems.*>(.*)<.*>", source)
		requires = re.search("<.*>App requires<.*>[.\s]*<ul>[.\s]*((?:<.*>[.\s]*)*)</ul>", source).group(1)
		requirements = re.findall("[.\s]*<li>(.*)</li>", requires)
		
		
		#1)app name 2)category 3)publisher 4)download size 5)last updated 6)version 7)workswith 8)apprequires 9)urltodownloadxap 10)localfilelocationxap(when finish downloading, whr ur crawler save it to) 
		
		

def helpmenu():
		print "\nUsage: %s [options]\n\n" % sys.argv[0]
		print "-a: Download both free and paid applications\n"
		print "-c <category>: Search only from category. Cannot be used with -s\n" 
		print "-d <directory>: Specify directory to download to\n"
		print "-f: Download only free applications\n"
		print "-h: Prints help menu\n"
		print "-i: Infinite xap download\n"
		print "-n <number>: Specify the number of xap to download\n"
		print "-p: Download only paid applications\n"
		print "-s <searchstring>: Use a search string. Cannot be used with -c\n"
		print "-u <date>: Only download xap files last updated after specified date\n"
		print "\n"
		sys.exit()
		
if __name__ == "__main__":
		
	baseurl = "http://www.windowsphone.com/en-sg/store/" #starting url
	amt = 10
	paid = 2
	directory = os.getcwd()
	searchstring = ""
	category = ""
	afterdate = ""
	
	try: 
		opts, args = getopt.getopt(sys.argv[1:], "ac:d:fhipn:s:u:")
	except getopt.GetoptError:
		helpmenu()
		
	for opt, arg in opts:
		if opt == '-h':
			helpmenu()
		
		elif opt == "-c":
			category = arg
			
		elif opt == "-i":
			amt = 0
			
		elif opt == "-n":
			if arg.isdigit():
				amt = int(arg)
			else:
				helpmenu()
				
		elif opt == "-p":
			paid = 1		
		elif opt == "-f":
			paid = 0
		elif opt == "-a":
			paid = 2
			
		elif opt == "-d":
			directory = arg
		
		elif opt == "-s":
			searchstring = arg
		
		elif opt == "-u":
			afterdate = arg
	
	if(searchstring and category):
		helpmenu()
	
	lock = threading.Lock()
	
	webcrawlers = []
	
	for i in range(3):
		t = Crawl(i, amt, paid, directory, searchstring, category, afterdate, lock) 
		t.daemon = True
		webcrawlers.append(t)
		t.start()
	# crawler = Crawl(1, amt, paid, directory, searchstring, category, afterdate, lock)
	# downloader1 = Crawl(2, amt, paid, directory, searchstring, category, afterdate, lock)
	# downloader2 = Crawl(3, amt, paid, directory, searchstring, category, afterdate, lock)
	# downloader3 = Crawl(4, amt, paid, directory, searchstring, category, afterdate, lock)

	
	# downloader1.daemon = True
	# downloader2.daemon = True
	# downloader3.daemon = True
	
	try:
		for t in webcrawlers:
			while True:
				t.join(1)
				if not t.isAlive:
					break
		# downloader1.start()
		# downloader2.start()
		# downloader3.start()		
	except (KeyboardInterrupt, SystemExit):
		Crawl.killed = True
		sys.exit()	
	# for link in Crawl.todownload:
		# print link

