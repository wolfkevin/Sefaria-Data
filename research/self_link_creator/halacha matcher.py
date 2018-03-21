# -*- coding: utf-8 -*-
import os
import json
import csv
import re

filepath = './shulchan arukh/Shulchan Arukh, Orach Chayim - he - Wikisource Shulchan Aruch.json'
fileoutpath = 'Shulchan Arukh, Orach Chayim_output.csv'
he_ref = u'שלחן עורך, אורח חיים'  # hebrew name of referenced text

self_ref_words = [u'קמן',  u'עיל', u'הלן', u'עיין', u'ע\"ל']
siman_words = [u"סי'", u'סימן', u'ס\"ס']
position_words = [u'ס\"ס', u'ריש', u'סוף']
seif_words = [u'סעיף', u"ס''"]

gematria = {}
gematria[u'א'] = 1
gematria[u'ב'] = 2
gematria[u'ג'] = 3
gematria[u'ד'] = 4
gematria[u'ה'] = 5
gematria[u'ו'] = 6
gematria[u'ז'] = 7
gematria[u'ח'] = 8
gematria[u'ט'] = 9
gematria[u'י'] = 10
gematria[u'כ'] = 20
gematria[u'ל'] = 30
gematria[u'מ'] = 40
gematria[u'נ'] = 50
gematria[u'ס'] = 60
gematria[u'ע'] = 70
gematria[u'פ'] = 80
gematria[u'צ'] = 90
gematria[u'ק'] = 100
gematria[u'ר'] = 200
gematria[u'ש'] = 300
gematria[u'ת'] = 400


def getGematria(txt):
    if not isinstance(txt, unicode):
        txt = txt.decode('utf-8')
    index = 0
    sum = 0
    while index <= len(txt) - 1:
        if txt[index:index + 1] in gematria:
            sum += gematria[txt[index:index + 1]]

        index += 1
    return sum


def isGematria(txt):
    txt = re.sub('[\', ":.\n)]', '', txt)
    if txt.find("טו") >= 0:
        txt = txt.replace("טו", "יה")
    elif txt.find("טז") >= 0:
        txt = txt.replace("טז", "יו")

    while txt[0] == u'ת':
        txt = txt[1:]

    if len(txt) == 1:
        if txt[0] < u'א' or txt[0] > u'ת':
            return False
    elif len(txt) == 2:
        if txt[0] < u'י' or (txt[0] < u'ק' and txt[1] > u'ט'):
            return False
    elif len(txt) == 3:
        if txt[0] < u'ק' or txt[1] < u'י' or txt[2] > u'ט':
            return False
    else:
        return False

    return True


def numToHeb(engnum=u""):
        engnum = str(engnum)
        numdig = len(engnum)
        hebnum = u""
        letters = [[u"" for i in range(3)] for j in range(10)]
        letters[0]=[u"", u"א", u"ב", u"ג", u"ד", u"ה", u"ו", u"ז", u"ח", u"ט"]
        letters[1]=[u"", u"י", u"כ", u"ל", u"מ", u"נ", u"ס", u"ע", u"פ", u"צ"]
        letters[2]=[u"", u"ק", u"ר", u"ש", u"ת", u"תק", u"תר", u"תש", u"תת", u"תתק"]
        if (numdig > 3):
            print "We currently can't handle numbers larger than 999"
            exit()
        for count in range(numdig):
            hebnum += letters[numdig-count-1][int(engnum[count])]
        hebnum = re.sub(u'יה', u'טו', hebnum)
        hebnum = re.sub(u'יו', u'טז', hebnum)
        return hebnum


def getRidOfSofitAndDash(txt):
    if txt == None:
        print "pause"
    txt = re.sub('[\', ":.\n)]', '', txt)
    if txt.find("ך") >= 0:
        txt = txt.replace("ך", "כ")
    if txt.find("ם") >= 0:
        txt = txt.replace("ם", "מ")
    if txt.find("ף") >= 0:
        txt = txt.replace("ף", "פ")
    if txt.find("ץ") >= 0:
        txt = txt.replace("ץ", "צ")
    return txt


def isContinuationLink(siman_1, siman_2):
    siman_2 = getRidOfSofitAndDash(siman_2)
    return (getGematria(getRidOfSofitAndDash(siman_1)) + 1 ==
            getGematria(siman_2)) and isGematria(siman_2)


