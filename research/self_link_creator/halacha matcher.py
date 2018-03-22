# -*- coding: utf-8 -*-
import os
import json
import re
import string
import codecs
from collections import namedtuple

filepath = './shulchan arukh/Shulchan Arukh, Orach Chayim - he - merged.json'
fileoutpath = 'Shulchan Arukh, Orach Chayim_output.csv'
he_ref = u'שלחן ערוך, אורח חיים'  # hebrew name of referenced text

self_ref_words = [u'לקמן', u'לעיל', u'להלן', u'עיין', u'ע\"ל']
siman_words = [u"סי'", u'סימן', u'ס\"ס']
position_words = [u'ס\"ס', u'ריש', u'סוף']
seif_words = [u'סעיף', u"ס''"]
SelfLink = namedtuple('SelfLink', ['insert', 'offset'])

siman_length = []

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
gematria[u'ם'] = 40
gematria[u'ן'] = 50
gematria[u'ף'] = 80
gematria[u'ץ'] = 90


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
    txt = getRidOfSofit(txt)
    txt = re.sub('[\', ":.\n)]', '', txt)
    if txt.find(u"טו") >= 0:
        txt = txt.replace(u"טו", u"יה")
    elif txt.find(u"טז") >= 0:
        txt = txt.replace(u"טז", u"יו")

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
    letters[0] = [u"", u"א", u"ב", u"ג", u"ד", u"ה", u"ו", u"ז", u"ח", u"ט"]
    letters[1] = [u"", u"י", u"כ", u"ל", u"מ", u"נ", u"ס", u"ע", u"פ", u"צ"]
    letters[2] = [u"", u"ק", u"ר", u"ש", u"ת", u"תק", u"תר", u"תש", u"תת", u"תתק"]
    if (numdig > 3):
        print "We currently can't handle numbers larger than 999"
        exit()
    for count in range(numdig):
        hebnum += letters[numdig - count - 1][int(engnum[count])]
    hebnum = re.sub(u'יה', u'טו', hebnum)
    hebnum = re.sub(u'יו', u'טז', hebnum)
    return hebnum


