#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import requests
from requests.auth import HTTPBasicAuth, HTTPDigestAuth
import shutil
import re
from datetime import datetime

# Auth Scheme Mapping for Requets
AUTH_MAP = {
    'basic': HTTPBasicAuth,
    'digest': HTTPDigestAuth,
}

#s = requests.Session()

def auth_get(url, *args, **kwargs):
    r = requests.get(url, **kwargs)

    if r.status_code != 401:
        return r

    auth_scheme = r.headers['WWW-Authenticate'].split(' ')[0]
    auth = AUTH_MAP.get(auth_scheme.lower())

    if not auth:
        raise ValueError('Unknown authentication scheme')

    r = requests.get(url, auth=auth(*args), **kwargs)

    return r

# Cam Specific Parameters
cam_url = '10.1.1.5'
cam_id  = 'GardenCam'
cam_usr = 'admin'
cam_pwd = 'admin'

r = auth_get('http://{}/cgi-bin/storageDevice.cgi?action=getDeviceAllInfo'.format(cam_url), cam_usr, cam_pwd)
if r.status_code == 200:
    data = r.text.split('\r\n')
    for line in data:
       if 'Path' in line:
           Path = line.split('=')[1].strip()
       elif 'Name' in line:
           Name = line.split('=')[1].strip()
       elif 'TotalBytes' in line:
           TotalBytes = float(line.split('=')[1])
       elif 'UsedBytes' in line:
           UsedBytes = float(line.split('=')[1])
       elif 'IsError' in line:
           IsError = bool(line.split('=')[1].strip().lower() == 'true')
else:
    r.raise_for_status()

PercentUsed = round((UsedBytes / TotalBytes) * 100.0, 1)
#TotalGB = round((TotalBytes / 1000000000.0), 2)
#print('Storage: {}% of {} GB used in Path {}'.format(PercentUsed, TotalGB, Path))
TotalMB = round((TotalBytes / 1024.0 / 1024.0), 1)
print('Storage: {}% of {} MB used in Path {}'.format(PercentUsed, TotalMB, Path))


# Input Arguments:
#Flags  = ['Timing', 'Manual', 'Marker', 'Event', 'Mosaic', 'Cutout']
#Event  = ['AlarmLocal', 'VideoMotion', 'VideoLoss', 'VideoBlind', 'Traffic*']
# Channel
channel = 0
# Set Type to either 'mp4' or 'jpg'
type    = 'mp4'
#type    = 'jpg'
# Start and End Time
#today = datetime.today()
#start_date = '{:4}-{:02}-{:02} 00:00:01'.format(today.year, today.month, today.day)
start_date = '2019-11-11 00:00:01'
end_date   = '2019-11-11 23:59:59'


count = 100
items = []

# Create a mediaFileFinder
r = auth_get('http://{}/cgi-bin/mediaFileFind.cgi?action=factory.create'.format(cam_url), cam_usr, cam_pwd)
if r.status_code == 200:
    data = r.text.split('\r\n')
    factory = data[0].split('=')[1]

    # Start findFile
    r = auth_get('http://{}/cgi-bin/mediaFileFind.cgi?action=findFile&object={}&condition.Channel={}&condition.StartTime={}&condition.EndTime={}&condition.Types[0]={}'.format(cam_url, factory, channel, start_date, end_date, type), cam_usr, cam_pwd)
    success = (r.text == 'OK\r\n')

    # findNextFile
    while success:
        r = auth_get('http://{}/cgi-bin/mediaFileFind.cgi?action=findNextFile&object={}&count={}'.format(cam_url, factory, count), cam_usr, cam_pwd)
        if r.status_code == 200:
            data = r.text.split('\r\n')
            numitems = int(data[0].split('=')[1])

            if numitems > 0:
                # Ignore first and last line for calculation of item length
                numkeys = int((len(data) - 2) / numitems)
            else:
                numkeys = 0

            item = {}
            for line in data[1:-1]:
               #if 'FilePath' in line:
               #    item['FilePath'] = line.split('=')[1].decode()
               #elif 'Length' in line:
               #    item['Length'] = int(line.split('=')[1].decode())
               #elif 'StartTime' in line:
               #    item['StartTime'] = line.split('=')[1].decode()
               #elif 'EndTime' in line:
               #    item['EndTime'] = line.split('=')[1].decode()
               #elif 'Flags[0]' in line:
               #    item['Flag'] = line.split('=')[1].decode()
               #elif 'Events[0]' in line:
               #    item['Event'] = line.split('=')[1].decode()
               item.update({k: v for k,v in re.findall(r'items\[\d*\]\.(\S*)=(.*)', line)})
               #if len(item) == 6:
               if len(item) == numkeys:
                   items.append(item)
                   item = {}
        if r.status_code != 200 or numitems == 0:
            if r.status_code != 200:
                print('Unexpected Status: {}'.format(r.status_code))
                r.raise_for_status()
            break

    print('{} items found'.format(len(items)))

    # Close and destroy the mediaFIleFinder
    r = auth_get('http://{}/cgi-bin/mediaFileFind.cgi?action=close&object={}'.format(cam_url, factory), cam_usr, cam_pwd)
    r = auth_get('http://{}/cgi-bin/mediaFileFind.cgi?action=destroy&object={}'.format(cam_url, factory), cam_usr, cam_pwd)

calyear = 2019
calmonth = 11
#for week in list(calendar.monthcalendar(calyear,calmonth)):
#    # week sequence is Mon, Tue, Wed, Thu, Fri, Sat, Sun
#    for day in week:
#        # day is actual day of month or zero
#        print day
# or weeks_of_month = list(calendar.monthcalendar(calyear,calmonth))
# week_of_month = weeks_of_month[0..5]
# day_of_month = weeks_of_month[0..5][0..6] = list(calendar.monthcalendar(calyear,calmonth))[0..5][0..6]

# Handle the results
for index, item in enumerate(items):
    try:
        cmd = 'http://{}/cgi-bin/RPC_Loadfile{}'.format(cam_url, item['FilePath'])
        #cmd = 'rtsp://{}{}'.format(cam_url, item['FilePath'])

        #print('{}\t{}\t{}: {}'.format(index + 1, item['StartTime'].split()[1], item['Flag'], item['Event']))
        print('{}\t{} - {}\t{}: {}'.format(index + 1, item['StartTime'].split()[1], item['EndTime'].split()[1], item['Flags[0]'], item['Events[0]']))
        #print('Start Time:\t {}'.format(item['StartTime']))
        #print('End Time:\t {}'.format(item['EndTime']))
        #print('File Size:\t {}(KB)'.format(int(round(int(item['Length'])/1024.0, 0))))

        #filename = /mnt/sd/2019-11-11/001/dav/21/21.40.47-21.41.33[M][0@0][0].mp4
        #parts = cmd.split(os.path.sep)
        #outname = '{}_{}_{}.{}'.format(cam_id, parts[-5], parts[-1][:8], parts[-1][-3:])


        #r = auth_get(cmd, cam_usr, cam_pwd)
        #if r.status_code == 200:
        #    #r.raw.decode_content = True
        #    with open('-'.join(cmd.split(os.path.sep)[-6:]), 'wb') as out:
        #        out.write(r.content)
        #        #shutil.copyfileobj(r.raw, out)
    except:
       continue
