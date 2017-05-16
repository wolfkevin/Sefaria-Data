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

klal_titles = []
KlalTitle = namedtuple('KlalTitle', ['num', 'title'])

footnotes = {}  # needs to be a dict bc of double klalim
Footnote = namedtuple('Footnote', ['klal_num', 'comment_num', 'letter'])

klal_count = 0
comment_count = 0
ca_footnote_count = 0
local_foot_count = 0

CHELEK_BET_ADDITION = 69


tags = {}
tags['00'] = 'klal_num'
tags['11'] = 'klal_title'
tags['22'] = 'seif_num'
tags['33'] = 'comment'
tags['44'] = 'list_comment'
tags['99'] = 'footer'

mapping = dict.fromkeys(map(ord, u":.\n)"))  #chars to eliminate when parsing chayei adam numbers

def getKlalNum(klal):
    return getGematria(klal.find("klal_num").text.split()[1])

def getRidOfSofit(txt):
    if txt.find("ך")>=0:
        txt = txt.replace("ך", "כ")
    if txt.find("ם")>=0:
        txt = txt.replace("ם", "מ")
    if txt.find("ף")>=0:
        txt = txt.replace("ף", "פ")
    if txt.find("ץ")>=0:
        txt = txt.replace("ץ", "צ")
    return txt

def checkForFootnotes(line):

    global klal_count, comment_count, ca_footnote_count, local_foot_count

    while '#' in line:

        footnote_index = line.index('#')
        end_footnote = footnote_index + line[footnote_index:].find(' ')

        if end_footnote < footnote_index:  # when footnote appears at end of comment cant find ' '
            end_footnote = len(line)  # so use len of line as end_footnote index

        letter = unicode(line[footnote_index+1:end_footnote])
        # footnote_num = getGematria(letter)

        # if footnote_num is local_foot_count + 1 or footnote_num is 1:
        #     local_foot_count = footnote_num
        #
        # else:
        #     print "FOOTNOTE COUNT OFF", line

        # add footnote to array based off where it is found
        footnotes[ca_footnote_count] = Footnote(klal_count, comment_count, line, letter.translate(mapping))
        line = line.replace(line[footnote_index:end_footnote], u'<i data-commentator="{}" data-order="{}"></i>'.format("Nishmat Adam", ca_footnote_count))

        ca_footnote_count += 1


def checkAndEditTag(tag, line, file):

    global klal_count, comment_count, ca_footnote_count, local_foot_count

    if tag is 'list_comment':
        line = '<b>' + line.replace("@55", " </b> ", 1)

        checkForFootnotes(line)

    elif tag is 'klal_num':
        file.write("</klal><klal>")  # adding this makes it much easier to parse klalim

        local_foot_count = 0

        klal_num = getGematria(line.split()[1])


        if len(line.split()) > 2:  # abnormally long line

            if klal_num + 1 is getGematria(line.split()[2]):  # its a double klal
                klal_count += 2

            else:  # klal_title is on same line as klal and should be moved down and split
                file.write(u"<{}>{}</{}>".format(tag, ' '.join(line.split()[:2]), tag))  # write klal num to file
                tag ='klal_title'
                line = ' '.join(line.split()[2:])  # create klal title from rest of words that aren't klal num
                klal_count += 1

        elif klal_num is klal_count + 1 or klal_num + CHELEK_BET_ADDITION is klal_count + 1 or klal_num is 1:
            klal_count += 1

        else:
            print "KLAL NUMBER OFF", klal_num, klal_count



    elif tag is 'seif_num':

        comment_num = getGematria(line)

        if comment_num is comment_count + 1 or comment_num is 1:
            comment_count = comment_num

        else:  # TODO: weird case of ראוי here
            print "seif num off", line
            line = numToHeb(comment_count + 1)
            comment_count += 1

    elif tag is 'comment':

        checkForFootnotes(line)
        # print footnotes[ca_footnote_count]

    return tag, line

opener = urllib2.build_opener()
opener.addheaders = [('User-agent', 'Mozilla/5.0')]
page = opener.open("https://he.wikisource.org/w/index.php?title=%D7%97%D7%99%D7%99_%D7%90%D7%93%D7%9D&printable=yes")
soup = BeautifulSoup(page, 'html.parser')

header = soup.find(id=".D7.A1.D7.93.D7.A8_.D7.94.D7.99.D7.95.D7.9D")  # get seder hayom section
header = header.parent

section_start_num = 1  # start of first section of halachot
section_end_num = 0  # end is added to start

for section in header.find_next_siblings("h3"):
    bullets = section.find_next_sibling("ul")
    section_end_num = len(bullets.find_all("li")) + section_start_num - 1
    sections.append(Section(section.text, section_start_num, section_end_num))
    section_start_num = section_end_num + 1


