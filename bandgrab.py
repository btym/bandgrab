from imgurpython import ImgurClient
import traceback
import sys
import time
import urllib
import mechanize
import json
import re
import subprocess
import os
import zipfile
import realwhatapi as whatapi
from bs4 import BeautifulSoup
from cStringIO import StringIO

imgur = ImgurClient('YOUR','KEYS')
api = whatapi.WhatAPI(username="WHAT USERNAME",password="WHAT PASSWORD")

tracker = "http://tracker.what.cd:34000/"
passkey = "YOUR PASSKEY"

output_folder = "/home/sbu/downloads/auto/"
torrent_watch = "/home/sbu/downloads/watch/"

acceptable_tags = ['1920s','1930s','1940s','1950s','1960s','1970s','1980s','1990s','2000s','2010s','alternative','ambient','apps.linux','apps.mac','apps.sound','apps.windows','bluegrass','blues','breaks','classical','comedy','comics','country','dance','drum.and.bass','dubstep','electro','electronic','emo','experimental','folk','funk','garage','grunge','hardcore.dance','hardcore.punk','hip.hop','house','idm','indie','industrial','jazz','jpop','mashup','metal','minimal.electronic','new.age','pony','pop','post.rock','progressive.rock','psychedelic','psytrance','punk','reggae','rhythm.and.blues','rock','sheet.music','ska','soul','techno','trance','trip.hop','uk.garage','vanity.house','world.music']

def make_torrent(input_dir, output_dir):
    torrent = os.path.join(output_dir, os.path.basename(input_dir)) + ".torrent"
    if not os.path.exists(os.path.dirname(torrent)):
        os.path.makedirs(os.path.dirname(torrent))
    tracker_url = '%(tracker)s%(passkey)s/announce' % {
        'tracker' : tracker,
        'passkey' : passkey,
    }
    command = ["mktorrent", "-p", "-a", tracker_url, "-o", torrent, input_dir]
    subprocess.check_output(command, stderr=subprocess.STDOUT)
    return torrent

def handle_album(album_url):
	conn = urllib.urlopen(album_url)
	content = conn.read()
	if conn.geturl().endswith("-ep") or conn.geturl().endswith("-e-p"):
		release_type = '5'
	elif "demo" in conn.geturl():
		release_type = '23'
	else:
		release_type = '1'
	conn.close()

	embeddata = re.search('var EmbedData = ({.*?});',content,re.DOTALL).group(1)

	album_title = re.search('album_title: "(.*)",',embeddata).group(1)
	album_art = 'http://f1.bcbits.com/img/a'+re.search('art_id: (\d*),',embeddata).group(1)+'_16.jpg'
	artist = re.search('artist: "(.*)",',embeddata).group(1)

	if artist.lower() == 'various artists':
		return

	tags = []

	for tag in re.findall('http:\/\/bandcamp\.com\/tag\/([\w\d]+)',content):
		ftag = tag.replace(' ','.')
		if ftag in acceptable_tags:
			tags.append(ftag)

	albumid = re.search(r'album id (?P<id>\d+)', content).group('id')

	fr = open('bandgrabcache','r')
	if albumid in fr.read():
		fr.close()
		return
	fr.close()

	bcdesc = re.search('Description" content="(.*?)">',content,re.DOTALL).group(1)
	bcdesc = str(BeautifulSoup(bcdesc))

	year = re.search('.* (\d{4})', bcdesc).group(1)
	if year != '2015':
		fw = open('bandgrabcache','a')
		fw.write(albumid+'\n')
		fw.close()
		return

	description = bcdesc+"\n"+album_url

	try:
		conn = urllib.urlopen(re.search('(?<=freeDownloadPage: ")[^"]+',content).group(0))
	except:
		fw = open('bandgrabcache','a')
		fw.write(albumid+'\n')
		fw.close()
		return

	whatsearch = api.request('browse',searchStr='',groupname=album_title,artistname=artist)
	if len(whatsearch['response']['results']) == 0:
		print '------'
		print album_title + " by " + artist + " ("+release_type+")"
		print 'No results on What.CD'
	else:
		for torrent in whatsearch['response']['results'][0]['torrents']:
			if torrent['format'] == 'FLAC':
				return
		print '------'
		print album_title + " by " + artist + " ("+release_type+")"
		print 'Group exists on What.CD but not in FLAC'

	if release_type == '5':
		whatsearch = api.request('browse',searchStr='',groupname=re.search('(.*) .*',album_title).group(1),artistname=artist)
		if len(whatsearch['response']['results']) == 0:
			print 'No results without "EP", either'
		else:
			for torrent in whatsearch['response']['results'][0]['torrents']:
				if torrent['format'] == 'FLAC':
					return
			print '------'
			print album_title + " by " + artist + " ("+release_type+")"
			print 'Group exists on What.CD but not in FLAC'

	content = conn.read()
	conn.close()
	info = re.search(r'items: (.*?),$', content, re.MULTILINE).group(1)
	info = json.loads(info)[0]
	initial_url = info['downloads']['flac']['url']
	re_url = r'(?P<server>http://(.*?)\.bandcamp\.com)/download/album\?enc=flac&fsig=(?P<fsig>.*?)&id=(?P<id>.*?)&ts=(?P<ts>.*)$'
	m_url = re.match(re_url, initial_url)
	request_url = '%s/statdownload/album?enc=flac&fsig=%s&id=%s&ts=%s&.rand=665028774616&.vrs=1' % (m_url.group('server'), m_url.group('fsig'), albumid, m_url.group('ts'))
	conn = urllib.urlopen(request_url)
	final_url_webpage = conn.read()
	conn.close()
	final_url = re.search(r'"retry_url":"(.*?)"', final_url_webpage).group(1)
	conn = urllib.urlopen(final_url)
	filename = unicode(re.search('filename="([^"]+)', conn.info()['Content-Disposition']).group(1),'utf-8')
	conn.close()
	print 'Donwloading zip...'
	urllib.urlretrieve(final_url,filename)
	zipf = zipfile.ZipFile(filename, 'r')
	foldername = output_folder+os.path.splitext(filename)[0]
	print 'Extracting files...'
	try:
		zipf.extractall(foldername)
	except:
		os.remove(filename)
		return
	os.remove(filename)
	try:
		[os.rename(foldername+'/'+f, foldername+'/'+f.replace(artist+' - '+album_title+' - ', '')) for f in os.listdir(foldername) if not f.startswith('.')]
	except:
		fw = open('bandgrabcache','a')
		fw.write(albumid+'\n')
		fw.close()
		return
	print 'Making torrent...'
	torrent_path = make_torrent(foldername, torrent_watch)
	print 'Uploading torrent...'
	upload_torrent(torrent_path, artist, album_title, year, release_type, tags, album_art, description)
	fw = open('bandgrabcache','a')
	fw.write(albumid+'\n')
	fw.close()
	print '------'

