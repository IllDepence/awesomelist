# -*- coding: utf-8 -*-

import http.client
import json
import os
import re
import time
import datetime
import unicodedata
import urllib.parse
import urllib.request
import sys

CLIENT_ID   = 'sirtetris-eky4q'
CLIENT_SEC  = 'AcF5qNj4St50Bf0mPLLU9BgpRObb'
USERS       = ['sirtetris','jinxitjing','pengu','Medeadea']

class Anime:
    def __init__(self, al_data):
        self.al_id = str(al_data['anime']['id'])
        self.title = al_data['anime']['title_romaji'].strip()
        self.img = al_data['anime']['image_url_med']
        if al_data['anime']['airing_status'] == 'currently airing':
            self.airing = 999
        else:
            self.airing = 0
        ep_total = al_data['anime']['total_episodes']
        if not ep_total is None and ep_total > 0:
            self.ep_total = str(ep_total)
        else:
            self.ep_total = '?'
        self.ep_seen = str(al_data['episodes_watched'])
        if self.ep_seen=='None': self.ep_seen = '0'

class AnimeList:
    def __init__(self, anilist_data):
        self.anilist_data = anilist_data
        self.owner = self.anilist_data['display_name']

        wlist_raw = self.anilist_data['lists']['watching']
        wlist_processed = []
        for al_data in wlist_raw:
            wlist_processed.append(Anime(al_data))
        self.watching = wlist_processed

        cdict_raw = self.anilist_data['lists']['completed']
        cdict_processed = []
        for al_data in cdict_raw:
            cdict_processed.append(Anime(al_data))
        self.completed = cdict_processed

class Watcher:
    def __init__(self, name, eps):
        self.name = name
        self.eps = eps

class CompAnime:
    def __init__(self, al_id, title, img, airing):
        self.al_id = al_id
        self.title = title
        self.img = img
        self.airing = airing
        self.watchers = []
    def addWatcher(self, name, eps):
        self.watchers.append(Watcher(name, eps))

class CompList:
    def __init__(self, lists):
        done_ids = []
        self.clist = []
        self.cdict = {}
        for l in lists:
            for w in l.watching:
                if not w.al_id in done_ids:
                    self.cdict[w.al_id] = CompAnime(w.al_id, w.title, w.img, w.airing)
                self.cdict[w.al_id].addWatcher(l.owner, w.ep_seen)
                done_ids.append(w.al_id)
        for l in lists:
            for c in l.completed:
                if c.al_id in done_ids:
                    self.cdict[c.al_id].addWatcher(l.owner, c.ep_seen)
        for i, ca in self.cdict.items():
            ca.watchers = sorted(ca.watchers, key=lambda k: -int(k.eps))
            self.clist.append(ca)
        self.clist = sorted(self.clist, key=lambda k: -(len(k.watchers)+k.airing))

def getAuthCode():
    print('You have to generate an auth code:\n'
          'http://moc.sirtetris.com/anihilist/echocode.php\n\n'
          'Paste it here, then continue with <ENTER>.')
    return sys.stdin.readline().strip()

def setup():
    if not os.path.exists('access_data.json'):
        auth_code = getAuthCode()
        newAccessToken(auth_code)
    else:
        getAccessToken() # may have to be refreshed

def callAPI(method, url, data=None, headers={}):
    conn = http.client.HTTPSConnection('anilist.co', 443)
    url = urllib.parse.quote(url,safe='/?=&')
    conn.request(method=method, url=url, body=data, headers=headers)
    resp_obj = conn.getresponse()
    resp_json = resp_obj.read().decode('utf-8')
    resp_data = json.loads(resp_json)
    return resp_data

def newAccessToken(auth_code):
    url = ('/api/auth/access_token?grant_type=authorization_code'
           '&client_id={0}&client_secret={1}&redirect_uri={2}'
           '&code={3}').format(CLIENT_ID,CLIENT_SEC,REDIR_FOO,auth_code)
    access_data = callAPI('POST', url)
    with open('access_data.json', 'w') as f:
        f.write(json.dumps(access_data))
    f.close()

def getAccessToken():
    with open('access_data.json', 'r') as f:
        access_json = f.read().rstrip()
    f.close()
    access_data = json.loads(access_json)
    now = int(time.time())
    if (now+60) > access_data['expires']:
        return refreshAccessToken(access_data['refresh_token'])
    else:
        return access_data['access_token']

def refreshAccessToken(refresh_token):
    url = ('/api/auth/access_token?grant_type=refresh_token'
           '&client_id={0}&client_secret={1}&refresh_token='
           '{2}').format(CLIENT_ID,CLIENT_SEC,refresh_token)
    access_data_new = callAPI('POST', url)
    with open('access_data.json', 'r+') as f:
        access_json = f.read().rstrip()
        access_data = json.loads(access_json)
        access_data['access_token'] = access_data_new['access_token']
        access_data['expires'] = access_data_new['expires']
        f.seek(0)
        f.truncate()
        f.write(json.dumps(access_data))
    f.close()
    return access_data['access_token']

def getAnilistData(user):
    url = ('/api/user/{0}/animelist?access_token='
           '{1}').format(user, getAccessToken())
    return callAPI('GET', url)

def main():
    anime_lists = []
    for u in USERS:
        anilist_data = getAnilistData(u)
        anime_lists.append(AnimeList(anilist_data))
    comp_list = CompList(anime_lists)
    t = datetime.datetime.now()
    page = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>awesomelist</title>
<style>
#main {
margin: 20px;
}
.entry {
clear: left;
overflow: hidden;
padding: 5px;
margin-top 15px;
border-bottom: solid 1px #000;
}
.entry img {
float: left;
margin-right: 15px;
}
.watchers {
float: left;
}
.airing {
background-color: #cef3d2;
}
.notairing {
background-color: #e1e1e1;
}
h3 {
margin: 0 0 5px 0;
}
</style>
</head>
<body>"""
    page += """<p>Last update: {0}.{1}.{2}, {3}:{4}</p>
<div id="main">""".format(t.day, t.month, t.year, t.hour+2, t.minute)
    for ca in comp_list.clist:
        class_extra = ' notairing'
        if ca.airing > 0:
            class_extra = ' airing'
        page += """<div class="entry{3}">
<h3>{1}</h3>
<a href="{0}"><img src="{2}"></a>
<div class="watchers">
""".format(ca.al_id, ca.title, ca.img, class_extra)
        for w in ca.watchers:
            page += '<p>{0}: {1}</p>'.format(w.name, w.eps)
        page += '</div></div>'
    page += """</div>
</body>
</html>"""
    with open('index.html', 'w') as f:
        f.write(page)
    f.close()

if __name__ == '__main__':
    main()
