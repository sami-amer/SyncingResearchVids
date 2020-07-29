# CODE FOR METADATA EXTRACTION
## ffmpeg -i input.mp4 -c copy -map_metadata 0 -map_metadata:s:v 0:s:v -map_metadata:s:a 0:s:a -f ffmetadata output.txt
import subprocess
import os
import pandas as pd
import pytesseract
from PIL import Image
import re
import cv2
import numpy as np

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
    try:
        text  = pd.read_csv('output.txt', sep = '=',index_col= 0)
    except:
        print('Error in video!')
        return None
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
    # im1.show()
    ret,img = cv2.threshold(np.array(im1), 125, 255, cv2.THRESH_BINARY)
    img = Image.fromarray(img.astype(np.uint8))
    width, height = img.size[0], img.size[1]
    img = img.resize((500,int((500)/width * height)),Image.ANTIALIAS)
    ocr_result = pytesseract.image_to_string(img, lang='eng',config='--psm 10 --oem 3 -c tessedit_char_whitelist=0123456789-:.')
    # img.show()
    os.remove('frame.jpg')
    # print(ocr_result)
    #insert code to split up timecode
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
    compTime1 = float(time1[1]) * 60 + float(time1[2])
    compTime2 = float(time2[1])*60 + float(time2[2])
    timeshift = (compTime1 - compTime2)
    if timeshift < 0:
        syncedTime = datetime1[1]
        timeshift= abs(timeshift)
    else:
        syncedTime = datetime2[1]
    return syncedTime, timeshift

def get_time_diff_multiple(dateTimes):
    #Assert all of these happens on the same day
    testTime = dateTimes[0][0]
    dayStatus = [True if n[0] == testTime else False for n in dateTimes]
    if False in dayStatus:
        print('Some of these videos happen on different days!')
        return None
    compTimes = [float((n[1].split(':'))[1])*60 + float((n[1].split(':'))[2]) for n in dateTimes]
    setTime = max(compTimes)
    timeShifts = [setTime - n for n in compTimes]
    return timeShifts

def shift_by(video,time,output):
    # Code to crop start
    ## ffmpeg -i in.mp4 -ss 64 -c:v libx264 out.mp4
    # Code to add black frames
 
    # ffmpeg -i test.mp4 -f lavfi -i "color=c=black:s=640x480:r=25:sar=0/1" -filter_complex \
    # "[0:v] setpts=PTS-STARTPTS [main]; \
    # [1:v] trim=end=10,setpts=PTS-STARTPTS [pre]; \
    # [1:v] trim=end=30,setpts=PTS-STARTPTS [post]; \
    # [pre][main][post] concat=n=3:v=1:a=0 [out]" \
    # -map "[out]" -vcodec mpeg2video -maxrate 30000k -b:v 30000k output.mp4
    subprocess.call([
        'ffmpeg',
        '-i',
        video,
        '-ss',
        str(time),
        '-c:v',
        'libx264', #can't be copy, the times are off by too much i think. can be tested per machine.
        '-c:a',
        'aac',
        output
    ])

def add_black_frames(video,before,after,res,output):
    ## add support for multiple ratios and resolutions
    ## 
    # ffmpeg -i input -f lavfi -i "color=c=black:s=720x576:r=25:sar=1023/788" -filter_complex \
    # "[0:v] setpts=PTS-STARTPTS [main]; \
    #  [1:v] trim=end=10,setpts=PTS-STARTPTS [pre]; \
    #  [1:v] trim=end=30,setpts=PTS-STARTPTS [post]; \
    #  [pre][main][post] concat=n=3:v=1:a=0 [out]" \
    # -map "[out]" -vcodec mpeg2video -maxrate 30000k -b:v 30000k output.mpg
    
    subprocess.call([
        'ffmpeg', '-i', video, '-f', 'lavfi','-i', 'color=c=black:s='+res+':r=30:sar=1/1','-filter_complex','[0:v] setpts=PTS-STARTPTS [main]; [1:v] trim=end='+ str(before) +',setpts=PTS-STARTPTS [pre]; [1:v] trim=end='+str(after)+',setpts=PTS-STARTPTS [post]; [pre][main][post] concat=n=3:v=1:a=0 [out]','-map','[out]', 
        '-vcodec', 'libx264', '-maxrate', '30000k', '-b:v', '30000k', 'tempVid.mp4'
    ])
    # ffmpeg -i input-video.mp4 output-audio.mp3
    subprocess.call([
        'ffmpeg', '-i',video,'tempAud.m4a'
    ])
    # ffmpeg -i in.avi -i audio.wav -filter_complex"[1]adelay=62000|62000[aud];[0][aud]amix" -c:v copy out.avi
    audioShift = before * 1000
    subprocess.call([
        'ffmpeg','-i','tempVid.mp4','-i','tempAud.m4a', '-filter_complex','[1] adelay='+str(audioShift)+'|'+str(audioShift)+',aformat=sample_fmts=fltp:sample_rates=48000 [aud]','-map', '[aud]','-map','0:v','-c:v','copy',output
    ])
    os.remove('tempAud.m4a')
    os.remove('tempVid.mp4')
def get_res(video):
    # ffprobe -v error -show_entries stream=width,height -of csv=p=0:s=x input.m4v
    result = subprocess.run(['ffprobe','-v','error','-show_entries', 'stream=width,height', '-of','csv=p=0:s=x',video],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT)
    return result.stdout.decode('utf-8').rstrip()

