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

post = False

def isGematria(txt):
    txt = normalize_final_letters_in_str(txt)
    txt = re.sub(ur'[\', ׳”״”":.\r\n)]', u'', txt)
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

filler_chars = ur'[\(\[{\)\]\}\s.,:;]'
#skip (להלן|לעיל|לקמן) ((ילפ|ב|פ(\'|\")).{0,30}) (\(|\[)?((דף|ד\')(\.)? )?[א-ת]*
self_ref_words = u'(?P<self_ref_word>(להלן|לעיל|לקמן){}+)'.format(filler_chars)

# filler_words = u"(ילפ|ב|פ(\'|\"))"
number = ur'[״”״׳\'\"א-ת]'
perek_number = ur'(?P<perek_number>{}+)'.format(number)
pasuk_number = ur'(?P<pasuk_number>{}+)?'.format(number)
parentheses1 = ur'(?P<parentheses1>[\(\[{])'
parentheses2 = ur'(?P<parentheses2>[\(\[{])'
pasuk_words = ur'(?P<pasuk_words>(\u05e4\u05e1\u05d5\u05e7|ב?\u05e4["״׳\u05f4\u2018\u2019\u0027]*){}*)'.format(filler_chars)
perek_words = ur"(?P<perek_prepend>(פ['׳]|\u05e4\u05bc?\u05b6?\u05e8\u05b6?\u05e7(?:\u05d9\u05b4?\u05dd)?|[רס][\"”“״׳\']+פ)\s*)"

files_dict = {}
# perakim_names = ur'(?P<perek_name>'

perek_to_mesechet_dict = {}
mesechet_to_alt_titles = {}
# with codecs.open('perakim.txt', 'r', encoding='utf-8') as fr:
#     for line in fr:
#         values = line.split(u',')
#         ref = Ref(values[0].strip())
#         perek_to_mesechet_dict[values[2].strip()] = ref.he_book()
#         mesechet_to_alt_titles[ref.he_book()] = ref.index.all_titles('he')
#         perakim_names += values[2].strip() + ur'|'
#     perakim_names = perakim_names[:-1] + ur').?.?'
#     print(perakim_names)

filler_outside_words = ur'((ו?ב?(סוף|ריש)( הפרק)?|ופ["””״׳\']+ק דבתרא|בברייתא|תנן) )?'
filler_inside_words = ur'(?P<filler_inside>ו?ב?(סוף|ריש){}+)?'.format(filler_chars)

perek_pasuk_str = self_ref_words + filler_inside_words + perek_words + ur'?' + perek_number + pasuk_words + ur'?' + pasuk_number
perek_str = self_ref_words + filler_inside_words + perek_words + perek_number
pasuk_str = self_ref_words + filler_inside_words + pasuk_words + pasuk_number
links_added = 0
base_text = None
has_multiple_base_texts = False

