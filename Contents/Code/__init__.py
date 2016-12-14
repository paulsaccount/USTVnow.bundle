import sys, os, re
import urllib, urllib2, socket, cookielib
import json, random

from datetime import datetime

TITLE       = 'USTVnow'
PREFIX      = '/video/ustvnow'
ART         = 'art-default.jpeg'
ICON        = 'icon-default.png'
ICON_PREFS  = 'icon-prefs.png'
XPATHS      = {'Live'       : "//div[contains(@class, 'livetv-content-pages')]",
               'Favorites'  : "//div[contains(@class, 'livetv-content-pages')]",
               'Recordings' : "//div[contains(@class, 'reccontentpage')]"}

BASE_URL         = 'http://m.ustvnow.com'
GUIDE            = 'http://www.ustvnow.com?a=do_login&force_redirect=1&manage_proper=1&input_username=%s&input_password=%s'
RECORD_PROGRAM   = 'http://www.ustvnow.com/recordprogram.php?id=%s&token=%s'
DELETE_RECORDING = 'http://www.ustvnow.com/recordprogram.php?delete=%s&token=%s'
LOGIN_URL        = BASE_URL + '/iphone/1/live/login?username=%s&password=%s'
LIVETV           = BASE_URL + '/gtv/1/live/channelguide?pgonly=true&token=%s'
RECORDINGS       = BASE_URL + '/iphone/1/dvr/viewdvrlist?pgonly=true&token=%s'
FAVORITES        = BASE_URL + '/iphone/1/live/showfavs?pgonly=true&token=%s'
ADD_FAVORITE     = BASE_URL + '/iphone/1/live/updatefavs?prgsvcid=%s&token=%s&action=add'
mBASE_URL = 'http://m-api.ustvnow.com'
mcBASE_URL = 'http://mc.ustvnow.com'

####################################################################################################
def Start():
    ObjectContainer.title1 = TITLE
    ObjectContainer.art = R(ART)
    DirectoryObject.thumb = R(ICON)
    DirectoryObject.art = R(ART)

####################################################################################################
@handler(PREFIX, TITLE, art=ART, thumb=ICON)
def MainMenu(view_group='InfoList'):
    Login()
    oc = ObjectContainer()
    oc.add(DirectoryObject(key = Callback(GetItems, title='All Channels', url=LIVETV), title = 'All Channels'))
    oc.add(PrefsObject(title = 'Preferences', thumb = R(ICON_PREFS)))
    return oc

####################################################################################################
@route(PREFIX + '/getitems')
def GetItems(title, url):
    oc = ObjectContainer(title2=title)
    quality = Prefs["quality"]
    if quality == "HD":
        quality = '4'
    elif quality == "High":
        quality = '3'
    elif quality == "Medium":
        quality = '2'
    elif quality == "Low":
        quality = '1' 
    page = get_link(int(quality))
    for item in page:
        codecs = get_Codecs(item['url'])
        if len(item['description']) > 0:
            summary = item['description']
        else:
            summary = 'No description available'
        try: durationTime = int(item['duration']) * 1000
        except: durationTime = 0
        oc.add(CreateVideoClipObject(
                smil_url = item['url'],
                title = item['title'],
                summary = summary,
                thumb = R(item['name'] + '.jpg'),
                duration = int(item['duration']),
                video_codec = codecs['video_codec'],
                resolution = codecs['resolution'],
                ))
    if len(oc) == 0:
        return ObjectContainer(title2=title, header=title, message='None Found')
    else:
        return oc
####################################################################################################

@route(PREFIX + '/createvideoclipobject', include_container=bool)
def CreateVideoClipObject(smil_url, title, summary, thumb, duration, video_codec, resolution, include_container=False, **kwargs):
    videoclip_obj = VideoClipObject(
        key = Callback(CreateVideoClipObject, smil_url=smil_url, title=title, summary=summary, thumb=thumb, duration=int(duration), video_codec=video_codec, resolution=resolution, include_container=True),
        rating_key = smil_url,
        title = title,
        summary = summary,
        thumb = thumb,
        duration = int(duration),
        items = [
            MediaObject(
                parts = [
                    PartObject(key=Callback(PlayVideo, smil_url=smil_url))
                ],
                protocol = 'hls',
                container = Container.MP4,
                video_codec = video_codec,
                audio_codec = AudioCodec.AAC,
                audio_channels = 2,
                video_resolution = resolution,
                duration = int(duration),
            )
        ]
    )
    if include_container:
        return ObjectContainer(objects=[videoclip_obj])
    else:
        return videoclip_obj

