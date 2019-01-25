# -*- coding: utf-8 -*-
import django
django.setup()
import re
from sefaria.helper.text import replace_roman_numerals
from sefaria.model import *
import json
from sources.functions import post_text


all_titles_reg = library.all_titles_regex('en', citing_only=True)
post = True

def remove_roman_and_repost(line, tref):
    new_line = u''
    prev_end = 0
    changed = False
    for match in all_titles_reg.finditer(line):
        title = match.group('title')
        check_text = line[match.start():match.end()-1] + replace_roman_numerals(line[match.end()-1:], only_lowercase=True)
        res = library._internal_ref_from_string(title, check_text, 'en', stIsAnchored=True, return_locations=True)  # Slice string from title start
        if res:
            ref = res[0][0]
            if not ref.is_talmud():
                new_line += line[prev_end:match.start()] + check_text[:res[0][1][1]]
                end = re.search(ur'[.:]', line[match.end():match.end()+10])
                if end:
                    changed = True
                    end = end.end() + match.end()
                    if len(ref.toSections) == 2:
                        end = line.find(str(ref.toSections[-1]), end)
                        if (end <= prev_end): 
                            print "bad enddd {}".format(line)
                        end += len(str(ref.toSections[-1]))
                    elif len(ref.toSections) > 2:
                        print "more than d2 ref {}".format(ref.normal())
                    if re.search(ur'.*\(.*\).*', check_text[:res[0][1][1]]):
                        end += 1
                    prev_end = end
    if changed and post:
        new_line += line[prev_end:]
        try:
            text_version = {
                'versionTitle': "Commentary of Ibn Ezra on Isaiah - trans. by M. Friedlander, 1873",
                'versionSource': "http://primo.nli.org.il/primo_library/libweb/action/dlDisplay.do?vid=NLI&docId=NNL_ALEPH001338443",
                'language': 'en',
                'text': new_line,
            }
            if post:
                post_text(tref, text_version)
            # linkified = library._wrap_all_refs_in_string(st=new_line, lang="en")
        except:
            pass

with open('Ibn Ezra on Isaiah - en - Commentary of Ibn Ezra on Isaiah - trans. by M. Friedlander, 1873.json') as f:
    data = json.load(f)
    text = data['text']
    for title in ["Translators Foreword", 'Prelude']:
        for idx1, line in enumerate(text[title]):
            remove_roman_and_repost(line, u'Ibn_Ezra_on_Isaiah, {}.{}'.format(title, idx1+1))
    for idx1, line1 in enumerate(text['']):
        for idx2, line2 in enumerate(line1):  
            for idx3, line in enumerate(line2):
                remove_roman_and_repost(line, u'Ibn_Ezra_on_Isaiah.{}.{}.{}'.format(idx1+1, idx2+1, idx3+1))
