# -*- coding: utf8 -*-
import os, sys

import urllib2
from bs4 import BeautifulSoup
import bleach

from collections import namedtuple

from sources.local_settings import *

sys.path.insert(0, SEFARIA_PROJECT_PATH)
os.environ['DJANGO_SETTINGS_MODULE'] = "sefaria.settings"

from data_utilities.util import ja_to_xml, traverse_ja, getGematria, numToHeb
from sefaria.datatype import jagged_array
from sources.functions import post_index, post_text, get_page, removeExtraSpaces
from sefaria.model import *


reload(sys)
sys.setdefaultencoding("utf-8")


par_c = 0
dh_c = 0

def checkAndEditTag(tag, line, file):
    global par_c
    global dh_c

    if tag is 'p':
        line = '<b> ' + line.replace("@12", " </b> ", 1) if "@12" in line \
            else '<b> ' + line.replace("@15", " </b> ", 1)

        # remove שם when it is first word b/c not useful
        if "שם" in line.split()[1]:
            line = line.replace(line.split()[1], "", 1)

            if "</b>" == line.split()[1]:
                line = line.replace("</b>", line.split()[2] + " </b>", 1)
                line = line.replace(line.split()[3], "", 1)

        # begining of comment so assume DH is everything before this word
        for word in ["פירוש", "פי'", 'ק"ל', "ופרשי"]:
            if word in line.split()[:20]:
                line = line.replace("</b>", "", 1)
                line = line.replace(word, " </b> " + word, 1)
                dh_c += 1
                print line

        # end of quote so assume DH ends right after this word
        for word in ["וכו'", "."]:
            if word in line.split()[:20]:
                line = line.replace("</b>", "", 1)
                line = line.replace(word, word + " </b> ", 1)
                dh_c += 1
                print line

        par_c += 1

    elif tag is 'h2':
        file.write("</daf><daf>")  # adding this makes it much easier to parse daf

    return line


tags = {}
tags['00'] = 'h1'
tags['11'] = 'p'
tags['14'] = 'p'
tags['22'] = 'h2'


sections = []
Section = namedtuple('Section', ['title', 'start', 'end'])


with open("ritva_yevamot.txt") as file_read, open("ry_parsed.xml", "w") as file_write:

    file_write.write("<root><daf>")

    for line in file_read:

        if line[:1] is '@':
            tag = tags[line[1:3]]
            line = line[3:].strip()

            line = checkAndEditTag(tag, line, file_write)
            file_write.write(u"<{}>{}</{}>".format(tag, line, tag))

        else:
            print "LINE ERROR\n", line

    file_write.write("</daf></root>")

daf_ja = jagged_array.JaggedArray([[]])  # JA of [Daf[], Daf[comment, comment]]


with open("ry_parsed.xml") as file_read:

    soup = BeautifulSoup(file_read, 'lxml')

    perek_start = "2a.0"
    perek_end = ""
    perek_title = u"חמש עשרה נשים"  # set first title manually
    prev_daf_count = 1

    for daf in soup.find_all("daf")[1:]:

        # getGematria and check if amud bet or aleph
        # daf_num = (getGematria(daf.h2.text.split()[1]) - 1) * 2 + 1 if daf.h2.text.split('"')[1] == u'ב' \
        #     else ((getGematria(daf.h2.text.split()[1]) - 1) * 2)

        daf_num = str(getGematria(daf.h2.text.split()[1])) + 'a' if daf.h2.text.endswith(u'א') \
            else str(getGematria(daf.h2.text.split()[1])) + 'b'

        comments = []
        comment_text = ""
        comment_num = 1  # so alt struct can know where to break

        for content in daf.children:

            if content.name is 'p':
                comments.append(bleach.clean(content, tags=['b'], strip=True))
                comment_num += 1

            elif content.name == 'h1':

                if content.previous_sibling.name == "h2":  # new chapter at beginning of daf
                    if daf_num.endswith('a'):
                        prev_daf_num = str(int(daf_num[:-1]) - 1)
                        prev_daf_num += 'b'
                    else:
                        prev_daf_num = daf_num[:-1] + 'a'

                    sections.append(Section(perek_title, perek_start, prev_daf_num + "." + str(prev_daf_count)))
                    perek_start = daf_num + "." + '1'

                else:
                    sections.append(Section(perek_title, perek_start, str(daf_num) + "." + str(comment_num)))
                    perek_start = str(daf_num) + "." + str(comment_num + 1)

                perek_title = ""
                for word in content.text.split()[2:]:
                    perek_title += word

        prev_daf_count = comment_num

        if comment_text:  # is a last comment that exists
            comments.append(bleach.clean(comment_text, tags=['b'], strip=True))
            print "does this happen?"

        daf_ja.set_element([get_page(int(daf_num[:-1]), daf_num[-1:])], comments, [])
    sections.append(Section(perek_title, perek_start, daf_num + "." + str(comment_num)))

ja_to_xml(daf_ja.array(), ["daf", "comment"])

print sections

links = []

for comment in traverse_ja(daf_ja.array()):
    links.append({
        'refs': [
            'Ritva on Yevamot.{}.{}'.format(*[i - 1 for i in comment['indices']])
        ],
        'type': 'commentary',
        'auto': True,
        'generated_by': 'Ritva on Yevamot linker'
    })

index_schema = JaggedArrayNode()
index_schema.add_primary_titles("Ritva on Yevamot", u'ריטב"א על יבמות')
index_schema.add_structure(["Daf", "Comment"], address_types=["Talmud", "Integer"])
index_schema.validate()


alt_schema = SchemaNode()

chapter_count = 0
for section in sections:
    map_node = ArrayMapNode()
    map_node.add_title(section.title, "he", True)
    map_node.add_title("Chapter" + str(chapter_count), "en", True)
    map_node.wholeRef = "Ritva on Yevamot.{}-{}".format(section.start, section.end)
    map_node.includeSections = True
    map_node.depth = 0
    map_node.validate()

    alt_schema.append(map_node)
    chapter_count += 1

index = {
    "title": "Ritva on Yevamot",
    "base_text_mapping": "commentary_increment_base_text_depth",
    "dependence": "Commentary",
    "categories": ["Talmud", "Commentary"],
    "schema": index_schema.serialize(),
    "alt_structs": { "Chapters": alt_schema.serialize() },
    "base_text_titles": ["Yevamot"]
}

text_version = {
    'versionTitle': "Ritva on Yevamot",
    'versionSource': "https://drive.google.com/drive/folders/0B4oYznKuBhPOV2twVGV2enpaTGM?usp=sharing",
    'language': 'he',
    'text': daf_ja.array()
}

# post_index(index)

# post_text("Ritva on Yevamot", text_version)


# TODO: address questions:
'''
Questions:=

'''
