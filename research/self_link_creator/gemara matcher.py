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

titles_dict = {
    "Shulchan Arukh, Yoreh De'ah": u'שו"ע יו"ד',
    "Shulchan Arukh, Orach Chayim": u'שו"ע או"ח ',
    "Shulchan Arukh, Even HaEzer": u'שו"ע אב"ה',
    "Shulchan Arukh, Choshen Mishpat": u'שו"ע חו"מ',
    "Beit Shmuel": u'שו"ע אב"ה',
    "Chelkat Mechokek": u'שו"ע אב"ה',
}

titles_to_parse = [
    "Rashi on Zevachim",
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
daf_words = [u"ד'", u'דף']
AMUD_WORDS = [u'עמוד', u'']

SelfLink = namedtuple('SelfLink', ['insert', 'offset'])

# siman_length = []

# TODO: DEFINE THESE
SELF_REF_WORDS = self_ref_words
D1_WORDS = daf_words
D2_WORDS = None
SHORTHAND_LETTER = u'ס'

TEXT_JA = None
BASE_TEXT = None
BASE_TEXT_JA = None


def convert_index_to_daf(index):
    amud = u"b" if index % 2 else u'a'
    daf = (index/2) + 1
    return unicode(daf) + amud


def convert_daf_to_index(daf, amud):
    return (daf*2)-2 if amud == u"." else (daf*2)-1


def isGematria(txt):
    txt = normalize_final_letters_in_str(txt)
    txt = re.sub('[\', ":.\n)]', u'', txt)
    if txt.find(u"טו") >= 0:
        txt = txt.replace(u"טו", u"יה")
    elif txt.find(u"טז") >= 0:
        txt = txt.replace(u"טז", u"יו")
        
    if txt == u'דפ':
        pass

    if len(txt) == 0:
        print "not gematria " + txt
        return False
    try:
        while txt[0] == u'ת':
            txt = txt[1:]
    except:
        return False

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


# u'עיין', u'ע\"ל', u"ע'", u"לק'", u'באר'
# talmud_str = ur"(להלן|לעיל|לקמן)( |\(|{|\[)((((ילפ|ב).{0,30})|דף|ד')( |{|\(|\[))?(([א-ת]*)(:|\.))"
talmud_str = ur"(להלן|לעיל|לקמן) ((((ילפ|ב).{0,30})?(\(|\[)))?(((דף|ד')(\.)? )?(([א-ת]*)(:|\.|)))"
talmud_str_re = re.compile(talmud_str)
with codecs.open(filepath + 'commentary' + '_test4.tsv', 'wb+', 'utf-8') as csvfile:
    csvfile.write(u'Source\tText With Ref\n')
    for title in IndexSet({"$and": [{"categories": "Talmud"}, {"categories": "Commentary"},  {"schema.depth": 3}]}):
        # new_text_ja = jagged_array.JaggedArray([[]])
        # text_w_links = [[]]
        ref = Ref(title.title)
        # he_ref = ref.he_normal()
        TEXT_JA = TextChunk(ref, 'he').text
        BASE_TEXT = Ref(ref.index.base_text_titles[0])
        BASE_TEXT_JA = TextChunk(BASE_TEXT, 'he').text
        # d1_length = []
        # d1_length.append(0)
        # for d1 in d1im:
        #     d1_length.append(len(d1))
        for d1_idx, d1 in enumerate(TEXT_JA):   
            # d1_w_links = []
            for d2_idx, d2 in enumerate(d1):
                for d3_idx, seg_text in enumerate(d2):
                    offset = 0
                    for match in re.finditer(talmud_str, seg_text):
                        if u'דפ' in match.group(11):
                            pass
                        if len(match.group(11)) > 0 and isGematria(match.group(11)):
                            #TODO insert into text after item the object match.end()
                            # match.group(7)
                            if seg_text[match.end()+offset] == u')':
                                insert = u'{} '.format(BASE_TEXT.he_normal()) 
                                seg_text = seg_text[:match.regs[7][0]+offset] + insert + seg_text[match.regs[7][0]+offset:]
                            else:
                                insert = u'({} '.format(BASE_TEXT.he_normal())
                                seg_text = seg_text[:match.regs[7][0]+offset] + insert + seg_text[match.regs[7][0]+offset:match.end()+offset] + u')' + seg_text[match.end()+offset:]
                                offset += 1
                            csvfile.write(u'{}\t{}\t{}\n'.format((ref.normal() + u' ' + convert_index_to_daf(d1_idx)+u'.'+unicode(d3_idx)), seg_text[match.start()+offset-20:match.end()+offset+len(insert)+2], seg_text[match.start()-1+offset:match.end()+offset+len(insert)+1]))
                            offset += len(insert)
                        else:
                            pass
            # seg = Segment(BASE_TEXT, seg_text, d1_idx, d2_idx)
            # seg.get_selfrefs()
            # new_text_ja.set_element([d1_idx, d2_idx], u' '.join(seg.original_words), u'')
            # # d1_w_links.append(u' '.join(d2.original_words))
            # for link in seg.csv_rows:
            #     
            # text_w_links.append(d1_w_links)
            # writer.writerow(to_utf8(link))

    # text_version = {
    #     'versionTitle': "Merged with generated links",
    #     'versionSource': "http://proto.sefaria.org/{}".format(title),
    #     'language': 'he',
    #     'text': new_text_ja.array(),
    # }
    # post_text(title, text_version)
# ''' 
# # כדיליף לקמן (עמוד ב)
# תענית (פ"ב דף טז: ולקמן דף סג.)
# (לקמן דף מט:)
# (לקמן כו.)
# (לקמן ד' כט.)
# בכתובות (דף קיב:)
# לעיל בפירקין (דף נב.)
# לקמן בפרק בית שמאי (דף מג.)
# לקמן באיזהו מקומן (דף מח.)
# לקמן בכל הזבחים שנתערבו (דף פב.)
# לקמן ילפינן לה בפירקין (כג:)
# '''