def walk_thru_action(s, tref, heTref, version):
    global base_text
    global links_added
    global csvfile
    global has_multiple_base_texts
    seg_text = u''
    pre_idx = 0
    offset = 0
    text_changed = False
    # if re.search(self_ref_words, s):
    #     print "found"
    for match in re.finditer(pasuk_str, s):
        pasuk = match.group('pasuk_number')
        if isGematria(pasuk):
            if has_multiple_base_texts:
                print(tref)
                base_text = Ref(re.sub(ur'.*?,(.*?)(,.*|$)', ur'\1', tref)).index.get_title('he')
            # base_text_title = perek_to_mesechet_dict[match.group('perek_name')]
            insert = u'{} {}'.format(base_text, numToHeb(Ref(tref).sections[0]))
            ref = insert + u':{}'.format(pasuk)
            try:
                Ref(ref)._validate()
            except e:
                print(e)
            if Ref().is_ref(ref): 
                text_changed = True
                links_added += 1
                indx = match.end('self_ref_word')
                seg_text += s[pre_idx:indx] + base_text + u' ' + s[indx:match.end()+1]
                pre_idx = match.end() + 1
                # if s[match.end()] == u')' or s[match.end()] == u']':
                #     seg_text += s[pre_idx:match.start('self_ref_word')] + u'(' + base_text + u' ' + s[indx:match.end()] + u')'
                #     pre_idx = match.end() + 1
                # else:
                #     seg_text += s[pre_idx:indx] + base_text + u' ' + s[indx:match.end()+2]
                #     pre_idx = match.end() + 2
                    # pre_idx = match.end()
                csvfile.write(u'{}\t{}\t{}\n'.format(
                    tref, s[match.start():match.end()+1].strip(),
                    seg_text[match.start()+offset:].strip()))
                offset += len(base_text)+1
        elif pasuk == u'שם':
            if has_multiple_base_texts:
                print(tref)
                base_text = Ref(re.sub(ur'.*?,(.*?)(,.*|$)', ur'\1',tref)).index.get_title('he')
            pass
        else:
            pass
    for match in re.finditer(perek_str, s):
        perek = match.group('perek_number')
        if isGematria(perek):
            if has_multiple_base_texts:
                print(tref)
                base_text = Ref(re.sub(ur'.*?,(.*?)(,.*|$)', ur'\1', tref)).index.get_title('he')
            # base_text_title = perek_to_mesechet_dict[match.group('perek_name')]
            ref = u'{} {}'.format(base_text, perek)
            if match.group('pasuk_number'):
                ref += u':{}'.format(match.group('pasuk_number'))
            if Ref().is_ref(ref): 
                text_changed = True
                links_added += 1
                indx = match.end('self_ref_word')
                seg_text += s[pre_idx:indx] + base_text + u' ' + s[indx:match.end()+1]
                pre_idx = match.end() + 1
                # if s[match.end()] == u')' or s[match.end()] == u']':
                #     seg_text += s[pre_idx:match.start('self_ref_word')] + u'(' + base_text + u' ' + s[indx:match.end()] + u')'
                #     pre_idx = match.end() + 1
                # else:
                #     seg_text += s[pre_idx:indx] + base_text + u' ' + s[indx:match.end()+2]
                #     pre_idx = match.end() + 2
                    # pre_idx = match.end()
                csvfile.write(u'{}\t{}\t{}\n'.format(
                    tref, s[match.start():match.end()+1].strip(),
                    seg_text[match.start()+offset:].strip()))
                offset += len(base_text)+1
        elif perek == u'שם':
            if has_multiple_base_texts:
                print(tref)
                base_text = Ref(re.sub(ur'.*?,(.*?)(,.*|$)', ur'\1',tref)).index.get_title('he')
            pass
        else:
            pass

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
    
    # vs = VersionSet({"title": "Responsa Rav Pealim"})
    vs = VersionSet({"language": "he"})
    for idx in IndexSet({"$and": [{"categories": "Tanakh"}, {"categories": "Commentary"}, ]}):
        for v in VersionSet({"$and": [{"title": idx.title}, {"language": "he"}]}):
            try:
                i = v.get_index()
                if i.is_dependant_text():
                    base_text = Ref(i.base_text_titles[0]).index.get_title('he')
                    if len(i.base_text_titles) > 1:
                        has_multiple_base_texts = True
                        print i.title + u' has multiple base texts'
                    else:
                        has_multiple_base_texts = False
                else:
                    print u"{} has no base text".format(idx.title)
                v.walk_thru_contents(walk_thru_action, heTref=i.get_title('he'), schema=i.schema)
            except BookNameError:
                print u"Skipping {}, {}".format(v.title, v.versionTitle)
                continue
            except Exception as e:
                print e, v.title, v.versionTitle
                continue
    print u"Links Added: {}".format(links_added)
    
    
'''
 בריאה (לעיל פסוק א) וכן יעשה
 ים "רֶמֶשׂ הָאֲדָמָה" (פסוק כה) בעבור 
 למעלה (כב) כתוב
 פירשתי (לעיל פסוקים ד י יב) וטעם 
 ב (לעיל א כ-כד) בדג
 בהם (לעיל א כ כד)
 שהרי רש"י פירש למעלה (פסוק ד) שא
 "יִשְׁרְצוּ הַמַּיִם" (פסוק כ)
 (להלן ב ז) וַיִּיצֶר ה' אֱלֹהִים
'''
    
