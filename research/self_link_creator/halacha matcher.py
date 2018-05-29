# -*- coding: utf-8 -*-
from collections import namedtuple
import json
import codecs
import re
from sources.functions import post_index, post_text
from sefaria.utils.hebrew import strip_nikkud, normalize_final_letters_in_str, gematria
from data_utilities.util import numToHeb
from sefaria.datatype import jagged_array
from sefaria.model import *

Ref.is_ref("Yoreh De'ah 123:100")

titles_dict = {
    "Shulchan Arukh, Yoreh De'ah": u'שו"ע יו"ד',
    "Shulchan Arukh, Orach Chayim": u'שו"ע או"ח ',
    "Shulchan Arukh, Even HaEzer": u'שו"ע אב"ה',
    "Shulchan Arukh, Choshen Mishpat": u'שו"ע חו"מ',
    "Beit Shmuel": u'שו"ע אב"ה',
    "Chelkat Mechokek": u'שו"ע אב"ה',
}

titles_to_parse = [
    "Shulchan Arukh, Yoreh De'ah",
    # "Shulchan Arukh, Orach Chayim",
    # "Shulchan Arukh, Even HaEzer",
    # "Shulchan Arukh, Choshen Mishpat",
    # "Chelkat Mechokek"
]

# indx = Ref("Shulchan Arukh, Orach Chayim").index
# indx.struct_objs['Topic'].default = True
# ind = {
# }
# for k, v in indx:
#     ind[k] = v
# post_index(indx)

fileend = " - he - merged.json"
filepath = 'shulchan arukh/'
fileoutpath = './output/'
# he_ref = u''  # hebrew name of referenced text

self_ref_words = [u'לקמן', u'לעיל', u'להלן', u'עיין', u'ע\"ל', u"ע'", u"לק'", u'באר']
siman_words = [u"סי'", u'סימן', u'ס\"ס', u'ס"ס', u"ס''ס"]
position_words = [u'ריש', u'סוף']
seif_words = [u'סעי', u"ס'"]
SelfLink = namedtuple('SelfLink', ['insert', 'offset'])

# siman_length = []

# TODO: DEFINE THESE
SELF_REF_WORDS = self_ref_words
D1_WORDS = siman_words
D2_WORDS = seif_words
SHORTHAND_LETTER = u'ס'

TEXT_JA = None
BASE_TEXT = None


def isGematria(txt):
    txt = normalize_final_letters_in_str(txt)
    txt = re.sub('[\', ":.\n)]', u'', txt)
    if txt.find(u"טו") >= 0:
        txt = txt.replace(u"טו", u"יה")
    elif txt.find(u"טז") >= 0:
        txt = txt.replace(u"טז", u"יו")

    if len(txt) == 0:
        print "not gematria " + txt
        return False

    while txt[0] == u'ת':
        txt = txt[1:]
    
    if txt == u'זה':
        pass

    if len(txt) == 1:
        if txt[0] < u'א' or txt[0] > u'ת':
            print "not gematria " + txt
            return False
    elif len(txt) == 2:
        if txt[0] < u'י' or (txt[0] < u'ק' and txt[1] > u'ט'):
            print "not gematria " + txt
            return False
    elif len(txt) == 3:
        if txt[0] < u'ק' or txt[1] < u'י' or txt[2] > u'ט':
            print "not gematria " + txt
            return False
    else:
        return False
    return True


# # In scripts you can add this value to your Python path so that you can
# # import from sefaria, if this path is not already set in your environment
# SEFARIA_PROJECT_PATH = "/path/your/copy/of/Sefaria-Project"
# 
# SEFARIA_SERVER = "http://proto.sefaria.org"
# 
# API_KEY = "6fC09W4nRt37WGpVyMKGyjcCXLchaCR8RDVODE10r38"


