# -*- coding: utf8 -*-
import os, sys

import urllib2
from bs4 import BeautifulSoup

from collections import namedtuple

from sources.local_settings import *

sys.path.insert(0, SEFARIA_PROJECT_PATH)
os.environ['DJANGO_SETTINGS_MODULE'] = "sefaria.settings"

from data_utilities.util import ja_to_xml, traverse_ja, getGematria, numToHeb
from sefaria.datatype import jagged_array
from sources.functions import post_index, post_text
from sefaria.model import *


reload(sys)
sys.setdefaultencoding("utf-8")

sections = []
Section = namedtuple('Section', ['title', 'start', 'end'])

subtitles = []
Subtitle = namedtuple('Subtitle', ['klal_num', 'title'])

footnotes = {}
Footnote = namedtuple('Footnote', ['klal_num', 'comment_num', 'letter'])

klal_count = 0
comment_count = 0
footnote_count = 0

def checkAndEditTag(tag, line, file):

    global klal_count, comment_count, footnote_count

    if tag is 'ul':
        line = '<b>' + line.replace("@55", " </b> ", 1)

    elif tag is 'h1':
        file.write("</div><div>")  # adding this makes it much easier to parse klalim

        klal_num = getGematria(line.split()[1])

        if len(line.split()) > 2:  # abnormally long line

            if klal_num + 1 is getGematria(line.split()[2]):  # its a double klal
                klal_count += 2

            else:  # subtitle is on same line as klal and should be moved down and split
                file.write(u"<{}>{}</{}>".format(tag, ' '.join(line.split()[:2]), tag))
                tag ='h2'
                line = ' '.join(line.split()[2:])
                klal_count += 1

        elif klal_num is klal_count + 1 or klal_num is 1:
            klal_count = klal_num

        else:  # line is off and should be corrected
            line = u"כלל " + numToHeb(klal_count + 1)
            klal_count += 1

    elif tag is 'h3':

        comment_num = getGematria(line)

        if comment_num is comment_count + 1 or comment_num is 1:
            comment_count = comment_num

        else:  # TODO: weird case of ראוי here
            line = numToHeb(comment_count + 1)
            comment_count += 1

    elif tag is 'p':

        while '#' in line:

            footnote_index = line.index('#')
            end_footnote = line[footnote_index].find(' ')
            letter = line[footnote_index+1:end_footnote]
            footnote_num = getGematria(letter)

            if footnote_num is local_foot_count + 1 or footnote_num is 1:
                local_foot_count = footnote_num

            else:
                print "FOOTNOTE COUNT OFF", line

            footnotes[footnote_count] = Footnote(letter, klal_count, comment_count)

            if local_foot_count is not footnote_num:
                print "MISMATCHED COUNT AND GEMATRIA"

            line.replace(line[footnote_index:end_footnote], u'<i data-commentator="{}" data-order="{}"></i>').format("Nishmat Adam", footnote_count)
            footnote_count += 1

    return tag, line


tags = {}
tags['00'] = 'h1'
tags['11'] = 'h2'
tags['22'] = 'h3'
tags['33'] = 'p'
tags['44'] = 'p'
tags['99'] = 'footer'

opener = urllib2.build_opener()
opener.addheaders = [('User-agent', 'Mozilla/5.0')]
page = opener.open("https://he.wikisource.org/w/index.php?title=%D7%97%D7%99%D7%99_%D7%90%D7%93%D7%9D&printable=yes")
soup = BeautifulSoup(page, 'html.parser')

header = soup.find(id=".D7.A1.D7.93.D7.A8_.D7.94.D7.99.D7.95.D7.9D")  # get seder hayom section
header = header.parent

start = 1  # start of first section of halachot
end = 0  # end is added to start

for section in header.find_next_siblings("h3"):
    bullets = section.find_next_sibling("ul")
    end = len(bullets.find_all("li")) + start - 1
    sections.append(Section(section.text, start, end))
    start = end + 1


with open("chayei_adam.txt") as file_read, open("ca_parsed.xml", "w") as file_write:

    file_write.write("<root><div>")

    for line in file_read:

        if line[:1] is '$':
            tag = 'section'
            line = line[1:]

            if u'הלכות' not in line:
                tag = 'sub' + tag

        elif line[:1] is '@':
            tag = tags[line[1:3]]
            line = line[3:]
            tag, line = checkAndEditTag(tag, line, file_write)

        # else:
        #     tag = 'p'
        #     line = line.replace('@44', '<b>')
        #     line = line.replace('@55', '</b>')


        file_write.write(u"<{}>{}</{}>".format(tag, line.strip(), tag))


    file_write.write("</div></root>")

klalim_ja = jagged_array.JaggedArray([[]])   # JA of [Klal[comments]]]
nishmat_ja = jagged_array.JaggedArray([[]])  # JA of [Klal[footnote]]

