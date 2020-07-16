# CODE FOR METADATA EXTRACTION
## ffmpeg -i input.mp4 -c copy -map_metadata 0 -map_metadata:s:v 0:s:v -map_metadata:s:a 0:s:a -f ffmetadata output.txt
import subprocess
import os
import pandas as pd
import pytesseract
from PIL import Image
import re

def get_creation_time(file_name):
    subprocess.call([
        'ffmpeg',
        '-i',
        file_name,
        '-c',
        'copy',
        '-map_metadata',
        '0',
        '-map_metadata:s:v',
        '0:s:v',
        '-map_metadata:s:a',
        '0:s:a',
        '-f',
        'ffmetadata',
        'output.txt']
    )
    text  = pd.read_csv('output.txt', sep = '=',index_col= 0)
    time = (text.loc['creation_time'][0])
    os.remove('output.txt')
    time = time.split('T')
    date, time = time[0], time[1]
    time = time.replace('Z','')
    return date, time

# CODE FOR FRAME EXTRACTION
## ffmpeg -i input.mp4  -ss 0 -frames 1 -r 1 -f image2 frame%03d.jpeg

def get_first_frame(file_name, output):
    subprocess.call([
        'ffmpeg',
        '-i',
        file_name,
        '-ss',
        '0',
        '-frames',
        '1',
        '-r',
        '1',
        '-f',
        'image2',
        output
    ])

def get_timecode(file_name):
    get_first_frame(file_name, 'frame.jpg')
    im = Image.open('frame.jpg')
    w, h = im.size
    right = w * 4/10
    bottom = h * 1/15
    im1 = im.crop((0,0,right,bottom))
    ocr_result = pytesseract.image_to_string(im1, lang='eng',config='--psm 10 --oem 3 -c tessedit_char_whitelist=0123456789-:.')
    os.remove('frame.jpg')
    ## insert code to split up timecode
    ocr_result = re.split('[:-]',ocr_result)
    date = ocr_result[0][-4:] + '-' + ocr_result[1]+'-' + ocr_result[2][0:2]
    time = ocr_result[2][-2:] + ':' + ocr_result[3] + ':' + ocr_result[4][0:2]
    return date, time

def get_time_diff(datetime1,datetime2):
    date1, time1 = datetime1[0], datetime1[1]
    date2, time2 = datetime2[0], datetime2[1]
    time1, time2 = time1.split(':'), time2.split(':')
    # step 1: assert that it is the same date.
    if date1 != date2:
        print('These clips happened on different days!')
        return None
    # step 2: find which one is the later timestamp (and thus the timestamp to remain unchanged)
    # only checks hour for issues, they should be the same
    if time1[0] != time2[0]:
        print('The videos are off by an hour. This doesnt make sense, and is probably due to daylight savings issues')
        return None
    compTime1 = float(time1[1]) * 60 + float(time1[2])
    compTime2 = float(time2[1])*60 + float(time2[2])
    timeshift = (compTime1 - compTime2)
    if timeshift < 0:
        syncedTime = datetime2[1]
        timeshift= abs(timeshift)
    else:
        syncedTime = datetime1[1]
    return syncedTime, timeshift

    
if __name__ == "__main__":
    dt1 = (get_creation_time('test.LRV'))
    # get_frames('vid1.mp4','1')
    dt2 = get_timecode('vid1.mp4')
    print(get_time_diff(dt1,dt2))
