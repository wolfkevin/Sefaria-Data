# -*- coding: utf-8 -*-
from collections import namedtuple
import json
import os
import sys
import codecs
import re
from sources.functions import numToHeb, getGematria, isGematria,  post_index, post_text
from sefaria.utils.hebrew import strip_nikkud, normalize_final_letters_in_str
import sefaria.datatype as data
# import http_request

p = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, p)
sys.path.insert(0, "../")




titles_dict = {
    "Shulchan Arukh, Yoreh De'ah": u'שו, יורה דעה',
    "Shulchan Arukh, Orach Chayim": u'שלחן ערוך, אורח חיים',
    "Shulchan Arukh, Even HaEzer": u'שלחן ערוך, אבן העזר',
    "Shulchan Arukh, Choshen Mishpat": u'שלחן ערוך, חושן משפט',
    "Beit Shmuel": u'שלחן ערוך, אבן העזר',
    "Chelkat Mechokek": u'שלחן ערוך, אבן העזר',
}

titles_to_parse = [
    # "Shulchan Arukh, Yoreh De'ah",
    # "Shulchan Arukh, Orach Chayim",
    # "Shulchan Arukh, Even HaEzer",
    # "Shulchan Arukh, Choshen Mishpat",
    "Chelkat Mechokek"
]

fileend = " - he - merged.json"
filepath = './Talmud/'
he_ref = u''  # hebrew name of referenced text


self_ref_words = [u'לקמן', u'לעיל'] #, u'להלן'
# ref_words = [u'עיין', u'ע\"ל', u"ע'"]
SelfLink = namedtuple('SelfLink', ['insert', 'offset'])

siman_length = []


"""
Local Settings Example file for Sefaria-Data scripts
Copy this file to "local_settings.py" and import values as needed.
e.g.:
import sys
import os
# for a script located two directories below this file
p = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, p)
from local_settings import *
sys.path.insert(0, SEFARIA_PROJECT_PATH)
os.environ['DJANGO_SETTINGS_MODULE'] = "settings"
from sefaria.model import *
"local_settings.py" is excluded from this Git repo.
"""

# In scripts you can add this value to your Python path so that you can
# import from sefaria, if this path is not already set in your environment
SEFARIA_PROJECT_PATH = "/path/your/copy/of/Sefaria-Project"

SEFARIA_SERVER = "http://draft.sefaria.org"

