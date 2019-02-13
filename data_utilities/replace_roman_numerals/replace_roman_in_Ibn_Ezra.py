# -*- coding: utf-8 -*-
import django
django.setup()
import re
from sefaria.helper.text import replace_roman_numerals
from sefaria.model import *
import json
from sources.functions import post_text
import codecs

filename = 'Pirkei DeRabbi Eliezer - en - Pirke de Rabbi Eliezer, trans. and annotated by Gerald Friedlander, London, 1916.json'
post = False 
versionTitle = ''
versionSource = ''


all_tanakh_titles = []

for index in IndexSet({"categories": "Tanakh", "is_cited": True}):
    if len(index.categories) == 2:
        all_tanakh_titles += index.all_titles(lang='en')
        
all_tanakh_titles.sort(key=len)
title_string = ur'\((' + ur'|'.join(sorted(map(re.escape, all_tanakh_titles), key=len)) + ur')'

ibid_reg = ur'(?P<ibid><i>ibid.</i>)(?P<ref> (?P<ref1>(m{0,4}(cm|cd|d?c{0,3})(xc|xl|l?x{0,3})(ix|iv|v?i{0,3}))\.)? ?(?P<ref2>\d+)?)(?:\D|$)'
all_titles_reg = library.all_titles_regex('en', citing_only=True)

def check_for_continuation(o_text, title, ref):
    continuation_match = re.search(ibid_reg, o_text)
    if continuation_match:
        capital_idx = re.search(ur'[A-Z]', o_text[:continuation_match.start()])
        if capital_idx:
            # title_idx = re.search(title_string, o_text[:continuation_match.start()])
            # if title_idx:
                return 0, u''
        new_ref = u''
        if continuation_match.group('ref1'):
            new_ref = title + replace_roman_numerals(continuation_match.group('ref'), only_lowercase=True)
        elif continuation_match.group('ref2'):    
            new_ref = title + u' ' + str(ref.toSections[0]) + u':' + continuation_match.group('ref2')
        else:
            print "no ref but ibid"
        # subtract = len(text)
        # text += o_text[continuation_match.start('ref'):]
        # 
        # res = library._internal_ref_from_string(title, text, 'en', stIsAnchored=True, return_locations=True)  # Slice string from title start
        # ref = None
        # if res:
        #     ref = res[0][0]
        #     post_idx = res[0][1][1] - subtract + pre_idx
        #     new_text += u'<a class="refLink" href="/{}" data-ref="{}">{}</a>'.format(ref.url(), ref.normal(), o_text[pre_idx:post_idx])
        #     self._current_entry['refs'].append(ref.normal())
        # 
        # new_idx, txt = self.check_for_continuation(o_text[post_idx:], ref, title)
        # post_idx += new_idx
        # new_text += txt
        text = o_text[:continuation_match.start()] + new_ref
        end = continuation_match.end('ref')
        try:
            r = Ref(new_ref)
            new_end, new_text = check_for_continuation(o_text[end:], title, r)
            return end + new_end, text + new_text  
        except:
            print o_text[end:end+20], title
    return 0, u''
    

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
                            print u"bad enddd {}".format(line[end:end+20])
                        end += len(str(ref.toSections[-1]))
                    elif len(ref.toSections) > 2:
                        print u"more than d2 ref {}".format(ref.normal())
                    if re.search(ur'.*\(.*\).*', check_text[:res[0][1][1]]):
                        end += 1
                    prev_end = end
                    # new_end, new_text = check_for_continuation(line[prev_end:], title, ref)
                    # new_line += new_text
                    # prev_end += new_end
    # return new_line + line[prev_end:]
    if changed and post:
        new_line += line[prev_end:]
        try:
            text_version = {
                'versionTitle': versionTitle,
                'versionSource': versionSource,
                'language': 'en',
                'text': new_line,
            }
            if post:
                post_text(tref, text_version)
            # linkified = library._wrap_all_refs_in_string(st=new_line, lang="en")
        except:
            pass
        
        
# filedata = None
# with codecs.open(filename, 'r', encoding='utf-8') as file:
#   filedata = file.read()
# 
# filedata = remove_roman_and_repost(filedata, None)
# 
# with codecs.open('new wo ibid {}'.format, 'w', encoding='utf-8') as file:
#     file.write(filedata)



with open(filename) as f:
    data = json.load(f)
    text = data['text']
    versionTitle = data['versionTitle']
    versionSource = data['versionSource']
    title = data['title']
    
    # for title in ["Translators Foreword", 'Prelude']:
    #     for idx1, line in enumerate(text[title]):
    #         remove_roman_and_repost(line, u'Ibn_Ezra_on_Isaiah, {}.{}'.format(title, idx1+1))
    # for idx1, line1 in enumerate(text[u'']):
    #     for idx2, line2 in enumerate(line1):  
    #         for idx3, line in enumerate(line2):
    #             remove_roman_and_repost(line, u'Ibn_Ezra_on_Isaiah.{}.{}.{}'.format(idx1+1, idx2+1, idx3+1))
    for idx1, line1 in enumerate(text):
        for idx2, line in enumerate(line1):  
            remove_roman_and_repost(line, u'{}.{}.{}'.format(title, idx1+1, idx2+1))


"""

verse 14:9
viz. 15:13
Ibid. 12:4
See Shemini, Section 4:9
"""