def addMultipleSimanim(self_links_t, words, offset, klal_index, klal_link_num):
    # sometimes links to multiple simanim, so get all of them

    continuation_link = None
    siman_link = words[offset]

    while len(words) > offset + 1:

        if isContinuationLink(words[offset], words[offset + 1]):
            offset += 1
            continuation_link = words[offset]

        elif u'וסי' in words[offset + 1]:
            if isContinuationLink(words[offset], words[offset + 2]):
                continuation_link = words[offset + 2]

            else:
                self_links_t.append(createLinkInsert(klal_index + offset, klal_link_num, siman_link, continuation_link))
                siman_link = words[offset + 2]

            offset += 2

        elif words[offset + 1][0] == u'ו' and isContinuationLink(words[offset], words[offset + 1][1:]):
            offset += 1
            continuation_link = words[offset][1:]

        else:
            break

    self_links_t.append(createLinkInsert(klal_index + offset, klal_link_num, siman_link, continuation_link))
    return


def isSiman(siman_word, siman_num):
    return any(sim in siman_word for sim in [u'דין', u"סי'", u'סימן']) \
           and isGematria(siman_num) \
           and getGematria(siman_num) < 58


def isRegularReference(word, comment_words, klal_index):
    return u'כלל' in word \
           and len(comment_words[klal_index:]) > 3 \
           and isSiman(comment_words[klal_index + 2], comment_words[klal_index + 3])


def isReferenceToPreviousOrUpcoming(word, comment_words, klal_index):
    return (u'קמן' in word or u'עיל' in word) \
           and len(comment_words[klal_index:]) > 2 \
           and (not (u'כלל' in comment_words[klal_index + 1])) \
           and isSiman(comment_words[klal_index + 1], comment_words[klal_index + 2])


def isReferenceToAnotherWork(comment_words, klal_index):
    return any(word in comment_words[klal_index - 1] for word in [u'אדם', u'נ"א', u'ח"א', u'ש"א', u'ת"ח']) \
           or ((len(comment_words[klal_index:]) > 4) and (u'נ"א' in comment_words[klal_index + 4]))


def referencesChelekBet(comment_words, klal_index):
    return any(word in comment_words[klal_index - 1] for word in [u"שבת", u"לולב", u"תענית", u"פסח"])


def isUpcoming(cur_siman, siman_link_num, cur_klal_num=0, klal_link_num=0):
    return klal_link_num > cur_klal_num or \
           (klal_link_num == cur_klal_num and siman_link_num > cur_siman)


def getKlalReferenceNum(comment_words, klal_index, cur_klal_num, cur_siman, isChelekBet):
    klal_link_num = getGematria(comment_words[klal_index + 1])

    if u'קודם' in comment_words[klal_index + 1]:
        klal_link_num = cur_klal_num - 1

    elif any(word in comment_words[klal_index - 1] for word in [u"ברכות", u"תפלה"]):
        pass

    elif referencesChelekBet(comment_words, klal_index):
        isChelekBet = True

    else:
        if isChelekBet and cur_klal_num is not 207:
            isChelekBet = True

        if (u'קמן' in comment_words[klal_index - 1] or u'קמן' in comment_words[klal_index - 2]) and \
                not isUpcoming(cur_siman, getGematria(comment_words[klal_index + 3]), cur_klal_num, klal_link_num, ):
            print "you should be more", comment_words[klal_index + 1], "in", cur_klal_num, "siman", cur_siman
            return -1

        elif (u'עיל' in comment_words[klal_index - 1] or u'עיל' in comment_words[klal_index - 2]) and \
                isUpcoming(cur_siman, getGematria(comment_words[klal_index + 3]), cur_klal_num, klal_link_num):
            print "you should be less happened", comment_words[
                klal_index + 1], "in", cur_klal_num, "siman", cur_siman
            return -1

    return klal_link_num, isChelekBet


def createLinkInsert(ref_title, link_num_1, link_num_2, continuation_link=None):
    insert_text = u"({} {}, {}".format(he_ref, numToHeb(link_num_1), numToHeb(link_num_1))
    if continuation_link:
        insert_text += u'-' + getRidOfSofitAndDash(continuation_link)
    return SelfLink(insert_text + u")", insert_offset)

while not any(x == line[end_footnote] for x in (string.whitespace + string.punctuation)):
            end_footnote += 1

