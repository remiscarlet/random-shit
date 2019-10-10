import requests
import csv
import os
import re
import smtplib
import secrets.craigslist_secrets as secrets

url = "https://newyork.craigslist.org/search/sss?format=rss&query=flute"
url = "https://newyork.craigslist.org/search/sss?format=rss&query=flute&sort=rel"


r = requests.get(url)

CRAIGSLIST_URL_AND_POST_REGEX = "<item rdf:about=\"(?P<url>.*?)\">.*?<dc:date>(?P<post_date>.*?)</dc:date>.*?<\/item>"
craigslist_re = re.compile(CRAIGSLIST_URL_AND_POST_REGEX)
matches = re.findall(CRAIGSLIST_URL_AND_POST_REGEX, r.text, flags=re.DOTALL)

print matches

DATABASE_FILE = "db.csv"
if not os.path.isfile(DATABASE_FILE):
	with open(DATABASE_FILE, "w") as f:
		f.write("")

DATABASE = {}
with open(DATABASE_FILE, "r") as f:
	reader = csv.reader(f)
	for line in reader:
		url, post_date = line
		DATABASE[url] = post_date

def WRITE_TO_DB(url, date_posted):
	global DATABASE
	DATABASE[url] = date_posted 

def SAVE_DB():
	global DATABASE
	global DATABASE_FILE
	with open(DATABASE_FILE, "w") as f:
		writer = csv.writer(f)
		for url, date_posted in DATABASE.items():
			writer.writerow([url, date_posted])

def IS_NEW_TO_DB(url, date_posted):
	global DATABASE
	return url not in DATABASE
	

def NOTIFY_OF_NEW_URL(new_urls):
	recipients = secrets.recipients


	email_text = """
FOUND NEW LINKS:
%s
	""" % ("\n".join(["--\nURL: %s\nDATE POSTED: %s\n\n" % (url, date_posted) for url, date_posted in new_urls]))

	print email_text
	return

	sender = secrets.gmail_user
	server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
	server.ehlo()
	server.login(sender, secrets.gmail_password)
	
	for recipient in recipients:
		server.sendmail(sender, recipient, email_text)
	
	server.close()

NEW_URLS = []

for url, date_posted in matches:
	print url, date_posted
	if IS_NEW_TO_DB(url, date_posted):
		WRITE_TO_DB(url, date_posted)
		NEW_URLS.append((url, date_posted))
	else:
		print "Not a new link... "+url

if len(NEW_URLS) > 0:
	NOTIFY_OF_NEW_URL(NEW_URLS)

SAVE_DB()