####################################################################################################
@indirect
@route(PREFIX + '/playvideo')
def PlayVideo(smil_url):
    return IndirectResponse(VideoClipObject, key=HTTPLiveStreamURL(url=smil_url))

####################################################################################################
def FormatDate(date):
    times = date.split('-')
    start = datetime.strptime(times[0], "%H:%M%p").strftime("%I:%M%p")
    end = datetime.strptime(times[1], "%H:%M%p").strftime("%I:%M%p")
    return start + '-' + end
####################################################################################################
def get_Codecs(url):
    playList = HTTP.Request(url).content
    for line in playList.splitlines():
        if 'BANDWIDTH' in line:
            stream = {}
            # stream['bitrate'] = int(Regex('(?<=BANDWIDTH=)[0-9]+').search(line).group(0))

            if 'RESOLUTION' in line:
                stream['resolution'] = int(Regex('(?<=RESOLUTION=)[0-9]+x[0-9]+').search(line).group(0).split('x')[1])
            else:
                stream['resolution'] = 0
            
            if 'CODECS' in line:
                stream['video_codec'] = re.findall(r'(?<=CODECS=)"(.*?)"', line)[0].split(',')[0]
            else:
                stream['video_codec'] = 'VideoCodec.H264'
            
    return stream
####################################################################################################
# def Get_Channels(title, url, xp):
#     content = get_json('gtv/1/live/channelguide', {'token': (Dict['token'])})
#     img = get_json()
#     #page = HTML.ElementFromURL(url % (Dict['token']), cacheTime=0)
#     #items = page.xpath(xp)
#     channels = []
#     results = content['results'];
#     for i in results:
#         try:
#             if i['order'] != 1:
#                 from datetime import datetime
#                 event_date_time = datetime.fromtimestamp(i['ut_start']).strftime('%I:%M %p').lstrip('0')
#                 name = Addon.cleanChanName(i['stream_code'])
#                 mediatype = i['mediatype']
#                 poster_url = mcBASE_URL + '/gtv/1/live/viewposter?srsid=' + str(i['srsid']) + '&cs=' + i['callsign'] + '&tid=' + mediatype
#                 mediatype = mediatype.replace('SH', 'tvshow').replace('EP', 'episode').replace('MV', 'movie').replace('SP', 'tvshow')
# #	                rec_url = '/gtv/1/dvr/updatedvr?scheduleid=' + str(i['scheduleid']) + '&token=' + self.token + '&action=add'
# #	                set_url = '/gtv/1/dvr/updatedvrtimer?connectorid=' + str(i['connectorid']) + '&prgsvcid=' + str(i['prgsvcid']) + '&eventtime=' + str(i['event_time']) + '&token=' + self.token + '&action=add'
#                 # if Addon.get_setting('free_package') != 'true':
#                 #     if name in ['CW','ABC','FOX','PBS','CBS','NBC','MY9']:
#                 #         channels.append({
#                 #             'name': name,
#                 #             'episode_title': i['episode_title'],
#                 #             'title': i['title'],
#                 #             'plot': i['description'],
#                 #             'mediatype': mediatype,
#                 #             'playable': True,
#                 #             'poster_url': poster_url,
#                 #             'rec_url': rec_url,
#                 #             'set_url': set_url,
#                 #             'event_date_time': event_date_time
#                 #                 })
#                 #     else:
#                 channels.append({
#                     'name': name,
#                     'episode_title': i['episode_title'],
#                     'title': i['title'],
#                     'plot': i['description'],
#                     'mediatype': mediatype,
#                     'playable': True,
#                     'poster_url': poster_url,
#                     'rec_url': rec_url,
#                     'set_url': set_url,
#                     'event_date_time': event_date_time
#                         })
#         except:
#             pass
# 
#     return channels