API_KEY = "6fC09W4nRt37WGpVyMKGyjcCXLchaCR8RDVODE10r38"



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
        self.text_words = strip_nikkud(seif_text).split()
        self.siman_num = siman_idx + 1
        self.seif_num = seif_idx + 1
        self.csv_rows = []
        self.cur_end_idx = 0
        self.cur_word_idx = 0
        self.cur_siman_num_ref = 0
        self.cur_seif_num_ref = 0
        self.cur_cont_num_ref = 0

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

    def is_valid_seif_num(self, seif_num):
        if isGematria(seif_num) and siman_length[self.cur_siman_num_ref] >= getGematria(seif_num):
            return True
        else:
            print("weird")
            return False

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
            # else:
            #     print u"not actually behind in {} {} but says: {} {} {}".format(self.siman_num, self.seif_num, ref_word,
            #                                                                     self.text_words[siman_num_idx - 1],
            #                                                                     self.text_words[siman_num_idx + 1])
        else:
            return True

    def find_insert_idx(self, end_idx, is_shorthand_seif=False):
        end_insert = 0
        if len(self.text_words) <= end_idx:
            print "uh oh"
        while (end_insert < len(self.original_words[end_idx])) \
                and (not any(end_delimiter == self.original_words[end_idx][end_insert]
                             for end_delimiter in [u'.', u',', u':', u')', u'<', u'<'  u']'])):
            end_insert += 1
        if is_shorthand_seif:
            end_insert -= 1
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
        backward_offset = self.cur_word_idx if self.cur_word_idx < 2 else 2
        # forward_offset = len(self.original_words) - 1 if self.cur_end_idx + 3 >= len(self.original_words) else self.cur_end_idx + 3
        row['original text'] = u" ".join(self.original_words[self.cur_word_idx - backward_offset:end_idx + 4])
        if row['original text'] == '':
            print "stop"
        row['text with ref'] = u" ".join(self.original_words[self.cur_word_idx:end_idx]) + u" " + link_insert
        self.csv_rows.append(row)

    def is_continuation(self, ref_num, end_idx, potential_cont_idx):
        if len(self.text_words) > potential_cont_idx:
            gematria_idx = self.find_insert_idx(potential_cont_idx)
            potential_continuation = self.text_words[potential_cont_idx][:gematria_idx]
            if self.is_valid_seif_num(potential_continuation) and \
                    (ref_num + 1 == getGematria(potential_continuation)):
                self.cur_cont_num_ref = getGematria(potential_continuation)
                return self.is_continuation(self.cur_cont_num_ref, potential_cont_idx, potential_cont_idx + 1)

            elif len(potential_continuation) > 1 and \
                    potential_continuation[0] == u'ו' and \
                    self.is_valid_seif_num(potential_continuation[1:]) \
                    and (ref_num + 1 == getGematria(potential_continuation[1:])):
                self.cur_cont_num_ref = getGematria(potential_continuation[1:])
                return self.is_continuation(self.cur_cont_num_ref, potential_cont_idx, potential_cont_idx + 1)
        return end_idx

    def get_seif_link(self, seif_num_idx, is_shorthand_seif=False):
        if len(self.text_words) > seif_num_idx:
            seif_num = self.text_words[seif_num_idx][1:] if is_shorthand_seif else self.text_words[seif_num_idx]
            seif_num_gematria_idx = self.find_insert_idx(
                seif_num_idx, is_shorthand_seif)  # sometimes can be appended to html so isGematria will return false
            if self.is_valid_seif_num(seif_num[:seif_num_gematria_idx]):
                if self.cur_siman_num_ref == 0:
                    self.cur_siman_num_ref = self.siman_num
                self.cur_seif_num_ref = getGematria(seif_num[:seif_num_gematria_idx])
                self.cur_end_idx = self.is_continuation(self.cur_seif_num_ref, seif_num_idx, seif_num_idx + 1)
                self.get_ref(seif_num_idx + 1)

    def get_siman_link(self, siman_num_idx, self_ref_word=''):
        if len(self.text_words) > siman_num_idx:
            siman_num = self.text_words[siman_num_idx]
            if siman_num == u"אוקמיה":
                print("found ya")
            if self.is_valid_siman_num(siman_num) \
                    and self.siman_relative_to_ref_word(self_ref_word, siman_num_idx):
                self.cur_siman_num_ref = getGematria(siman_num)
                self.cur_end_idx = siman_num_idx
                self.get_ref(siman_num_idx + 1, self_ref_word)

    def get_ref(self, word_idx, self_ref_word=''):
        if len(self.text_words) > word_idx:
            if self.is_position_word(word_idx):
                # e.g. לקמן ריש סימן רפ"ב
                self.get_ref(word_idx + 1, self_ref_word)
            elif self.is_siman_word(word_idx):
                # e.g לקמן סימן רפ"ב
                if self.cur_siman_num_ref != 0:
                    link_insert = self.create_link_insert(self.cur_end_idx)
                    self.add_csv_row(self.cur_end_idx, link_insert)
                    self.original_words[self.cur_end_idx] = link_insert
                    self.cur_siman_num_ref = 0
                self.get_siman_link(word_idx + 1, self_ref_word)
            elif self.is_seif_word(word_idx):
                # e.g לקמן סימן רפ"ב
                if self.cur_seif_num_ref != 0:
                    link_insert = self.create_link_insert(self.cur_end_idx)
                    self.add_csv_row(self.cur_end_idx, link_insert)
                    self.original_words[self.cur_end_idx] = link_insert
                    self.cur_seif_num_ref = 0
                self.get_seif_link(word_idx + 1)
            elif self.is_shorthand_seif(word_idx):
                if self.cur_seif_num_ref != 0:
                    link_insert = self.create_link_insert(self.cur_end_idx)
                    self.add_csv_row(self.cur_end_idx, link_insert)
                    self.original_words[self.cur_end_idx] = link_insert
                    self.cur_seif_num_ref = 0
                self.get_seif_link(word_idx, True)
        if self.cur_siman_num_ref != 0:
            link_insert = self.create_link_insert(self.cur_end_idx)
            self.add_csv_row(self.cur_end_idx, link_insert)
            self.original_words[self.cur_end_idx] = link_insert
            self.cur_siman_num_ref = 0

    def get_selfrefs(self):
        for word_idx, word in enumerate(self.text_words):
            if u'אסורה' in word and self.siman_num == 7:
                print "gotcha"
            if self.is_self_refword(word):
                self.cur_word_idx = word_idx
                self.get_ref(word_idx + 1, word)


def to_utf8(lst):
    return [unicode(elem).encode('utf-8') for elem in lst]


with codecs.open(filepath + "Shulchan Arukh, Even HaEzer" + fileend, 'r', "utf-8") as fr:
    file_content = json.load(fr)
    simanim = file_content['text']
    siman_length = []
    siman_length.append(0)
    for siman in simanim:
        siman_length.append(len(siman))

for title in titles_to_parse:
    text_w_links = [[]]
    with codecs.open(filepath + title + fileend, 'r', "utf-8") as fr:
        file_content = json.load(fr)
        en_title = file_content['title']
        he_ref = titles_dict[en_title]
        simanim = file_content['text']
        with codecs.open(filepath + 'output/' + en_title + '_test.tsv', 'w', 'utf-8') as csvfile:
            # fieldnames     = ['Source', 'riginal text', 'text with ref']
            # writer.writeheader()
            csvfile.write(u'Source\tOriginal Text\tText With Ref\n')
            # siman_length = []
            # siman_length.append(0)
            # for siman in simanim:
            #     siman_length.append(len(siman))
            for siman_idx, siman in enumerate(simanim):
                siman_w_links = []
                for seif_idx, seif_text in enumerate(siman):
                    seif = Seif(seif_text, siman_idx, seif_idx)
                    seif.get_selfrefs()
                    siman_w_links.append(u' '.join(seif.original_words))
                    for link in seif.csv_rows:
                        csvfile.write(
                            u'{}\t{}\t{}\n'.format(link['source'], link['original text'], link['text with ref']))
                text_w_links.append(siman_w_links)
                # writer.writerow(to_utf8(link))
                
    text_version = {
        'versionTitle': "Merged with generated links",
        'versionSource': "http://draft.sefaria.org/Chelkat_Mechokek",
        'language': 'he',
        'text': text_w_links,
    }
    post_text(title, text_version)
'''
# כדיליף לקמן (עמוד ב)
תענית (פ"ב דף טז: ולקמן דף סג.)
(לקמן דף מט:)
(לקמן כו.)
(לקמן ד' כט.)
בכתובות (דף קיב:)
'''
