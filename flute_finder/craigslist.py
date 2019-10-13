# -*- coding: utf-8 -*-
import requests
import re

#import dateutil
import datetime

url_list = {
    "https://newyork.craigslist.org/search/sss?query=flute+-drill+-champagne+-football+-fluted+-chrome+-shank+-endmill+-cnc+-glass&sort=date&search_distance=75&postal=07030"
}

def search():
    FOUND_URLS = {}

    for url in url_list:
        r = requests.get(url)

        # t⃘͢his i͓̍s bad beca͙̟use you cannot͚̟ parse html wit̜̐h̞̯ reg̰̭ex for ht⃓︠m⃗͆l is not a r᷍e̿ġu̅l̼aͣr̕ l̶ä́n͊g̟úǎg̴e̵ͧ n͇ͩO̟͜ s͙⃟t⃗͠O̓͞P̮ͪ y⃔̐O͗́̎u᷂᷉̕ c᷂̋̅Aͬͤ͠N⃓̛̏t⃒͔͆ S̰ͨͯT̆⃞⃒ͫO̮̯᷂ͥP᷊︣ͦͦ T᷄ͤͧ̐H᷿͔ͧ︣ë́᷃̅̂ P̨͙͐᷆̿ơͧ᷉͗̚N̮̤᷁᷃᷀Ý̛̝̺͗ H͖̊̍͗︡Ë̷͉̯͚́͘ C̤̙̃⃗̅ͅO̧̘̼᷿⃐ͫM̛᷂͕͎̃ͭe⃒͚⃗︣͒̚ṩ⃒̣̖͈̜S̢̃ͫ̓⃐⃛̇
        CRAIGSLIST_URL_AND_POST_REGEX = "<li class=\"result-row\".*?<a href=\"(.*?)\".*?<time class=\"result-date\" datetime=\"(.*?)\".*?</li>"
        craigslist_re = re.compile(CRAIGSLIST_URL_AND_POST_REGEX)
        matches = re.findall(CRAIGSLIST_URL_AND_POST_REGEX, r.text, flags=re.DOTALL)

        for url, date_posted in matches:
            date = datetime.datetime.strptime(date_posted, "%Y-%m-%d %H:%M") #2019-10-11 18:19
            if date > datetime.datetime(2019, 10, 7):
                FOUND_URLS[url] = date_posted

    return FOUND_URLS


search()
