#!/usr/bin/env python3
import requests
import re
import os
import urllib
import html

# Downloads files from url. Enumerates files into pretty format using the tr title as filename.
# DL's both flac and mp3.

# Reqs:
# - py3.7+
# - requests library

save_loc = "R:\\Evan Doorbell\\Group 1 Narrated Tape Playlist"


url = "http://www.evan-doorbell.com/production/group1.htm"
html_raw = requests.get(url).text
root_url = os.path.dirname(url)

space_cleaner_re = re.compile(r"\s+")
tag_cleaner_re = re.compile(r"<.*?>")
illegal_char_cleaner_re = re.compile(r"[<>:\"\/\\|?*]")
def cleanTitle(title: str) -> str:
	tmp = urllib.parse.unquote(title)
	tmp = html.unescape(tmp)
	tmp = tmp.replace("\n", " ")
	tmp = space_cleaner_re.sub(" ", tmp)
	tmp = tag_cleaner_re.sub("", tmp)
	tmp = illegal_char_cleaner_re.sub("", tmp) # illegal windows path chars
	return tmp

re_flags = re.DOTALL | re.MULTILINE
for fileformat in [".mp3", ".flac"]:
	regex = rf'<tr>\s+<td width="289".*?font size="2">(.*?)<\/font>.*?<a href="(\w+\{fileformat})">.*?<\/tr>'
	dest_folder = os.path.join(save_loc, fileformat.strip("."))
	if not os.path.exists(dest_folder):
		os.mkdirs(dest_folder, exist_ok=True)

	i = 1
	for find in re.findall(regex, html_raw, re_flags):
		title, filename = find
		formatted_title = f"{i:02}. {cleanTitle(title).strip()}{fileformat}"
		print((formatted_title, filename))
		i += 1

		dest_loc = os.path.join(dest_folder, formatted_title)
		file_url = f"{root_url}/{filename}"
		print("DLing from... "+file_url)
		print("Saving to..."+dest_loc)

		r = requests.get(url, stream=True)
		with open(dest_loc, "wb") as f:
			for chunk in r.iter_content(chunk_size=1024):
				if chunk:
					f.write(chunk)