def upload_torrent(torrent_path, artist, title, year, releasetype, tags, album_art, description):
	response = api.session.get("https://what.cd/upload.php")
	forms = mechanize.ParseFile(StringIO(response.text.encode('utf-8')), "https://what.cd/upload.php")
	form = forms[-1]
	form.find_control('file_input').add_file(open(torrent_path), 'application/x-bittorrent', os.path.basename(torrent_path))
	form['artists[]'] = artist
	form['title'] = title
	form['year'] = year
	form.find_control(name='releasetype').value = [releasetype]
	form['format'] = ['FLAC']
	form['bitrate'] = ['Lossless']
	form['media'] = ['WEB']
	form['tags'] = ','.join(tags)
	album_art = imgur.upload_from_url(album_art)['link']
	form['image'] = album_art
	form['album_desc'] = description
	form['release_desc'] = 'This album entry/torrent group was generated automatically. If any information is incorrect, please PM me.'
	_, data, headers = form.click_request_data()
	return api.session.post("https://what.cd/upload.php", data=data, headers=dict(headers))

def search_tag(tag):
	for i in range(25):
		conn = urllib.urlopen("https://bandcamp.com/tag/"+tag+"?page="+str(i+1)+"&sort_field=pop")
		content = conn.read()
		conn.close()
		for url in re.findall('http:\/\/\w+?\.bandcamp\.com\/album[^"]+',content):
			try:
				handle_album(url)
			except:
				print 'Error while handling '+url+":"
				traceback.print_exc()


def login(api):
    loginpage = 'https://what.cd/login.php'
    data = {'username': api.username,
            'password': api.password}
    r = api.session.post(loginpage, data=data)
    if r.status_code != 200:
        print r
    accountinfo = api.request('index')['response']
    api.authkey = accountinfo['authkey']
    api.passkey = accountinfo['passkey']
    api.userid = accountinfo['id']


headers = {
    'Connection': 'keep-alive',
    'Cache-Control': 'max-age=0',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_3)'\
        'AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.79'\
        'Safari/535.11',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9'\
        ',*/*;q=0.8',
    'Accept-Encoding': 'gzip,deflate,sdch',
    'Accept-Language': 'en-US,en;q=0.8',
    'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3'}

api.session.headers.update(headers)
login(api)

while True:
	search_tag("drone")
	search_tag("lo-fi")
	search_tag("shoegaze")
	search_tag("indie pop")
	search_tag("chill")
	search_tag("funk")
	search_tag("psychadelic")
	search_tag("blues")
	search_tag("rock")
	search_tag("pop")
	search_tag("indie")
	search_tag("electronic")
	search_tag("folk")
	search_tag("jazz")
	search_tag("ambient")
	search_tag("acoustic")
	search_tag("soul")
	search_tag("hip hop")
	search_tag("alternative")
	search_tag("experimental")
	search_tag("classical")
	time.sleep(43200)
