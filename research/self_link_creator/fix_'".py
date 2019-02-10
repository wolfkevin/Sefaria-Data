# -*- coding: utf-8 -*-
import django
django.setup()
from sefaria.model import *
import codecs
import pickle
import re
from sefaria.system.exceptions import InputError
from sources.functions import post_index, post_text, get_index_api
from sefaria.utils.hebrew import strip_nikkud, normalize_final_letters_in_str, gematria, has_cantillation
from data_utilities.util import numToHeb
from sefaria.datatype import jagged_array
from sefaria.model import *
from sefaria.system.exceptions import BookNameError

post = True

for idx in IndexSet():
    title_changed = False
    # i = get_index_api(idx._title)
    for title in idx.all_titles(lang='he'):
    # for t in i['schema']['titles']:
        # if t['lang'] == 'he':
        #     title = t['text']
            new_title = re.sub(ur'([\u0590-\u05FF])([\u2018\u2019\u0027][\u2018\u2019\u0027]|[\"“”])([\u0590-\u05FF])', ur'\1״\3', title)
            new_title = re.sub(ur'([\u2018\u2019\u0027][\u2018\u2019\u0027]|[“”])', ur'״', new_title)
            new_title = re.sub(ur'[\'\u2018\u2019]', ur'׳', new_title)        
            if title != new_title:
                # print(title)
                print(new_title)
                # i['schema']['titles'].append({'lang': 'he', 'text': u''.format(new_title)})
                idx.nodes.add_title(new_title, 'he')
                title_changed = True
    if title_changed and post:
        try:
            idx.save()
        except:
            print("issue posting {}".format(str(idx)))
        # post_index(i, weak_network=True) 
        
print "done with titles"
        
def walk_thru_action(s, tref, heTref, version):

    # hebrew letter, ugly quote, hebrew letter -> proper hebrew quote
    seg_text = re.sub(ur'([\u0590-\u05FF])([\u2018\u2019\u0027][\u2018\u2019\u0027]|[“”])([\u0590-\u05FF])', ur'\1״\3', s)
    # ugly quote -> american quote
    seg_text = re.sub(ur'([\u2018\u2019\u0027][\u2018\u2019\u0027]|[“”])', ur'"', seg_text)
    # hebrew letter, ugly single quote, hebrew letter -> geresh
    seg_text = re.sub(ur'([\u0590-\u05FF])[\u2018\u2019]([\u0590-\u05FF])', ur'\1׳\2', seg_text)
    # ugly quote -> american quote
    seg_text = re.sub(ur'[\u2018\u2019]', ur"'", seg_text)
    
    if post and (seg_text != s):
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

with codecs.open('fix' + '.tsv', 'wb+', 'utf-8') as csvfile:
        # s is the segment string
        # tref is the segment's english ref
        # heTref is the hebrew ref
        # version is the segment's version object. use it to get the version title and language```
    
    # vs = VersionSet({"title": "Siftei Kohen on Shulchan Arukh, Choshen Mishpat"})
    vs = VersionSet({"language": "he"})
    start_posting = True
    for v in vs:
        try:
            i = v.get_index()
            if (u'Chesed LeAvraham' not in i.get_title()) and (u'Rav Pealim' not in i.get_title()):
                # if u'Tosafot Yom Tov on Mishnah Oholot' in i.get_title():
                #     start_posting = True
                if start_posting:
                    v.walk_thru_contents(walk_thru_action, heTref=i.get_title('he'), schema=i.schema)
                    # if (u"B'Mareh HaBazak Volume VII" in i.get_title()):
                    #     start_posting = False
        except BookNameError:
            print u"Skipping {}, {}".format(v.title, v.versionTitle)
            continue
        except Exception as e:
            print e, v.title, v.versionTitle
            continue