####################################################################################################
def get_link(quality):
        activation_check = account_check()
        passkey = get_passkey()
        content = get_json('gtv/1/live/channelguide', {'token': (Dict['token'])})
        channels = []
        results = content['results']
        stream_type = 'rtmp'
        for i in results:
            if i['order'] == 1:
                if quality == 4 and i['scode'] == 'whvl':
                    quality = (quality - 1)
                stream = get_json('stream/1/live/view', {'token': (Dict['token']), 'key': passkey, 'scode': i['scode']})['stream']
                url = stream.replace('smil:', 'mp4:').replace('USTVNOW1', 'USTVNOW').replace('USTVNOW', 'USTVNOW' + str(quality))
                name = cleanChanName(i['stream_code'])
                thumb = mcBASE_URL + '/' + i['img']
                mediatype = i['mediatype']
                if activation_check == 'True':
                    if name in ['CW','ABC','FOX','PBS','CBS','NBC','MY9']:
                        channels.append({
                            'name': name,
                            'url': url,
                            'title': name + ' ' + '-' + ' ' + i['title'],
                            'description': i['description'],
                            'duration': (i['runtime'] * 1000)
                             })
                else:
                    channels.append({
                        'name': name,
                        'url': url,
                        'title': name + ' ' + '-' + ' ' + i['title'],
                        'description': i['description'],
                        'duration': (i['runtime'] * 1000)
                        })
        return channels
####################################################################################################    
def get_passkey():
        passkey = get_json('gtv/1/live/viewdvrlist', {'token': (Dict['token'])})['globalparams']['passkey']
        return passkey
 ####################################################################################################   
def account_check():
    activation_check = get_json('gtv/1/live/getuserbytoken', {'token': (Dict['token'])})['data']['need_account_activation']
    return activation_check   
####################################################################################################
def get_json(path, queries={}):
        content = False
        url = build_json(path, queries)
        response = fetch(url)
        if response:
            content = json.loads(response.read())
        else:
            content = False
        return content
####################################################################################################
def fetch(url, form_data=False):
        opener = urllib2.build_opener()
        opener.addheaders = [('User-agent', 'Mozilla/5.0')]
        if form_data:
            req = urllib2.Request(url, form_data)
        else:
            req = url
        try:
            response = opener.open(req)
            return response
        except urllib2.URLError, e:
            return False
####################################################################################################
def build_json(path, queries={}):
        if queries:
            query = urllib.urlencode(queries)
            return '%s/%s?%s' % (mBASE_URL, path, query)
        else:
            return '%s/%s' % (mBASE_URL, path)
####################################################################################################
def cleanChanName(string):
    string = string.strip()
    string = string.replace('WLYH','CW').replace('WHTM','ABC').replace('WPMT','FOX').replace('WPSU','PBS').replace('WHP','CBS').replace('WGAL','NBC').replace('WHVLLD','MY9').replace('AETV','AE')
    string = string.replace('APL','Animal Planet').replace('TOON','Cartoon Network').replace('DSC','Discovery').replace('Discovery ','Discovery').replace('BRAVO','Bravo').replace('SYFY','Syfy').replace('HISTORY','History').replace('NATIONAL GEOGRAPHIC','National Geographic')
    string = string.replace('COMEDY','Comedy Central').replace('FOOD','Food Network').replace('NIK','Nickelodeon').replace('LIFE','Lifetime').replace('SPIKETV','SPIKE TV').replace('FNC','Fox News').replace('NGC','National Geographic').replace('Channel','')
    return cleanChannel(string)
#####################################################################################################
def cleanChannel(string):
    string = string.replace('WLYH','CW').replace('WHTM','ABC').replace('WPMT','FOX').replace('WPSU','PBS').replace('WHP','CBS').replace('WGAL','NBC').replace('My9','MY9').replace('AETV','AE').replace('USA','USA Network').replace('Channel','').replace('Network Network','Network')
    return string.strip()
#####################################################################################################
def Login():
	Dict['token'] = ""
	username = Prefs["username"]
	password = Prefs["password"]
	cj = cookielib.CookieJar()
	opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
	opener.addheaders = [('User-agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US) AppleWebKit/533.4 (KHTML, like Gecko) Chrome/5.0.375.127 Large Screen Safari/533.4 GoogleTV/162671')]
	urllib2.install_opener(opener)
	url = build_json('gtv/1/live/login', {'username': username,
										   'password': password,
										   'device':'gtv',
										   'redir':'0'})
	response = opener.open(url)
	for cookie in cj:
		if cookie.name == 'token':
			Dict['token'] = (cookie.value)
			return True
	return False