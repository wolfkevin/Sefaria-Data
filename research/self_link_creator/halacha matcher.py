# -*- coding: utf-8 -*-
import os
import json
import re
import string
import codecs
from collections import namedtuple

filename = "Shulchan Arukh, Yoreh De'ah - he - merged.json"
filepath = './shulchan arukh/{}'.format(filename)
fileoutpath = './output/{}.csv'.format(filename[:filename.find('-')])
he_ref = u'שלחן ערוך, יורה דעה'  # hebrew name of referenced text

self_ref_words = [u'לקמן', u'לעיל', u'להלן', u'עיין', u'ע\"ל']
siman_words = [u"סי'", u'סימן', u'ס\"ס']
position_words = [u'ריש', u'סוף']
seif_words = [u'סעי', u"ס''"]
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
    txt = re.sub('[\', ":.\n)]', u'', txt)
    if txt.find(u"טו") >= 0:
        txt = txt.replace(u"טו", u"יה")
    elif txt.find(u"טז") >= 0:
        txt = txt.replace(u"טז", u"יו")

    if len(txt) == 0:
        return False

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


def strip_nekud(word):
    data = word.replace(u"\u05B0", "")
    data = data.replace(u"\u05B1", "")
    data = data.replace(u"\u05B2", "")
    data = data.replace(u"\u05B3", "")
    data = data.replace(u"\u05B4", "")
    data = data.replace(u"\u05B5", "")
    data = data.replace(u"\u05B6", "")
    data = data.replace(u"\u05B7", "")
    data = data.replace(u"\u05B8", "")
    data = data.replace(u"\u05B9", "")
    data = data.replace(u"\u05BB", "")
    data = data.replace(u"\u05BC", "")
    data = data.replace(u"\u05BD", "")
    data = data.replace(u"\u05BF", "")
    data = data.replace(u"\u05C1", "")
    data = data.replace(u"\u05C2", "")
    data = data.replace(u"\u05C3", "")
    data = data.replace(u"\u05C4", "")
    return data


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
        self.original_words = seif_text.split()
        self.text_words = strip_nekud(seif_text).split()
        self.siman_num = siman_idx + 1
        self.seif_num = seif_idx + 1
        self.csv_rows = []
        self.cur_end_idx = 0
        self.cur_word_idx = 0
        self.cur_siman_num_ref = 0
        self.cur_seif_num_ref = 0
        self.cur_cont_num_ref = 0

    # def create_seif_ref(self, siman_num_idx):
    #     return Seif.SeifRef(self)
    #
    # class SeifRef:
    #     def __init__(self, seif_inst, siman_num_idx):
    #         self.seif_inst = seif_inst
    #         self.siman_num_idx = siman_num_idx
    #         self.seif_num_idx = 0
    #         self.cont_num_idx = 0
    #
    #         self.siman_num = siman_idx + 1
    #         self.seif_num = seif_idx + 1
    #         self.text_inserts = []
    #         self.csv_rows = []

    def is_self_refword(self, word):
        return any(self_ref_word in word for self_ref_word in self_ref_words)

    def is_position_word(self, word_idx):
        return any(position_word in self.text_words[word_idx] for position_word in position_words)

    def is_siman_word(self, word_idx):
        return any(siman_word in self.text_words[word_idx] for siman_word in siman_words)

    def is_seif_word(self, word_idx):
        return any(seif_word in self.text_words[word_idx] for seif_word in seif_words)

    def is_shorthand_seif(self, word_idx):
        if self.text_words[word_idx][:1] == u'ס':
            return True
        elif u'ס' in self.text_words[word_idx][:self.text_words[word_idx].find(u'"')]:
            print "here"
        return False

    def is_valid_siman_num(self, siman):
        return isGematria(siman) and len(siman_length) > getGematria(siman)

    def is_valid_seif_num(self, siman_num, seif_num):
        return isGematria(seif_num) and siman_length[getGematria(siman_num)] >= getGematria(seif_num)

    def siman_relative_to_ref_word(self, ref_word, siman_num_idx):
        siman_num = getGematria(self.text_words[siman_num_idx])
        if u'לעיל' in ref_word:
            if self.siman_num >= siman_num:
                return True
            else:
                print u"not actually ahead in {} {} but says: {} {} {}".format(self.siman_num, self.seif_num, ref_word,
                                                                               self.text_words[siman_num_idx - 1],
                                                                               self.text_words[siman_num_idx])
        elif u'לקמן' in ref_word or u'להלן' in ref_word:
            if siman_num >= self.siman_num:
                return True
            else:
                print u"not actually behind in {} {} but says: {} {} {}".format(self.siman_num, self.seif_num, ref_word,
                                                                                self.text_words[siman_num_idx - 1],
                                                                                self.text_words[siman_num_idx + 1])
        else:
            return True

    def find_insert_idx(self, end_idx):
        end_insert = 0
        while end_insert < len(self.original_words[end_idx]) \
                and not any(end_delimiter == self.original_words[end_idx][end_insert]
                            for end_delimiter in [u'.', u',', u':', u')', u'<', u']']):
            end_insert += 1
        return end_insert

    def create_link_insert_text(self):
        insert_text = u"({} {}".format(he_ref, numToHeb(self.cur_siman_num_ref))
        if self.cur_seif_num_ref > 0:
            insert_text += u", {}".format(numToHeb(self.cur_seif_num_ref))
            self.cur_seif_num_ref = 0
        if self.cur_cont_num_ref > 0:
            insert_text += u'-{}'.format(numToHeb(self.cur_cont_num_ref))
            self.cur_cont_num_ref = 0
        return insert_text + u')'

    def create_link_insert(self, end_idx):
        insert_idx = self.find_insert_idx(end_idx)
        link_insert_text = self.create_link_insert_text()

        if insert_idx == len(self.original_words[end_idx]):
            return u'{} {}'.format(self.original_words[end_idx], link_insert_text)
        else:
            word_pre_insert = self.original_words[end_idx][:insert_idx]
            word_post_insert = self.original_words[end_idx][insert_idx:]
            return u'{} {}{}'.format(word_pre_insert, link_insert_text, word_post_insert)

    def add_csv_row(self, end_idx, link_insert):
        row = {}
        row['source'] = u'{} {}:{}'.format(he_ref, self.siman_num, self.seif_num)
        row['original text'] = u" ".join(self.original_words[self.cur_word_idx - 2:end_idx + 4])
        row['text with ref'] = u" ".join(self.original_words[self.cur_word_idx:end_idx]) + u" " + link_insert
        self.csv_rows.append(row)

    def is_continuation(self, ref_num, potential_continuation_idx):
        gematria_idx = self.find_insert_idx(potential_continuation_idx)
        potential_continuation = self.text_words[potential_continuation_idx][:gematria_idx]
        if isGematria(potential_continuation) and \
                (getGematria(ref_num) + 1 == getGematria(potential_continuation)):
            self.cur_cont_num_ref = getGematria(potential_continuation)
            return True
        elif len(potential_continuation) > 1 and \
                potential_continuation[0] == u'ו' and \
                isGematria(potential_continuation[1:]) \
                and (getGematria(ref_num) + 1 == getGematria(potential_continuation[1:])):
            self.cur_cont_num_ref = getGematria(potential_continuation[1:])
            return True
        return False

    def get_seif_link(self, siman_num, seif_num_idx, is_shorthand_seif=False):
        seif_num = self.text_words[seif_num_idx][1:] if is_shorthand_seif else self.text_words[seif_num_idx]
        seif_num_gematria_idx = self.find_insert_idx(
            seif_num_idx)  # sometimes can be appended to html so isGematria will return false
        if self.is_valid_seif_num(siman_num, seif_num[:seif_num_gematria_idx]):
            self.cur_seif_num_ref = getGematria(seif_num[:seif_num_gematria_idx])
            if len(self.text_words) > seif_num_idx + 1 and \
                    self.is_continuation(seif_num[:seif_num_gematria_idx], seif_num_idx + 1):
                link_insert = self.create_link_insert(seif_num_idx + 1)
                self.add_csv_row(seif_num_idx + 1, link_insert)
                self.original_words[seif_num_idx + 1] = link_insert
                seif_num_idx += 1
            else:
                link_insert = self.create_link_insert(seif_num_idx)
                self.add_csv_row(seif_num_idx, link_insert)
                self.original_words[seif_num_idx] = link_insert
            if len(self.text_words) > seif_num_idx + 2:
                if self.is_seif_word(seif_num_idx + 1):
                    # siman x seif y and seif z
                    self.get_seif_link(siman_num, seif_num_idx + 2)
                # TODO: maybe this could happen but don't think so
                #  elif self.is_shorthand_seif(seif_num_idx + 1):
                #     self.get_seif_link(siman_num, seif_num_idx + 1, True)
                elif self.is_siman_word(seif_num_idx + 1):
                    # siman x seif y and siman z
                    self.get_siman_link(seif_num_idx + 2)
                # TODO: maybe add vi not continuation here or something
            # if self.is_continuation(seif_num, self.text_words[seif_num_idx+1])

    def get_siman_link(self, siman_num_idx, self_ref_word=''):
        siman_num = self.text_words[siman_num_idx]
        if self.is_valid_siman_num(siman_num) \
                and self.siman_relative_to_ref_word(self_ref_word, siman_num_idx):
            self.cur_siman_num_ref = getGematria(siman_num)
            if len(self.text_words) > siman_num_idx + 2:
                if self.is_seif_word(siman_num_idx + 1):
                    self.get_seif_link(siman_num, siman_num_idx + 2)
                elif self.is_siman_word(siman_num_idx + 1):
                    link_insert = self.create_link_insert(siman_num_idx)
                    self.add_csv_row(siman_num_idx, link_insert)
                    self.original_words[siman_num_idx] = link_insert
                    self.get_siman_link(siman_num_idx + 2)
                    # append siman link
                elif self.is_position_word(siman_num_idx + 1):
                    # ayein siman x and end of siman y
                    link_insert = self.create_link_insert(siman_num_idx)
                    self.add_csv_row(siman_num_idx, link_insert)
                    self.original_words[siman_num_idx] = link_insert
                    if self.is_siman_word(siman_num_idx + 2):
                        self.get_siman_link(siman_num_idx + 3, self_ref_word)
                elif self.is_shorthand_seif(siman_num_idx + 1):
                    self.get_seif_link(siman_num, siman_num_idx + 1, True)
                # TODO: maybe add continuation siman here
                else:
                    link_insert = self.create_link_insert(siman_num_idx)
                    self.add_csv_row(siman_num_idx, link_insert)
                    self.original_words[siman_num_idx] = link_insert

    def get_ref(self, word_idx, self_ref_word):
        if self.is_self_refword(self_ref_word):
            self.cur_word_idx = word_idx
            if len(self.text_words) > word_idx + 2:
                if self.is_position_word(word_idx + 1):
                    # e.g. לקמן ריש סימן רפ"ב
                    if self.is_siman_word(word_idx + 2):
                        self.get_siman_link(word_idx + 3, self_ref_word)
                elif self.is_siman_word(word_idx + 1):
                    self.get_siman_link(word_idx + 2, self_ref_word)

    def get_selfrefs(self):
        for word_idx, word in enumerate(self.text_words):

            self.get_ref(word_idx, word)


def to_utf8(lst):
    return [unicode(elem).encode('utf-8') for elem in lst]


with codecs.open(filepath, 'r', "utf-8") as fr, codecs.open(fileoutpath, 'w', 'utf-8') as csvfile:
    # fieldnames = ['Source', 'riginal text', 'text with ref']
    # writer.writeheader()
    csvfile.write(u'Source\tOriginal Text\tText With Ref\n')

    file_content = json.load(fr)
    ref = file_content['title']
    simanim = file_content['text']
    siman_length.append(0)
    for siman in simanim:
        siman_length.append(len(siman))
    for siman_idx, siman in enumerate(simanim):
        for seif_idx, seif_text in enumerate(siman):
            seif = Seif(seif_text, siman_idx, seif_idx)
            seif.get_selfrefs()
            for link in seif.csv_rows:
                csvfile.write(u'{}\t{}\t{}\n'.format(link['source'], link['original text'], link['text with ref']))
                # writer.writerow(to_utf8(link))
