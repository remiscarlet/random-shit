import requests
import re

#import dateutil
import datetime

url_list = {
    "https://www.ebay.com/sch/i.html?_from=R40&_nkw=flute&_sacat=0&_sop=10&rt=nc&_stpos=07039&_sadis=100&LH_PrefLoc=99&_fspt=1&_ipg=200",
}

def search():
    FOUND_URLS = {}

    for url in url_list:
        r = requests.get(url)

        EBAY_URL_AND_POST_REGEX = "<li class=\"s-item.*?<a href=\"(https:\/\/www.ebay.com\/itm\/[^\"]*?)\".*?s-item__listingDate.*?class=\"BOLD\">(.*?)<\/span>.*?<\/li>"
        matches = re.findall(EBAY_URL_AND_POST_REGEX, r.text, flags=re.DOTALL)

        for url, date_posted in matches:
            date = datetime.datetime.strptime("2019 "+date_posted, "%Y %b-%d %H:%M") # Oct-11 17:53 # I'm sorry this line sucks but it's a hack.
            if date > datetime.datetime(2019, 10, 7):
                FOUND_URLS[url] = date.isoformat()

    return FOUND_URLS