def getSelfLinks(cur_siman, comment, cur_klal_num, isChelekBet):
    comment_words = comment.split()

    self_links_t = []

    for klal_index, word in enumerate(comment_words):

        # self links formatted as:  ___ 'כלל ___ סי
        if isRegularReference(word, comment_words, klal_index):

            # if reference to other of his works before reference
            if isReferenceToAnotherWork(comment_words, klal_index):
                continue

            klal_link_num, isChelekBet = getKlalReferenceNum(comment_words, klal_index, cur_klal_num, cur_siman,
                                                             isChelekBet)

            if klal_link_num is -1:
                continue

            # self_links.append(selfLink(cur_klal_num, cur_siman + 1, klal_link_num, comment_words[klal_index + 3]))
            addMultipleSimanim(self_links_t, comment_words[klal_index:], 3, klal_index, klal_link_num)

            # self_links_t.append(createLinkInsert(link_offset, klal_link_num, siman_link))

        elif isReferenceToPreviousOrUpcoming(word, comment_words, klal_index):

            siman_link_num = getGematria(getRidOfSofitAndDash(comment_words[klal_index + 2]))

            klal_link_num, isChelekBet = getKlalReferenceNum(comment_words, klal_index, cur_klal_num, cur_siman,
                                                             isChelekBet)

            if u'קמן' in word and not isUpcoming(cur_siman, siman_link_num):
                print "you should be more", comment_words[
                    klal_index + 2], "in", cur_klal_num, "siman", cur_siman
                continue

            elif u'עיל' in word and isUpcoming(cur_siman, siman_link_num):
                print "you should be less happened", comment_words[
                    klal_index + 2], "in", cur_klal_num, "siman", cur_siman
                continue

            # self_links.append(selfLink(cur_klal_num, cur_siman, cur_klal_num, comment_words[klal_index + 2]))
            addMultipleSimanim(self_links_t, comment_words[klal_index:], 2, klal_index, klal_link_num)

    for l in reversed(self_links_t):
        negative_offset = 0
        while any(word in comment_words[l.offset][negative_offset - 1] for word in [u'.', u':', u')']):
            negative_offset -= 1
        if negative_offset < 0:
            comment_words.insert(l.offset + 1, l.insert + comment_words[l.offset][negative_offset:])
            comment_words[l.offset] = comment_words[l.offset][:negative_offset]
        else:
            comment_words.insert(l.offset + 1, l.insert)

    return " ".join(comment_words)

class Seif:

    def __init__(self, seif_text, siman_idx, seif_idx):
        self.text_words = seif_text.split()
        self.siman_idx = siman_idx + 1
        self.seif_idx = seif_idx + 1
        self.link_inserts = []

    def is_self_refword(self, word):
        return any(self_ref_word in word for self_ref_word in self_ref_words)


    def is_position_word(self, word_idx):
        return any(position_word in self.text_words[word_idx] for position_word in position_words)

    def is_siman_word(self, word_idx):
        return any(siman_word in self.text_words[word_idx] for siman_word in siman_words)

    def is_ref(self, word_idx, word):
        row = {}
        words_len = len(self.text_words)
        if self.is_self_refword(word):
            if words_len > word_idx + 2:
                if self.is_position_word(word_idx+1):
                    if self.is_siman_word(word_idx+2):
                        if words_len > word_idx + 3 and self.is_valid_siman
                        row['source'] = '{} {}:{}'.format(he_ref, self.siman_idx, self.seif_idx)
                        # row['orginal text'] =
                        # row['text with ref'] =
                elif self.is_siman_word(word_idx+2):





    def get_selfrefs(self):
        for word_idx, word in enumerate(self.text_words):
            if self.is_ref(word_idx, word):

                if self.

        if any()


    def add_trick(self, trick):
        self.tricks.append(trick)


with open(filepath, 'r') as fr, open(fileoutpath, 'w') as csvfile:
    fieldnames = ['source', 'original text', 'text with ref']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    file_content = json.load(fr)
    ref = file_content['title']
    simanim = file_content['text']
    for siman_idx, siman in enumerate(simanim):
        for seif_idx, seif_text in enumerate(siman):
            seif = Seif(seif_text, siman_idx, seif_idx)
            if siman_idx:
            row = {}
            row['source'] = '{} {}:{}'.format(ref, siman_idx + 1, seif_idx + 1)
            # row['orginal text'] =
            # row['text with ref'] =
            writer.writerow(row)
            csvfile.get_selfrefs()

#
# SelfLink = namedtuple('SelfLink', ['insert', 'offset'])