def get_length(filename):
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                             "format=duration", "-of",
                             "default=noprint_wrappers=1:nokey=1", filename],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT)
    return float(result.stdout)

def line_up_GOPR(vid,gopr,output,gopro = True):
    vidTime = get_timecode(vid)
    if gopro:
        goprTime = get_creation_time(gopr)
    else:
        goprTime = get_timecode(gopr)
    print(goprTime,vidTime)
    begBlack, startTime = get_time_diff(vidTime,goprTime)[1], get_time_diff(vidTime,goprTime)[0]  # check which starts first
    print(begBlack)
    print(startTime)
    if startTime == vidTime[1]:
        endBlack = get_length(vid)-get_length(gopr)-begBlack
        res = get_res(gopr)
        add_black_frames(gopr,begBlack,endBlack,res,output)
        print('vid')
    elif startTime == goprTime[1]:
        endBlack = 0
        print('gopr')
        # add_black_frames(vid,begBlack,endBlack)
        shift_by(gopr,begBlack,output)


def convert_csv_to_srt(csv,output):
    csv = pd.read_csv(csv)
    with open(output,'w+') as f:
        for row in csv.iterrows():
            elapsed_time = (row[1]['elapsed_time']).split(' ')[2].split('.')[0]+',00'
            speaker = (row[1]['speaker'])
            number = row[0] + 1 #srt is not 0 index
            content = row[1]['content']
            try:
                end_time = (csv.loc[row[0]+1]['elapsed_time']).split(' ')[2].split('.')[0]+',00'
            except:
                print('last line')
            if elapsed_time == end_time:
                secLater = int(elapsed_time.split(':')[2][0:2]) + 1
                if secLater < 60:
                    if secLater < 10:
                        secLater = '0'+str(secLater)
                    end_time = elapsed_time[0:6]+str(secLater)+',00'
                else:
                    minLater = int(elapsed_time.split(':')[1][0:2]) + 1
                    if minLater < 10:
                        minLater = '0'+str(minLater)
                    # print(minLater)
                    secLater = secLater - 60
                    if secLater < 10:
                        secLater = '0'+str(secLater)
                    end_time = elapsed_time[0:3] + str(minLater)+':'+str(secLater)+',00'
            f.write(str(number)+'\n'+elapsed_time+'-->'+end_time+'\n'+speaker+': '+content+'\n\n')

def line_up(main, vid2, vid3, parentList, childList):
    convert_csv_to_srt(main,'main.srt')
    line_up_GOPR(main,vid2,'vid2.mp4',False)
    line_up_GOPR(main,vid3,'vid3.mp4',False)
    for i,vid in enumerate(parentList):
        line_up_GOPR(main,vid,'parent'+str(i+1)+'.mp4')
    for i, vid in enumerate(childList):
        line_up_GOPR(main,vid,'child'+str(i+1)+'.mp4')

def cut_to_story(annotation):
    csv = pd.read_csv(annotation)
    toCut = 0
    for row in csv.iterrows():
        if (row[1]['Storyreading']) == 1:
            toCut = row[0] * 5
            break
    shift_by(main,toCut,'main.mp4')

if __name__ == "__main__":
    # add_black_frames('Resources/videos/test.mp4',10,30)
    # get_res(None)
    # print(get_length('Resources/videos/test.mp4'))
    # line_up_GOPR('Resources/videos/p01_s1_vid__parent_annotation_2019-03-06-11-36-09.mp4','Resources/First_Person_Videos/Child/GP014636.MP4')
    # print(get_res('Resources/First_Person_Videos/Child/GP014636.MP4'))
    # TODO: make a wrapper that detects which video needs what
    # make it possible to detect if a vid is before start, then change technique
    # convert_csv_to_srt('Resources/Rev_transcription (dialogic reading)/p01_s1_vid_parent_annotation_2019-03-06-11-36-09.csv','p01_s1_vid__parent_annotation_2019-03-06-11-36-09.srt')
    # line_up_GOPR('Resources/videos/p01_s1_vid__parent_annotation_2019-03-06-11-36-09.mp4','Resources/videos/p01_s1_vid2_2019-03-06-11-36-09.mp4','2.mp4',False)
    # line_up_GOPR('Resources/videos/p01_s1_vid__parent_annotation_2019-03-06-11-36-09.mp4','Resources/videos/p01_s1_vid3_2019-03-06-11-36-09.mp4','3.mp4',False)
    # line_up_GOPR('Resources/videos/p01_s1_vid__parent_annotation_2019-03-06-11-36-09.mp4','Resources/First_Person_Videos/Parent/GOPR1042.MP4','parent.mp4')
    # line_up_GOPR('Resources/videos/p01_s1_vid__parent_annotation_2019-03-06-11-36-09.mp4','Resources/First_Person_Videos/Child/GP014636.MP4','child.mp4')
    # line_up_GOPR('Resources/videos/p01_s1_vid__parent_annotation_2019-03-06-11-36-09.mp4','Resources/GOPR1043-003.MP4','parent2.mp4')
    # line_up_GOPR('Resources/videos/p01_s1_vid__parent_annotation_2019-03-06-11-36-09.mp4','Resources/GOPR4636-004.MP4','child2.mp4')
    # cut_to_story('Resources/video data labeling /parent-child(affect-labels)-april9/p01_s1_vid_parent_annotation_2019-03-06-11-36-09_Kaitlin_2020-01-13 10_55_52.csv')
    pass

