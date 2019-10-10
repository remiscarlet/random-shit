#!/usr/bin/python

import requests
import tempfile
import csv
import os
import sys
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import secrets.craigslist_secrets as secrets

import craigslist


if not os.path.isdir(secrets.ROOT_DIR):
    os.makedirs(secrets.ROOT_DIR)
os.chdir(secrets.ROOT_DIR)

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
    return host not in DATABASE or url not in DATABASE[host]

def NOTIFY_OF_NEW_URL(new_urls, is_real_run = False):
    if is_real_run:
        recipients = secrets.RECIPIENTS
    else:
        recipients = [
            "scarletjaeger+test@gmail.com",
        ]

    sender = secrets.GMAIL_USER

    new_urls = [(url, date_posted) for url, date_posted in new_urls.items()]
    new_urls.sort(key = lambda tup: tup[0])

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

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["Subject"] = "New Flute Listings"
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
        if IS_NEW_TO_DB(host, url, date_posted):
            WRITE_TO_DB(host, url, date_posted)

            NEW_URLS[url] = date_posted
        else:
            print "Not a new link... "+url

    SAVE_DB()

    return NEW_URLS

######################
## RUN

is_real_run = True if len(sys.argv) > 1 and sys.argv[1] == "--real-run" else False

NEW_URLS = PROCESS_URLS("craigslist", craigslist.search())

if len(NEW_URLS) > 0:
    NOTIFY_OF_NEW_URL(NEW_URLS, is_real_run)