class Segment:

    def __init__(self, ref, segment_text, d1_num, d2_num):
        self.ref = ref
        self.original_words = segment_text.split()
        self.text_words = strip_nikkud(segment_text).split()
        self.d1_num = d1_idx + 1
        self.d2_num = d2_idx + 1
        self.csv_rows = []
        self.cur_end_idx = 0
        self.cur_word_idx = 0
        self.cur_d1_num_ref = 0
        self.cur_d2_num_ref = 0
        self.cur_cont_num_ref = 0

    def is_self_refword(self, word):
        return any(self_ref_word in word for self_ref_word in SELF_REF_WORDS)

    def is_position_word(self, word_idx):
        return any(position_word in self.text_words[word_idx] for position_word in position_words)

    def is_d1_word(self, word_idx):
        return any(d1_word in self.text_words[word_idx] for d1_word in D1_WORDS)

    def is_d2_word(self, word_idx):
        return any(d2_word in self.text_words[word_idx] for d2_word in D2_WORDS)

    def is_shorthand_d2(self, word_idx):
        if self.text_words[word_idx][:1] == SHORTHAND_LETTER:
            return True
        elif u'ס' in self.text_words[word_idx][:self.text_words[word_idx].find(u'"')]:
            print "here"
        return False

    def is_valid_d1_num(self, d1):
        #TODO: maybe incorporate זה as valid num
        return isGematria(re.sub(ur'[^א-ת]', u'', d1)) and Ref.is_ref(
            "{} {}".format(self.ref.normal(), gematria(d1))) and len(BASE_TEXT) >= gematria(d1)

    def is_valid_d2_num(self, d2_num):
        return isGematria(d2_num) and Ref.is_ref(
            "{} {}:{}".format(self.ref.normal(), self.cur_d1_num_ref, gematria(d2_num))) and len(
            BASE_TEXT[gematria(d2_num)-1]) >= gematria(d2_num)

    def d1_relative_to_ref_word(self, ref_word, d1_num_idx):
        d1_num = gematria(self.text_words[d1_num_idx])
        if u'לעיל' in ref_word:
            if self.d1_num >= d1_num:
                return True
            else:
                print u"not actually ahead in {} {} but says: {} {} {}".format(self.d1_num, self.d2_num, ref_word,
                                                                               self.text_words[d1_num_idx - 1],
                                                                               self.text_words[d1_num_idx])
        elif u'לקמן' in ref_word or u'להלן' in ref_word:
            if d1_num >= self.d1_num:
                return True
            # else:
            #     print u"not actually behind in {} {} but says: {} {} {}".format(self.d1_num, self.d2_num, ref_word,
            #                                                                     self.text_words[d1_num_idx - 1],
            #                                                                     self.text_words[d1_num_idx + 1])
        else:
            return True

    def find_insert_idx(self, end_idx, is_shorthand_d2=False):
        end_insert = re.search(ur'[.,;?! })<]|$', self.original_words[end_idx]).start()
        if is_shorthand_d2:
            end_insert -= 1
        return end_insert

    def create_link_insert_text(self):
        insert_text = u"({} {}".format(self.ref.he_normal(), numToHeb(self.cur_d1_num_ref))
        if self.cur_d2_num_ref > 0:
            insert_text += u", {}".format(numToHeb(self.cur_d2_num_ref))
            self.cur_d2_num_ref = 0
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
        row['source'] = u'{} {}:{}'.format(self.ref.he_normal(), self.d1_num, self.d2_num)
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
            if self.is_valid_d2_num(potential_continuation) and \
                    (ref_num + 1 == gematria(potential_continuation)):
                self.cur_cont_num_ref = gematria(potential_continuation)
                return self.is_continuation(self.cur_cont_num_ref, potential_cont_idx, potential_cont_idx + 1)

            elif len(potential_continuation) > 1 and \
                    potential_continuation[0] == u'ו' and \
                    self.is_valid_d2_num(potential_continuation[1:]) \
                    and (ref_num + 1 == gematria(potential_continuation[1:])):
                self.cur_cont_num_ref = gematria(potential_continuation[1:])
                return self.is_continuation(self.cur_cont_num_ref, potential_cont_idx, potential_cont_idx + 1)
        return end_idx

    def get_d2_link(self, d2_num_idx, is_shorthand_d2=False):
        if len(self.text_words) > d2_num_idx:
            d2_num = self.text_words[d2_num_idx][1:] if is_shorthand_d2 else self.text_words[d2_num_idx]
            d2_num_gematria_idx = self.find_insert_idx(
                d2_num_idx, is_shorthand_d2)  # sometimes can be appended to html so isGematria will return false
            if self.is_valid_d2_num(d2_num[:d2_num_gematria_idx]):
                if self.cur_d1_num_ref == 0:
                    self.cur_d1_num_ref = self.d1_num
                self.cur_d2_num_ref = gematria(d2_num[:d2_num_gematria_idx])
                self.cur_end_idx = self.is_continuation(self.cur_d2_num_ref, d2_num_idx, d2_num_idx + 1)
                self.get_ref(d2_num_idx + 1)

    def get_d1_link(self, d1_num_idx, self_ref_word=''):
        if len(self.text_words) > d1_num_idx:
            d1_num = self.text_words[d1_num_idx]
            if self.is_valid_d1_num(d1_num) \
                    and self.d1_relative_to_ref_word(self_ref_word, d1_num_idx):
                self.cur_d1_num_ref = gematria(d1_num)
                self.cur_end_idx = d1_num_idx
                self.get_ref(d1_num_idx + 1, self_ref_word)

    def get_ref(self, word_idx, self_ref_word=''):
        if len(self.text_words) > word_idx:
            if self.is_position_word(word_idx):
                # e.g. לקמן ריש סימן רפ"ב
                self.get_ref(word_idx + 1, self_ref_word)
            elif self.is_d1_word(word_idx):
                # e.g לקמן סימן רפ"ב
                if self.cur_d1_num_ref != 0:
                    link_insert = self.create_link_insert(self.cur_end_idx)
                    self.add_csv_row(self.cur_end_idx, link_insert)
                    self.original_words[self.cur_end_idx] = link_insert
                    self.cur_d1_num_ref = 0
                self.get_d1_link(word_idx + 1, self_ref_word)
            elif self.is_shorthand_d2(word_idx):
                if self.cur_d2_num_ref != 0:
                    link_insert = self.create_link_insert(self.cur_end_idx)
                    self.add_csv_row(self.cur_end_idx, link_insert)
                    self.original_words[self.cur_end_idx] = link_insert
                    self.cur_d2_num_ref = 0
                self.get_d2_link(word_idx, True)
            elif self.is_d2_word(word_idx):
                # e.g לקמן סימן רפ"ב
                if self.cur_d2_num_ref != 0:
                    link_insert = self.create_link_insert(self.cur_end_idx)
                    self.add_csv_row(self.cur_end_idx, link_insert)
                    self.original_words[self.cur_end_idx] = link_insert
                    self.cur_d2_num_ref = 0
                self.get_d2_link(word_idx + 1)
        if self.cur_d1_num_ref != 0:
            link_insert = self.create_link_insert(self.cur_end_idx)
            self.add_csv_row(self.cur_end_idx, link_insert)
            self.original_words[self.cur_end_idx] = link_insert
            self.cur_d1_num_ref = 0

    def get_selfrefs(self):
        for word_idx, word in enumerate(self.text_words):
            if self.is_self_refword(word):
                self.cur_word_idx = word_idx
                self.get_ref(word_idx + 1, word)


