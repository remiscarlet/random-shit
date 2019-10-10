import requests
import re
import secrets.craigslist_secrets as secrets

#import dateutil
import datetime

url_list = {
    "https://newyork.craigslist.org/search/sss?format=rss&query=flute&sort=rel",
    "https://newjersey.craigslist.org/search/sss?format=rss&query=flute&sort=rel",
    "https://hartford.craigslist.org/search/sss?format=rss&query=flute&sort=rel",
    "https://newlondon.craigslist.org/search/sss?format=rss&query=flute&sort=rel",
    "https://newhaven.craigslist.org/search/sss?format=rss&query=flute&sort=rel",
    "https://nwct.craigslist.org/search/sss?format=rss&query=flute&sort=rel",
}

def search():
    FOUND_URLS = {}

    for url in url_list:
        r = requests.get(url)

        CRAIGSLIST_URL_AND_POST_REGEX = "<item rdf:about=\"(?P<url>.*?)\">.*?<dc:date>(?P<post_date>.*?)</dc:date>.*?<\/item>"
        craigslist_re = re.compile(CRAIGSLIST_URL_AND_POST_REGEX)
        matches = re.findall(CRAIGSLIST_URL_AND_POST_REGEX, r.text, flags=re.DOTALL)

        for url, date_posted in matches:
            date = datetime.datetime.strptime(date_posted, "%Y-%m-%dT%H:%M:%S-04:00") #2019-10-09T15:07:02-04:00
            if date > datetime.datetime(2019, 10, 7):
                FOUND_URLS[url] = date_posted
            else:
                print "FOUND URL POSTED BEFORE MINDATE: %s" % url

    return FOUND_URLS