with open("nishmat_adam.txt") as file_read:

    f_count = 0

    for line in file_read:

        if line[1:3] is '11':

            line = line.replace('@33', "</b>", 1)
            comment += '<br><b>' + line[3:].strip()

            if line.find('@'): print line

        elif line[1:3] is '22':

            letter = line[line.index('(')+1:line.index(')')]
            footnote = footnotes[f_count]

            if letter is not footnote.letter:
                print "letters off ", line

            nishmat_ja.set_element([footnote.klal_num - 1, getGematria(letter)], comment, "")
            f_count += 1
            comment = ""

        else: #TODO @11, @44, @99
            print "ERROR what is this", line


with open("ca_parsed.xml") as file_read:

    soup = BeautifulSoup(file_read, 'lxml')

    found_sections = soup.find_all("section")

    start = 1

    for index, section in enumerate(found_sections):

        # finds the heading of the last section klal before the next section
        # except for the last one which is manually set
        end = 154 if index + 1 >= len(found_sections) \
            else getGematria(found_sections[index + 1].find_previous_sibling("h1").text.split()[1])

        sections.append(Section(section.text, start, end))
        start = end + 1

    prev_klal_num = 0
    addition = 0

    for klal in soup.find_all("h1"):

        klal_num = getGematria(klal.text.split()[1]) + addition

        if klal_num < prev_klal_num:  # start of shabbat klalim
            addition = 69
            klal_num += addition

        comments = []

        for index, comment in enumerate(klal.find_next_siblings("p")):
            comments.append(comment.text)
            if comment.i:
                footnotes.append(Footnote(str(klal_num) + '.' str(index), comments[comment.index('#')+1:comment])))

        klalim_ja.set_element([klal_num - 1], comments, [])

        if addition is not 69:  # once adding offset, no need to set prev_klal_num
            prev_klal_num = klal_num

ja_to_xml(klalim_ja.array(), ["klal", "comment"])

links = []

# for comment in traverse_ja(klalim_ja.array()):
#     links.append({
#         'refs': [
#             # TODO: edit
#             # 'Shulchan_Arukh, Orach_Chayim.{}.{}'.format(comment['indices'][0] - 1, comment['indices'][1] - 1),
#             'Chayei Adam.{}.{}'.format(*[i - 1 for i in comment['indices']])
#         ],
#         'type': 'commentary',
#         'auto': True,
#         'generated_by': 'Chayei Adam linker'
#     })

index_schema = JaggedArrayNode()
index_schema.add_primary_titles("Chayei Adam", u"חיי אדם")
index_schema.add_structure(["Klal", "Comment"])
index_schema.validate()

alt_schema = SchemaNode()

for section in sections:
    map_node = SchemaNode()
    map_node.add_title(section.title, "he", True)
    map_node.add_title("temp", "en", True)
    alt_schema.append(map_node)

    start = section.start

    for subtitle in subtitles[section.start:section.end]
        map_node = ArrayMapNode()
        map_node.add_title(subtitle.title, "he", True)
        map_node.add_title(str(subtitle.klal_num), "en", True)
        map_node.wholeRef = "Chayei Adam.{}".format(subtitle.klal_num)
        map_node.includeSections = True
        map_node.depth = 0
        map_node.validate()

    map_node.wholeRef = "Chayei Adam.{}-{}".format(section.start, section.end)
    map_node.includeSections = True
    map_node.validate()



subtitle_schema = SchemaNode()



index = {
    "title": "Chayei Adam",
    "base_text_mapping": "commentary_increment_base_text_depth",
    "dependence": "Commentary",
    "categories": ["Halakhah", "Commentary", "Shulchan Arukh"],  # TODO: change
    "schema": index_schema.serialize(),
    "alt_structs": { "Categories": alt_schema.serialize() },
    "base_text_titles": ["Shulchan Arukh, Orach_Chayim"]  # TODO: change
}

post_index(index)

text_version = {
    'versionTitle': "Chayei Adam",
    'versionSource': "https://drive.google.com/drive/folders/0B4oYznKuBhPOV2twVGV2enpaTGM?usp=sharing",
    'language': 'he',
    'text': klalim_ja.array()
}

post_text("Chayei Adam", text_version)


# TODO: address questions:
'''
Questions:
- should we link from title all from OC kinda, some are siman, other si', others just in (), some link to 2 simanim, some x ad y (e.g 48), some 2 ()
- what is @44
- klal 61 is miswritten
- klal 26 (#2) is empty
- what are we doing with the subtitles @11's
- no subtitle or partial (131 or 132 #2)

Fixed:
- klalim restart = made it long running count and will have alt struct
- some klalim on other lines - parser splits this
- some klalim listed together (32, 33 #2) - skipped number and put it together



Nishmat Adam
- there are some 44's, 55's, 99, ?, ???
- only 2 @00
- @22 should be ordered
- do sections mean anything?

'''

for footnote in footnotes:
    links.append({
        'refs': [
            'Chayei Adam.{}.{}'.format(footnote.klal_num, footnote.comment_num)
            'Nishmat Adam.{}.{}'.format(footnote.klal_num, getGematria(footnote.letter))
        ],
        'type': 'commentary',
        'auto': True,
        'generated_by': 'Nishmat Adam linker'
    })
