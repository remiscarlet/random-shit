#!/usr/bin/python

import requests
import tempfile
import csv
import os
import sys
import re
import smtplib
import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import secrets.craigslist_secrets as secrets

import craigslist
import ebay

IS_LIVE_RUN = True if len(sys.argv) > 1 and sys.argv[1] == "--real-run" else False

if not os.path.isdir(secrets.ROOT_DIR):
    os.makedirs(secrets.ROOT_DIR)
os.chdir(secrets.ROOT_DIR)

if IS_LIVE_RUN:
    DATABASE_FILE = "db.csv"
else:
    DATABASE_FILE = "db.test.csv"
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
    return host not in DATABASE or url not in DATABASE[host]

def NOTIFY_OF_NEW_URL(new_urls, host, IS_LIVE_RUN = False):
    if IS_LIVE_RUN:
        recipients = secrets.RECIPIENTS
    else:
        recipients = secrets.RECIPIENTS_TEST

    sender = secrets.GMAIL_USER

    new_urls = [(url, date_posted) for url, date_posted in new_urls.items()]
    new_urls.sort(key = lambda tup: tup[1])

    print "____________"
    print new_urls[0:5]

    email_text = ""
    tmp_handle, tmp_path = tempfile.mkstemp(suffix=".csv")
    with open(tmp_path, "w") as f:
        writer = csv.writer(f)
        writer.writerow(["url", "date_posted"])

        for url, date_posted in new_urls:
            email_text += "--\nURL: %s\nDATE POSTED: %s\n\n" % (url, date_posted)
            writer.writerow([url, date_posted])

    body = MIMEText(email_text, "plain")

    with open(tmp_path, "r") as f:
        attachment = MIMEText(f.read(), _subtype="text") # Hardcode cuz only sending CSVs
    attachment.add_header("Content-Disposition", "attachment", filename="new_flute_listings.csv")


    today = str(datetime.date.today())
    msg = MIMEMultipart()
    msg["From"] = sender
    msg["Subject"] = "%s - %s - New Flute Listings" % (host, today)
    msg.attach(body)
    msg.attach(attachment)

    server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    server.ehlo()
    server.login(sender, secrets.GMAIL_PASSWORD)

    for recipient in recipients:
        msg["To"] = recipient
        server.sendmail(sender, recipient, msg.as_string())

    server.close()
    f.close()

def PROCESS_URLS(host, found_urls):
    NEW_URLS = {}

    for url, date_posted in found_urls.items():
        print url
        if IS_NEW_TO_DB(host, url, date_posted):
            WRITE_TO_DB(host, url, date_posted)
            NEW_URLS[url] = date_posted
            print "FOUND NEW URL POSTED ON %s: %s" % (date_posted, url)

    SAVE_DB()

    return NEW_URLS

######################
## RUN

MAPPING = {
        #"Craigslist": craigslist.search(),
        "Ebay": ebay.search(),
}

for host, search_results in MAPPING.items():
    new_urls = PROCESS_URLS(host, search_results)

    if len(new_urls) > 0:
        NOTIFY_OF_NEW_URL(new_urls, host, IS_LIVE_RUN)
    else:
        print "No new URLs"