with open("chayei_adam.txt") as file_read, open("ca_parsed.xml", "w") as file_write:

    file_write.write("<root><klal>")

    for line in file_read:

        if line[:1] is '$':
            tag = 'section'
            line = line[1:]

            if u'הלכות' not in line:
                tag = 'mini' + tag

        elif line[:1] is '@':
            tag = tags[line[1:3]]
            line = line[3:]
            tag, line = checkAndEditTag(tag, line, file_write)

        # else:
        #     tag = 'p'
        #     line = line.replace('@44', '<b>')
        #     line = line.replace('@55', '</b>')

        file_write.write(u"<{}>{}</{}>".format(tag, line.strip(), tag))

    file_write.write("</klal></root>")


klalim_ja = jagged_array.JaggedArray([[]])   # JA of [Klal[comment, comment]]]
nishmat_ja = jagged_array.JaggedArray([[]])  # JA of [Klal[footnote, footnote]]

with open("nishmat_adam.txt") as file_read:

    na_footnote_count = -1

    for line in file_read:

        if line[1:3] == '11':

            line = '<b>' + line[3:].strip().replace('@33', "</b>", 1)

            #TODO: D3 or leave as is
            nishmat_ja.set_element([footnote.klal_num - 1, getGematria(letter) - 1], line, "")

            if letter != footnote.letter:
                print "letters off "

            # print "klal:", footnote.klal_num, "#:", footnote.comment_num, "letter:", footnote.letter
            # print comment
            # print footnote.comment

        elif line[1:3] == '22':

            na_footnote_count += 1

            letter = unicode(line[line.index('(')+1:line.index(')')])
            footnote = footnotes[na_footnote_count]
            # print "\nfound:", letter, "from ca:", footnote.letter

        else:
            print "ERROR what is this", line

ja_to_xml(nishmat_ja.array(), ["klal", "footnote"])


with open("ca_parsed.xml") as file_read:

    soup = BeautifulSoup(file_read, 'lxml')

    found_sections = soup.find_all("section")

    start = 1 + CHELEK_BET_ADDITION  # all sections gotten from the text are from chelek bet

    for index, section in enumerate(found_sections):

        # end is 154 if this is last section
        # else find the heading of the last section klal before this next section and set that as klal end

        end = 154 if index + 1 >= len(found_sections) \
            else getKlalNum(found_sections[index].parent)

        end += CHELEK_BET_ADDITION
        sections.append(Section(section.text, start, end))
        start = end + 1


    prev_klal_num = 0
    addition = 0


    for klal in soup.find_all("klal")[1:]:  # [1:] because first klal is empty

        klal_num = getKlalNum(klal) + addition

        if klal_num < prev_klal_num:  # if the current klal > prev klal it means its the start of chelek bet
            addition = CHELEK_BET_ADDITION
            klal_num += addition

        comments = []

        klal_title = klal.find("klal_title")

        for index, comment in enumerate(klal.find_all("comment")):
            if klal_title:
                comments.append(u"<b>{}</b><br>{}".format(klal_title.text, comment.text))
                klal_title = ""
            else:
                comments.append(comment.text)
            # if comment.i:
            #     footnotes.append(Footnote(str(klal_num) + '.' + str(index), comments[comment.index('#')+1:comment]))

        klalim_ja.set_element([klal_num - 1], comments, [])

        if addition is not CHELEK_BET_ADDITION:  # once adding offset, no need to set prev_klal_num
            prev_klal_num = klal_num

ja_to_xml(nishmat_ja.array(), ["klal", "comment"])

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

# for section in sections:
#     map_node = SchemaNode()
#     map_node.add_title(section.title, "he", True)
#     map_node.add_title("temp", "en", True)
#     alt_schema.append(map_node)
#
#     start = section.start
#
#     for subtitle in subtitles[section.start:section.end]
#         map_node = ArrayMapNode()
#         map_node.add_title(subtitle.title, "he", True)
#         map_node.add_title(str(subtitle.klal_num), "en", True)
#         map_node.wholeRef = "Chayei Adam.{}".format(subtitle.klal_num)
#         map_node.includeSections = True
#         map_node.depth = 0
#         map_node.validate()
#
#     map_node.wholeRef = "Chayei Adam.{}-{}".format(section.start, section.end)
#     map_node.includeSections = True
#     map_node.validate()



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
- what are we doing with the subtitles @11's

Fixed:
- klalim restart = made it long running count and will have alt struct
- some klalim on other lines - parser splits this
- some klalim listed together (32, 33 #2) - skipped number and put it together
- klal 26 (#2) is empty
- no subtitle or partial (131 or 132 #2)




Nishmat Adam
- there are some 44's, 55's, 99, ?, ???
- only 2 @00
- @22 should be ordered
- do sections mean anything?

'''

# for footnote in footnotes:
#     links.append({
#         'refs': [
#             'Chayei Adam.{}.{}'.format(footnote.klal_num, footnote.comment_num)
#             'Nishmat Adam.{}.{}'.format(footnote.klal_num, getGematria(footnote.letter))
#         ],
#         'type': 'commentary',
#         'auto': True,
#         'generated_by': 'Nishmat Adam linker'
#     })
