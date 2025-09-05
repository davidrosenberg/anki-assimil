from queue import PriorityQueue
from nltk.tokenize import TweetTokenizer
import string
import Levenshtein
import hebtokenizer
import csv

tknzr = TweetTokenizer()
wordlist = [line.rstrip('\n') for line in open('wordlist.txt')]

# Load all words from anki
anki_heb = {}
anki_eng_heb = {}
headers = ['Hebrew','Definition','Gender','PartOfSpeech'
           ,'Shoresh','Audio','Inflections','Extended','Image','Tags']
with open('alldecks.txt') as tsvfile:
  reader = csv.DictReader(tsvfile, fieldnames=headers, dialect='excel-tab')
  for row in reader:
    anki_heb[row['Hebrew']] = row
    t = tknzr.tokenize(row['Definition'])
    defs = [b for b in t if b not in string.punctuation]
    for eng_word in defs:
        if eng_word in anki_eng_heb.keys():
            anki_eng_heb[eng_word].append(row['Hebrew'])
        else:
            anki_eng_heb[eng_word] = [row['Hebrew']]
anki_eng_heb['the']=[]
anki_eng_heb['is']=[]
anki_eng_heb['a']=[]
anki_eng_heb['in']=[]

## Read english translations
heb_eng_keys = []
heb_eng_dict = {}
fieldnames = ['id', 'hebrew', 'english', 'sound', 'tags']
#with open('assimil-init.csv', newline='') as csvfile:
with open('assimil.csv', newline='') as csvfile:
    reader = csv.DictReader(csvfile)#, fieldnames=fieldnames)
    for row in reader:
      if row['english'] is not 'NA':
        heb_eng_keys.append(row['id'])
        heb_eng_dict[row['id']] = row

def add_word(first_match, anki_word, lesson):
  if anki_word in first_match:
    prev_lesson = first_match[anki_word]
    print("Found ", anki_word, prev_lesson," current lesson: ",lesson)
    if lesson < prev_lesson:
      first_match[anki_word] = lesson
  else:
    print("New word ", anki_word," current lesson: ",lesson)
    first_match[anki_word] = lesson
  return first_match

## Read word matches we've got so far
first_match = {}
word_matches = []
with open('assimil-words.csv', newline='') as csvfile:
    reader = csv.DictReader(csvfile)#, fieldnames=fieldnames)
    for row in reader:
      word_matches.append(row)
      lesson = row['id'].split('.')[0][2:]
      anki_word = row['match_word']
      first_match = add_word(first_match, anki_word, lesson)

## Add in extra words
with open('assimil-words-extra.csv', newline='') as csvfile:
    reader = csv.DictReader(csvfile)#, fieldnames=fieldnames)
    for row in reader:
      lesson = row['Lesson']
      anki_word = row['AnkiID']
      first_match = add_word(first_match, anki_word, lesson)

## Generate anki tag update file for words
with open('assimil-tag-update.csv', 'w', newline='') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=headers)
    writer.writeheader()
    for word in first_match:
      if word in anki_heb.keys():
        row = anki_heb[word]
        level = first_match[word]
        row['Tags'] = row['Tags'] + ' assimil-' + level
        writer.writerow(row)
      else:
        print("WORD NOT FOUND!!!")

## Generate init file for word matches
newrows = []
for key in heb_eng_keys:
  row = heb_eng_dict[key]
  row_type = row['id'].split('.')[1][0]
  if (row_type == 'T'):
    continue

  tokenized = hebtokenizer.tokenize(row['hebrew'])
  words = [c for (b,c) in tokenized if b=='HEB']

  # get all vocabulary matches
  for word in words:
    pq = PriorityQueue()
    print(word)
    for w in wordlist:
      d = Levenshtein.distance(word, w)
      if d<=5:
        pq.put((d, w))
    num_to_get = 2
    num = 0
    while (not pq.empty() and num < num_to_get):
      d,w = pq.get()
      num += 1
      newrow = {'id': row['id'],
                'eng_text': row['english'],
                'heb_word': word, 'match_word': w,
                'match_word_def': anki_heb[w]['Definition'],
                'Levensht': d}
      newrows.append(newrow)

with open('assimil-words-init.csv', 'w', newline='') as csvfile:
    fieldnames = ['id','eng_text', 'heb_word', 'match_word', 'match_word_def', 'Levensht']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(newrows)

all_seen_words = []
newrows = []
for row in rows:
    row_type = row['id'].split('.')[1][0]
    if (row_type == 'T'):
        continue

    t = tknzr.tokenize(row['english'])
    english_words = [b for b in t if b not in string.punctuation]

    # get all vocabulary matches
    hebrew_candidates = []
    for w in english_words:
        if w in  anki_eng_heb.keys():
            hebrew_candidates.extend(anki_eng_heb[w])

    ## For each English word of translation, look up in anki

    tokenized = hebtokenizer.tokenize(row['hebrew'])
    words = [c for (b,c) in tokenized if b=='HEB']
    word_refs = []
    unknown_words = []
    seen_words = []
    possible_matches = []
    for word in words:
        if (word in all_seen_words):
            seen_words.append(word)
        else:
            all_seen_words.append(word)
            if word in wordlist:
                word_refs.append(word)
            else:
                unknown_words.append(word)
            for h in hebrew_candidates:
                d = Levenshtein.distance(h, word)
                possible_matches.append((d, word, h))

    row['word_refs'] = ','.join(word_refs)
    row['unknown_words'] = ','.join(unknown_words)
    row['seen_words'] = ','.join(seen_words)
    newrows.append(row)
import csv

with open('assimil-words.csv', 'w', newline='') as csvfile:
    fieldnames = ['id', 'hebrew', 'english', 'word_refs', 'unknown_words', 'seen_words', 'tags', 'sound']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(newrows)

    for row in rows:
        writer.writerow(row)

import csv
fieldnames = ['id', 'hebrew', 'english', 'sound', 'tags']
with open('assimil.csv', newline='') as csvfile:
    reader = csv.DictReader(csvfile, fieldnames=fieldnames)
    for row in reader:

        print(row)

##
Need to add these translations in:
L020.T01,בסוף שבוע אתם שוחים בים.٭,NA,[sound:L020.T01.mp3],assimil assimil-20
L020.T02,אנחנו הולכים לברכה עם חברים.٭,NA,[sound:L020.T02.mp3],assimil assimil-20
L020.T03,בערב אנחנו אוכלים על האש.٭,NA,[sound:L020.T03.mp3],assimil assimil-20
L020.T04,למה הם מדברים על פוליטיקה?٭,NA,[sound:L020.T04.mp3],assimil assimil-20
L020.T05,בבוקר אנחנו מפטפטים בטלפון.٭,NA,[sound:L020.T05.mp3],assimil assimil-20
