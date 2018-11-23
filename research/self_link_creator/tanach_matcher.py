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
from sefaria.system.exceptions import BookNameError

post = True

def isGematria(txt):
    txt = normalize_final_letters_in_str(txt)
    txt = re.sub(ur'[\', ”״”":.\r\n)]', u'', txt)
    if txt.find(u"טו") >= 0:
        txt = txt.replace(u"טו", u"יה")
    elif txt.find(u"טז") >= 0:
        txt = txt.replace(u"טז", u"יו")

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
# filler_words = u"(ילפ|ב|פ(\'|\"))"
daf_words = ur"(?P<daf_prepend>(ב?ד[פף]?\'?)\.? )?"
daf_number = ur'(?P<daf_number>[״”״׳\'\"א-ת]+)'
parentheses = ur'(?P<parentheses>[\(\[{])'
amud_words = ur'(?P<amud>[:.]|(ע(מוד |[”״”"\']+)|,? )[אב])?'
perek_prepend = ur"(פ[׳\']|פרק|[רס][\"””״׳\']+פ) "

files_dict = {}
perakim_names = ur'(?P<perek_name>'

perek_to_mesechet_dict = {}
mesechet_to_alt_titles = {}
with codecs.open('perakim.txt', 'r', encoding='utf-8') as fr:
    for line in fr:
        values = line.split(u',')
        ref = Ref(values[0].strip())
        perek_to_mesechet_dict[values[2].strip()] = ref.he_book()
        mesechet_to_alt_titles[ref.he_book()] = ref.index.all_titles('he')
        perakim_names += values[2].strip() + ur'|'
    perakim_names = perakim_names[:-1] + ur').?.?'
    print(perakim_names)

filler_outside_words = ur'((ו?ב?(סוף|ריש)( הפרק)?|ופ["””״׳\']+ק דבתרא|בברייתא|תנן) )?'
filler_inside_words = ur'(?P<filler_inside>ו?ב?(סוף|ריש) )?'

perek_str = filler_outside_words + parentheses + filler_inside_words + daf_words + daf_number + amud_words
links_added = 0
base_text = None

def walk_thru_action(s, tref, heTref, version):
    global base_text
    global links_added
    global csvfile
    seg_text = u''
    pre_idx = 0
    offset = 0
    text_changed = False
    for match in re.finditer(perek_str, s):
        daf = match.group('daf_number')
        talmud_title = perek_to_mesechet_dict[match.group('perek_name')]
        # alt_titles = mesechet_to_alt_titles[talmud_title]
        if (isGematria(daf) and Ref().is_ref(talmud_title + u' ' + daf)) or daf == u'שם':
            text_changed = True
            links_added += 1
            indx = match.end('parentheses')
            if s[match.end()] == u')' or s[match.end()] == u']':
                seg_text += s[pre_idx:match.start('parentheses')] + u'(' + talmud_title + u' ' + s[indx:match.end()] + u')'
                pre_idx = match.end() + 1
            else:
                seg_text += s[pre_idx:indx] + talmud_title + u' ' + s[indx:match.end()]  
                pre_idx = match.end()
            csvfile.write(u'{}\t{}\t{}\n'.format(
                tref, s[match.start():match.end()+1].strip(),
                seg_text[match.start()+offset:].strip()))
            offset += len(talmud_title)+1
        else:
            pass
            # print tref
    seg_text += s[pre_idx:]
    if re.search(ur'ֿֿ[\(\[](ריש|סוף)', seg_text):
        print u"SEG TEXT: {}".format(seg_text) 
    if text_changed and post:
        try:
            text_version = {
                'versionTitle': version.versionTitle,
                'versionSource': version.versionSource,
                'language': 'he',
                'text': seg_text,
            }
            print post_text(tref, text_version)
        except:
            print u"Issue posting: {}".format(tref)
    return 


with codecs.open('test' + '.tsv', 'wb+', 'utf-8') as csvfile:
        # s is the segment string
        # tref is the segment's english ref
        # heTref is the hebrew ref
        # version is the segment's version object. use it to get the version title and language```
    
    # vs = VersionSet({"title": "Responsa Rav Pealim"})
    # vs = VersionSet({"title": "Nachal Eitan on Mishneh Torah, Divorce"})
    vs = VersionSet({"language": "he"})
    for v in vs:
        try:
            i = v.get_index()
            # if i.is_dependant_text():
            #     base_text = i.base_text_titles[0]
            #     if len(i.base_text_titles) > 1:
            #         print i.title + u' has multiple base texts'
            v.walk_thru_contents(walk_thru_action, heTref=i.get_title('he'), schema=i.schema)
        except BookNameError:
            print u"Skipping {}, {}".format(v.title, v.versionTitle)
            continue
        except Exception as e:
            print e, v.title, v.versionTitle
            continue
    print u"Links Added: {}".format(links_added)
    
