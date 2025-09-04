# http://www.mila.cs.technion.ac.il/tools_token.html
# https://github.com/NLPH/NLPH_Resources

codepath = '/Users/drosen/Dropbox/code/anki-assimil'
os.chdir(codepath)

import csv
import hebtokenizer

import mutagen
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2
from mutagen.easyid3 import EasyID3

wordlist = [line.rstrip('\n') for line in open('wordlist.txt')]

import shutil
import os
mediafolder = "/Users/drosen/Desktop/anki-media-import"
basedirectory = "/Users/drosen/Desktop/assimil course"
alldirs = os.listdir(basedirectory)
dirs = [i for i in alldirs if i.startswith('L')]
dirs.sort()
rows = []
for d in dirs[:20]:
    directory = os.path.join(basedirectory, d)
    print(directory)
    filelist = os.listdir(directory)
    translateTitle = 'T00-TRANSLATE.mp3'
    if translateTitle in filelist:
        filelist.remove(translateTitle)
    filelist.sort()
    for filename in filelist:
        fname = os.path.join(directory, filename)
        #print(fname)
        audio = MP3(fname, ID3=EasyID3)
        #print(audio['title'][0].split('-'))
        lesson = audio['album'][0].split(' - ')[-1]
        lessonNum = lesson[2:]
        lessonTag = 'assimil-' + lessonNum
        split_title = audio['title'][0].split('-')
        hebrew_text = split_title[-1] #.rstrip('٭')
        id = '.'.join([lesson, split_title[0]])
        tags = ' '.join(['assimil', lessonTag])
        #print(lesson, split_title[0], hebrew_text )
        newfname = '.'.join([id,'mp3'])
        newfullpath = os.path.join(mediafolder,newfname)
        #print(newfullpath)
        shutil.copyfile(fname, newfullpath)
        row = {'id':id, 'hebrew':hebrew_text,
               'english':'NA', 'sound':''.join(['[sound:',newfname,']']),
               'tags': tags}
        rows.append(row)

dest_filename = 'assimil-init.csv'
fieldnames = ['id', 'hebrew', 'english', 'sound', 'tags']
with open(dest_filename, 'w', newline='') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)


dest_filename = 'assimil-init.csv'
with open(dest_filename, 'w', newline='', encoding='utf-8') as csv_file:
    writer = csv.writer(csv_file, delimiter=',')
    writer.writerows(rows)


import csv
fieldnames = ['id', 'hebrew', 'english', 'sound', 'tags']
with open('assimil.csv', newline='') as csvfile:
    reader = csv.DictReader(csvfile, fieldnames=fieldnames)
    for row in reader:
        
        print(row)

