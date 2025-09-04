
import csv
fieldnames = ['id', 'hebrew', 'english', 'sound', 'tags']
with open('assimil.csv', newline='') as csvfile:
    reader = csv.DictReader(csvfile, fieldnames=fieldnames)
    for row in reader:
        print(row)






###
import mutagen
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2
from mutagen.easyid3 import EasyID3

import shutil
import os
directory = "/Users/drosen/Desktop/assimil course/L018-Hebrew ASSIMIL"
mediafolder = "/Users/drosen/Desktop/anki-media-import"
rows = []
for filename in os.listdir(directory):
    fname = os.path.join(directory, filename)
    #print(fname)
    audio = MP3(fname, ID3=EasyID3)
    #print(audio['title'][0].split('-'))
    lesson = audio['album'][0].split(' - ')[-1]
    split_title = audio['title'][0].split('-')
    hebrew_text = split_title[-1] #.rstrip('٭')
    id = '.'.join([lesson, split_title[0]])
    tags = ' '.join(['assimil', lesson])
    #print(lesson, split_title[0], hebrew_text )
    newfname = '.'.join([id,'mp3'])
    newfullpath = os.path.join(mediafolder,newfname)
    shutil.copyfile(fname, newfullpath)
    row = (id, hebrew_text, 'hebrew translation', ''.join(['[sound:',newfname,']']), tags )
    rows.append(row)

import csv

with open('/Users/drosen/Desktop/assimil.csv', 'w', newline='', encoding='utf-8') as csv_file:
    writer = csv.writer(csv_file, delimiter=';')
    writer.writerows(rows)


with open('/Users/drosen/Desktop/assimil.csv', 'w', newline='', encoding='utf-8') as csv_file:
    writer = csv.writer(csv_file, delimiter=';')
    writer.writerows(rows)

#  cp  ~/Desktop/anki-media-import/* '/Users/drosen/Library/Application Support/Anki2/User 1/collection.media/'
# media folder: /Users/drosen/Library/Application\ Support/Anki2/User\ 1/collection.media