def getRidOfSofit(txt):
    if txt == None:
        print "pause"
    if txt.find(u"ך") >= 0:
        txt = txt.replace(u"ך", u"כ")
    if txt.find(u"ם") >= 0:
        txt = txt.replace(u"ם", u"מ")
    if txt.find(u"ף") >= 0:
        txt = txt.replace(u"ף", u"פ")
    if txt.find(u"ץ") >= 0:
        txt = txt.replace(u"ץ", u"צ")
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

    def __init__(self, seif_text, siman_num, seif_num):
        self.text_words = seif_text.split()
        self.siman_num = siman_idx + 1
        self.seif_num = seif_idx + 1
        # self.link_inserts = []
        self.csv_rows = []

    def create_seif_ref(self, siman_num_idx):
        return Seif.SeifRef(self)

    class SeifRef:
        def __init__(self, seif_inst, siman_num_idx):
            self.seif_inst = seif_inst
            self.siman_num_idx = siman_num_idx
            self.seif_num_idx = 0
            self.cont_num_idx = 0

            self.siman_num = siman_idx + 1
            self.seif_num = seif_idx + 1
            self.text_inserts = []
            self.csv_rows = []

    def is_self_refword(self, word):
        return any(self_ref_word in word for self_ref_word in self_ref_words)

    def is_position_word(self, word_idx):
        return any(position_word in self.text_words[word_idx] for position_word in position_words)

    def is_siman_word(self, word_idx):
        return any(siman_word in self.text_words[word_idx] for siman_word in siman_words)

    def is_seif_word(self, word_idx):
        return any(seif_word in self.text_words[word_idx] for seif_word in seif_words)

    def is_valid_siman_num(self, siman):
        return isGematria(siman) and len(siman_length) > getGematria(siman)

    def is_valid_seif_num(self, siman_num, seif_num):
        return isGematria(seif_num) and len(siman_length[getGematria(siman_num)]) > getGematria(seif_num)

    def siman_relative_to_ref_word(self, ref_word, siman_num_idx):
        siman_num = getGematria(self.text_words[siman_num_idx])
        if u'לעיל' in ref_word:
            if self.siman_num >= siman_num:
                return True
            else:
                print "not actually behind " + ref_word + siman_num
        elif u'לקמן' in ref_word or u'להלן' in ref_word:
            if siman_num >= self.siman_num:
                return True
            else:
                print "not actually ahead " + ref_word + siman_num
        else:
            return True

    def find_insert_idx(self, end_idx):
        end_insert = 0
        while end_insert < len(self.text_words[end_idx]) \
                and not any(end_delimiter == self.text_words[end_idx][end_insert]
                            for end_delimiter in [u'.', u':', u')', u'<']):
            end_insert += 1
        return end_insert

    def create_link_insert_text(self, link_num_1_idx, link_num_2_idx=0, continuation_link_idx=0):
        link_num_1 = self.text_words[link_num_1_idx]
        insert_text = u"({} {}".format(he_ref, numToHeb(getGematria(link_num_1)))
        if link_num_2_idx > 0:
            link_num_2 = self.text_words[link_num_2_idx]
            insert_text += u", {}".format(numToHeb(getGematria(link_num_2)))
        if continuation_link_idx:
            continuation_link = self.text_words[continuation_link_idx]
            insert_text += u'-{}'.format(numToHeb(getGematria(continuation_link)))
        return insert_text + u')'
        # return SelfLink(insert_text + u")", insert_offset)

    def create_link_insert(self, siman_num_idx, seif_num_idx=0, continuation_link_idx=0):
        end_idx = max(siman_num_idx, seif_num_idx, continuation_link_idx)
        insert_idx = self.find_insert_idx(end_idx)
        link_insert_text = self.create_link_insert_text(siman_num_idx, seif_num_idx, continuation_link_idx)

        if insert_idx == len(self.text_words[insert_idx]):
            return u'{} {}'.format(self.text_words[insert_idx], link_insert_text)
        else:
            word_pre_insert = self.text_words[end_idx][:insert_idx]
            word_post_insert = self.text_words[end_idx][insert_idx:]
            return u'{} {}{}'.format(word_pre_insert, link_insert_text, word_post_insert)


    def create_csv_row(self, end_idx, link_insert):
        row = {}
        row['source'] = u'{} {}:{}'.format(he_ref, self.siman_num, self.seif_num)
        row['original text'] = u" ".join(self.text_words[self.cur_word_idx - 2:end_idx + 2])
        row['text with ref'] = u" ".join(self.text_words[self.cur_word_idx:end_idx]) + u" " + link_insert
        self.csv_rows.append(row)

    def get_siman_link(self, siman_idx, self_ref_word):
        siman_num_idx = siman_idx + 1
        siman_num = self.text_words[siman_num_idx]
        if self.is_valid_siman_num(siman_num) \
                and self.siman_relative_to_ref_word(self_ref_word, siman_num_idx):
            # link_insert = createLinkInsert(self.text_words[siman_num_idx])
            if len(self.text_words) > siman_num_idx + 2:
                if self.is_seif_word(siman_num_idx + 2):
                    print('here')
                    # self.get_seif_link()
                elif self.is_siman_word(siman_num_idx + 2):
                    link_insert = self.create_link_insert(siman_num_idx)
                    self.csv_rows.append(self.create_csv_row(siman_num_idx, link_insert))
                    self.text_words[siman_num_idx] = link_insert
                    # append siman link
                # TODO: maybe add continuation siman here
                else:
                    link_insert = self.create_link_insert(siman_num_idx)
                    self.row_inserts.append(self.create_csv_row(siman_num_idx, link_insert))
                    self.text_words[siman_num_idx] = link_insert

    def get_ref(self, word_idx, self_ref_word):
        row = {}
        # row = []
        if self.is_self_refword(self_ref_word):
            self.cur_word_idx = word_idx
            if len(self.text_words) > word_idx + 2:
                if self.is_position_word(word_idx + 1):
                    # e.g. לקמן ריש סימן רפ"ב
                    if self.is_siman_word(word_idx + 2):
                        insert_link, end_siman_idx = self.get_siman_link(word_idx + 2, self_ref_word)
                # elif self.is_siman_word(word_idx+2):

    def get_selfrefs(self):
        for word_idx, word in enumerate(self.text_words):
            self.get_ref(word_idx, word)


def to_utf8(lst):
    return [unicode(elem).encode('utf-8') for elem in lst]


with codecs.open(filepath, 'r', "utf-8") as fr, codecs.open(fileoutpath, 'w', 'utf-8') as csvfile:
    fieldnames = ['source', 'original text', 'text with ref']
    # writer.writeheader()
    csvfile.write(u'source\toriginal text\ttext with ref\n')

    file_content = json.load(fr)
    ref = file_content['title']
    simanim = file_content['text']
    siman_length.append(0)
    for siman in enumerate(simanim):
        siman_length.append(len(siman))
    for siman_idx, siman in enumerate(simanim):
        for seif_idx, seif_text in enumerate(siman):
            seif = Seif(seif_text, siman_idx, seif_idx)
            seif.get_selfrefs()
            for link in seif.csv_rows:
                csvfile.write(u'{}\t{}\t{}\n'.format(link['source'], link['original text'], link['text with ref']))
                # writer.writerow(to_utf8(link))