def to_utf8(lst):
    return [unicode(elem).encode('utf-8') for elem in lst]


# with codecs.open(filepath + "Shulchan Arukh, Even HaEzer" + fileend, 'r', "utf-8") as fr:
#     file_content = json.load(fr)
#     d1im = file_content['text']
#     d1_length = []
#     d1_length.append(0)
#     for d1 in d1im:
#         d1_length.append(len(d1))


for title in titles_to_parse:
    new_text_ja = jagged_array.JaggedArray([[]])
    # text_w_links = [[]]
    ref = Ref(title)
    # he_ref = ref.he_normal()
    TEXT_JA = TextChunk(ref, 'he').text
    BASE_TEXT = TEXT_JA
    with codecs.open(filepath + ref.normal() + '_test.tsv', 'wb+', 'utf-8') as csvfile:
        csvfile.write(u'Source\tOriginal Text\tText With Ref\n')
        # d1_length = []
        # d1_length.append(0)
        # for d1 in d1im:
        #     d1_length.append(len(d1))
        for d1_idx, d1 in enumerate(TEXT_JA):
            # d1_w_links = []
            for d2_idx, seg_text in enumerate(d1):
                seg = Segment(ref, seg_text, d1_idx, d2_idx)
                seg.get_selfrefs()
                new_text_ja.set_element([d1_idx, d2_idx], u' '.join(seg.original_words), u'')
                # d1_w_links.append(u' '.join(d2.original_words))
                for link in seg.csv_rows:
                    csvfile.write(
                        u'{}\t{}\t{}\n'.format(link['source'], link['original text'], link['text with ref']))
            # text_w_links.append(d1_w_links)
            # writer.writerow(to_utf8(link))

    text_version = {
        'versionTitle': "Merged with generated links",
        'versionSource': "http://proto.sefaria.org/{}".format(title),
        'language': 'he',
        'text': new_text_ja.array(),
    }
    # post_text(title, text_version)
