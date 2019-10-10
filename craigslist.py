import requests
import csv
import os
import re
import smtplib
import secrets.craigslist_secrets as secrets

urls = {
    "craigslist": [
        "https://newyork.craigslist.org/search/sss?format=rss&query=flute&sort=rel",
        "https://newjersey.craigslist.org/search/sss?format=rss&query=flute&sort=rel",
    ],
}

DATABASE_FILE = "db.csv"
if not os.path.isfile(DATABASE_FILE):
    with open(DATABASE_FILE, "w") as f:
        f.write("")

DATABASE = {}
with open(DATABASE_FILE, "r") as f:
    reader = csv.reader(f)
    for line in reader:
        host, url, post_date = line
        if host not in DATABASE:
            DATABASE[host] = {}

        DATABASE[host][url] = post_date

def WRITE_TO_DB(host, url, date_posted):
    global DATABASE
    if host not in DATABASE:
        DATABASE[host] = {}

    DATABASE[host][url] = date_posted

def SAVE_DB():
    global DATABASE
    global DATABASE_FILE
    with open(DATABASE_FILE, "w") as f:
        writer = csv.writer(f)
        for host, data in DATABASE.items():
            for url, date_posted in data.items():
                writer.writerow([host, url, date_posted])

def IS_NEW_TO_DB(host, url, date_posted):
    global DATABASE
    return host not in DATABASE or url not in DATABASE

def NOTIFY_OF_NEW_URL(new_urls):
    recipients = secrets.recipients

    email_text = ""

    for host, data in new_urls.items():
        for url, date_posted in data:
            email_text += "--\nTYPE: %s\nURL: %s\nDATE POSTED: %s\n\n" % (host, url, date_posted)

    print email_text

    sender = secrets.gmail_user
    server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    server.ehlo()
    server.login(sender, secrets.gmail_password)

    for recipient in recipients:
        server.sendmail(sender, recipient, email_text)

    server.close()

NEW_URLS = {}
for host, url_list in urls.items():
    for url in url_list:
        r = requests.get(url)

        CRAIGSLIST_URL_AND_POST_REGEX = "<item rdf:about=\"(?P<url>.*?)\">.*?<dc:date>(?P<post_date>.*?)</dc:date>.*?<\/item>"
        craigslist_re = re.compile(CRAIGSLIST_URL_AND_POST_REGEX)
        matches = re.findall(CRAIGSLIST_URL_AND_POST_REGEX, r.text, flags=re.DOTALL)

        print matches

        for url, date_posted in matches:
            print url, date_posted
            if IS_NEW_TO_DB(host, url, date_posted):
                WRITE_TO_DB(host, url, date_posted)

                if host not in NEW_URLS:
                    NEW_URLS[host] = []
                NEW_URLS[host].append((url, date_posted))
            else:
                print "Not a new link... "+url
        SAVE_DB()

if len(NEW_URLS) > 0:
    NOTIFY_OF_NEW_URL(NEW_URLS)
