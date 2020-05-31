# -*- coding: utf-8 -*-
import requests
import re

#import dateutil
import datetime

BASE_URL = "https://www.ebay.com/sch/i.html?_from=R40&_nkw=%s&_sacat=0&_sop=10&rt=nc&_stpos=07039&_sadis=100&LH_PrefLoc=99&_fspt=1&_ipg=200"
url_params = [
    {
        "search": ["flute"],
        "ignore": ["auger", "extractor", "extractors", "spiral", "bit", "screw", "router", "figure", "figures", "milling", "statue", "magic flute", "volume", "sheet", "sheetmusic", "funko", "songbook", "cd", "book", "endmills", "floppy", "knob", "mills", "carbide", "NPS", "NPT", "high speed", "crystal", "mill", "drill", "cnc", "champagne", "football", "glass", "fluted", "chrome", "endmill", "shank"],
    },
    {
        "search": ["piccolo"],
        "ignore": ["book", "dragonball", "cd", "funko", "trumpet", "snare", "dragon"],
    },
]

def search():
    FOUND_URLS = {}

    for params in url_params:
        terms = []

        for part in ["search", "ignore"]:
            query_parts = params[part]
            query_parts = map(lambda term: term if " " not in term else "\"%s\"" % (term.replace(" ", "+")), query_parts)

            if part == "ignore":
                query_parts = map(lambda term: "-"+term, query_parts)
            terms.extend(query_parts)

        query_string = "+".join(terms)

        url = BASE_URL % query_string
        r = requests.get(url)
        print url
        # t⃘͢his i͓̍s bad beca͙̟use you cannot͚̟ parse html wit̜̐h̞̯ reg̰̭ex for ht⃓︠m⃗͆l is not a r᷍e̿ġu̅l̼aͣr̕ l̶ä́n͊g̟úǎg̴e̵ͧ n͇ͩO̟͜ s͙⃟t⃗͠O̓͞P̮ͪ y⃔̐O͗́̎u᷂᷉̕ c᷂̋̅Aͬͤ͠N⃓̛̏t⃒͔͆ S̰ͨͯT̆⃞⃒ͫO̮̯᷂ͥP᷊︣ͦͦ T᷄ͤͧ̐H᷿͔ͧ︣ë́᷃̅̂ P̨͙͐᷆̿ơͧ᷉͗̚N̮̤᷁᷃᷀Ý̛̝̺͗ H͖̊̍͗︡Ë̷͉̯͚́͘ C̤̙̃⃗̅ͅO̧̘̼᷿⃐ͫM̛᷂͕͎̃ͭe⃒͚⃗︣͒̚ṩ⃒̣̖͈̜S̢̃ͫ̓⃐⃛̇
        EBAY_URL_AND_POST_REGEX = "<li class=\"s-item.*?<a.*?href=\"?(https:\/\/www.ebay.com\/itm\/[^\">]*?)\"?>.*?s-item__listingDate.*?class=\"?BOLD\"?>(.*?)<\/span>.*?<\/li>"
        LISTINGS_REGEX = "<li class=\"s-item\s+\" data-view.*?</li>"

        listings = re.findall(LISTINGS_REGEX, r.text, flags=re.DOTALL)
        for listing in listings:

            matches = re.findall(EBAY_URL_AND_POST_REGEX, listing, flags=re.DOTALL)
            for url, date_posted in matches:
                print url, date_posted
                year = datetime.date.today().year
                date = datetime.datetime.strptime(str(year)+" "+date_posted, "%Y %b-%d %H:%M") # Oct-11 17:53 # I'm sorry this line sucks but it's a hack.
                if date > datetime.datetime(2019, 10, 7):
                    FOUND_URLS[url] = date.isoformat()

    return FOUND_URLS
