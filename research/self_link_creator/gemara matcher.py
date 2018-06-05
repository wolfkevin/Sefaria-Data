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
#skip (להלן|לעיל|לקמן) ((ילפ|ב|פ(\'|\")).{0,30}) (\(|\[)?((דף|ד\')(\.)? )?[א-ת]*
self_ref_words = u'(להלן|לעיל|לקמן)'
filler_words = u"(ילפ|ב|פ(\'|\"))"
daf_words = u"((דף|ד\')(\.)? )"
parentheses = u'(\(|\[)'
amud_words = u'(:|\.| ע\"ב| ע\"א)'

# u'עיין', u'ע\"ל', u"ע'", u"לק'", u'באר'
# talmud_str = ur"(להלן|לעיל|לקמן) ((ילפ|ב|פ('|\")).{0,30})?(\(|\[)?((דף|ד')(\.)? )?([א-ת]*)(:|\.| ע\"ב| ע\"א)?"
talmud_str = ur'(להלן|לעיל|לקמן) (((ילפ|ב|פ(\'|")|פרק).{0,30} ((\(|\[)?((דף|ד\')(\.)? )|(\(|\[)))|(\(|\[)?((דף|ד\')(\.)? )?)([א-ת][א-ת"]?["א-ת]?["א-ת]?)\'?(?!\")(:|\.| ע"[אב]|, ?[אב])?'
# talmud_str3 = ur'{} (({}.{{0,30}} ({}?{}|{}))|{}?{}?)[א-ת]{{0,3}}{}?'.format(self_ref_words, filler_words, parentheses, daf_words, parentheses, parentheses, daf_words, amud_words)
with codecs.open(filepath + 'commentary' + '_test4.tsv', 'wb+', 'utf-8') as csvfile:
    csvfile.write(u'Source\tOG Text\tText With Ref\n')
    for title in IndexSet({"$and": [{"categories": "Talmud"}, {"categories": "Commentary"},  {"schema.depth": 3}]}):
        # new_text_ja = jagged_array.JaggedArray([[]])
        # text_w_links = [[]]
        ref = Ref(title.title)
        text_chunk = TextChunk(ref, 'he')
        BASE_TEXT = Ref(ref.index.base_text_titles[0])
        BASE_TEXT_JA = TextChunk(BASE_TEXT, 'he').text
        text_len = len(BASE_TEXT_JA)
        for d1_idx, seg_text in enumerate(TEXT_JA):   
            # d1_w_links = []
            for d2_idx, d2 in enumerate(d1):
                for d3_idx, seg_text in enumerate(d2):
                    og_text = seg_text
                    offset = 0
                    for match in re.finditer(talmud_str, seg_text):
                        if (match.group(2) or match.group(17)) and isGematria(match.group(16)) and (text_len >= gematria(match.group(16))*2-1) and (gematria(match.group(16)) > 1):
                            insert = u'{} '.format(BASE_TEXT.he_normal()) 
                            if u'"' in match.group(16):
                                if not match.group(17) and not match.group(9) and not match.group(14):
                                    if re.search(ur'ע"[אב]', match.group(16)):
                                        insert += u'{} '.format(numToHeb(convert_index_to_daf(d1_idx)[:-1]))
                                    else:
                                        continue
                            text_changed = True
                            links_added += 1
                            for group_num in [9, 14, 16]:
                                # group 9 or 14 and if neither then before group 16
                                if match.start(group_num) > 0:
                                    start = match.start(group_num) + offset
                                    break
                            # if match.group(7) or match.group(12):
                            assert start
                            if match.group(7) or match.group(11) or match.group(12) or (seg_text[match.start()+offset-1] == u'(') or (u')' in re.sub(ur'(.*?)[\s$].*', ur'\1', seg_text[match.end()+offset:])):
                                # check for before and after for parentheses
                                seg_text = seg_text[:start] + insert + seg_text[start:]
                            else:
                                seg_text = seg_text[:start] + u'(' + insert + seg_text[start:match.end()+offset] + u')' + seg_text[match.end()+offset:]
                                offset += 2
                            
                            csvfile.write(u'{}\t{}\t{}\n'.format(
                                (ref.normal() + u' ' + convert_index_to_daf(d1_idx)+u'.'+unicode(d3_idx)),
                                og_text[match.start()-20:].strip(),
                                (ref.normal() + u' ' + convert_index_to_daf(d1_idx)+u'.'+unicode(d1_idx)),
                                og_text[match.start()-20:match.end()+len(insert)+1].strip(),
                                seg_text[match.start()-1+offset:match.end()+offset+len(insert)+1].strip()))
                            offset += len(insert)
                    new_text_ja.set_element([d1_idx], seg_text, u'')
        if text_changed:
            try:
                text_version = {
                    'versionTitle': text_chunk.version().versionTitle,
                    'versionSource': text_chunk.version().versionSource,
                    'language': 'he',
                    'text': new_text_ja.array(),
                }
                csvfile.write(u'{}\t{}\t{}\n'.format(title.title, links_added, text_chunk.version().versionTitle))
                # post_text(title.title, text_version)
                print "Changed: " + title.title + ' ' + text_chunk.version().versionTitle + " Version: " + text_chunk.version().versionSource
            except:
                print title.title + " is a merged text"
                csvfile.write(u'{}\t{}\t{}\n'.format(title.title, links_added, 'MERGED TEXT'))
# ''' 
# Test Suite
# תענית (פ"ב דף טז: ולקמן דף סג.) אשאש
# (לקמן דף מט:) אשאש
# (לקמן כו.) אשאש
# (לקמן ד' כט.) אשאש
# לעיל בפירקין (דף נב.) אשאש
# לקמן בפרק בית שמאי (דף מג.) אשאש
# לקמן באיזהו מקומן (דף מח.) אשאש
# לקמן בכל הזבחים שנתערבו (דף פב.) אשאש
# לקמן ילפינן לה בפירקין (כג:) אשאש
# תרי גווני הצעות יש דלקמן פ' אע"פ (דף נב.) אשאש
#  אשאשואמרינן לקמן (דף ה') אבל
# קורין בט"ו ועד כמה (לעיל דף ב ע"ב) א"ר
# והיינו כברייתא דלקמן צ"ה
# דפרישית בריש המניח (לעיל דף כ': ושם.):
# אינו רוצה כדפרישית לעיל (י"ח. ד"ה הא):
# מש בה, וכאותה שאמרו לקמן (מא, ב) שלשה
# ותלמידיו דלעיל פ"ו דף לט

# '''
