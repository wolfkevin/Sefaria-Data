# -*- coding: utf8 -*-
import os, sys

import urllib2, bleach
from bs4 import BeautifulSoup
import re

from collections import namedtuple

from sources.local_settings import *

sys.path.insert(0, SEFARIA_PROJECT_PATH)
os.environ['DJANGO_SETTINGS_MODULE'] = "sefaria.settings"

from data_utilities.util import ja_to_xml, traverse_ja, getGematria, numToHeb
from sefaria.datatype import jagged_array
from sources.functions import post_index, post_text, post_link, add_term, removeExtraSpaces
from sefaria.model import *

reload(sys)
sys.setdefaultencoding("utf-8")

klal_count = 0
comment_count = 0
ca_footnote_count = 0
local_foot_count = 0

CHELEK_BET_ADDITION = 69

na_links = []
self_links = []

tags = {}
tags['00'] = 'klal_num'
tags['11'] = 'klal_title'
tags['22'] = 'seif_num'
tags['33'] = 'comment'
tags['44'] = 'list_comment'
tags['99'] = 'footer'

SelfLink = namedtuple('SelfLink', ['insert', 'offset'])

mapping = dict.fromkeys(map(ord, u":.\n)"))  # chars to eliminate when parsing chayei adam numbers

def isGematria(txt):
    txt = re.sub('[\', ":.\n)]', '', txt)
    if txt.find("טו")>=0:
        txt = txt.replace("טו", "יה")
    elif txt.find("טז")>=0:
        txt = txt.replace("טז", "יו")

    while txt[0] == u'ת':
        txt = txt[1:]

    if len(txt) == 1:
        if txt[0] < u'א' or txt[0] > u'ת':
            return False
    elif len(txt) == 2:
        if txt[0] < u'י' or (txt[0] < u'ק' and txt[1] > u'ט'):
            return False
    elif len(txt) == 3:
        if txt[0] < u'ק' or txt[1] < u'י' or txt[2] > u'ט':
            return False
    else:
        return False

    return True



def getKlalNum(klal):
    return getGematria(klal.find("klal_num").text.split()[1])

def getRidOfSofitAndDash(txt):
    if txt == None:
        print "pause"
    txt = re.sub('[\', ":.\n)]', '', txt)
    if txt.find("ך") >= 0:
        txt = txt.replace("ך", "כ")
    if txt.find("ם") >= 0:
        txt = txt.replace("ם", "מ")
    if txt.find("ף") >= 0:
        txt = txt.replace("ף", "פ")
    if txt.find("ץ") >= 0:
        txt = txt.replace("ץ", "צ")
    return txt


def selfLink(klal_num, siman_num, klal_link_num, siman_link_num):
    return {
        'refs': [
            "Chayei Adam.{}.{}".format(klal_num, siman_num),
            "Chayei Adam.{}.{}".format(klal_link_num, getGematria(getRidOfSofitAndDash(siman_link_num)))
        ],
        'type': 'reference',
        'auto': True,
        'generated_by': 'Chayei Adam self linker'
    }


def Ca2NaLink(ca_klal_num, ca_siman_number, na_siman_number):
    return {
        'refs': [
            "Chayei Adam.{}.{}".format(ca_klal_num, ca_siman_number),
            "Nishmat Adam.{}.{}".format(ca_klal_num, na_siman_number)
        ],
        'type': 'commentary',
        'auto': True,
        'generated_by': 'Chayei Adam to Nishmat Adam linker',
        'inline_reference': {
            'data-commentator': "Nishmat Adam",
            "data-order": na_siman_number
        }

    }


def checkForNaFootnotes(line):
    global klal_count, comment_count, ca_footnote_count, local_foot_count

    while '#' in line:

        footnote_index = line.index('#')
        end_footnote = footnote_index + line[footnote_index:].find(' ')

        if end_footnote < footnote_index:  # when footnote appears at end of comment cant find ' '
            end_footnote = len(line)  # so use len of line as end_footnote index

        letter = unicode(line[footnote_index + 1:end_footnote]).translate(mapping)

        footnotes[ca_footnote_count] = Footnote(klal_count, comment_count, letter)
        letter_num = getGematria(letter)
        na_links.append(Ca2NaLink(klal_count, comment_count, letter_num))

        ca_footnote_count += 1

        line = line.replace(line[footnote_index:end_footnote],
                            u'<i data-commentator="{}" data-order="{}"></i>'
                            .format("Nishmat Adam", letter_num))
    return line


def isADoubleKlal(klal_num, line):
    # type: (int, str) -> bool

    return klal_num + 1 is getGematria(line.split()[2])


def klalNumIsOff(klal_num, klal_count):
    # type: (int, int) -> bool

    return (klal_num is not klal_count + 1) \
           and (klal_num + CHELEK_BET_ADDITION is not klal_count + 1) \
           and (klal_num is not 1)


def checkAndEditTag(tag, line, file):
    # type: (str, str, file) -> (str, str)

    global klal_count, comment_count, ca_footnote_count, local_foot_count

    if tag is 'klal_num':
        file.write("</klal><klal>")  # adding this makes it much easier to parse klalim

        local_foot_count = 0

        klal_num = getGematria(line.split()[1])

        if len(line.split()) > 2:  # klal number should not be longer than 2 words

            if isADoubleKlal(klal_num, line):
                klal_count += 2

            else:  # klal_title is on same line as klal and should be moved down and split
                file.write(u"<{}>{}</{}>".format(tag, ' '.join(line.split()[:2]), tag))  # write klal num to file
                tag = 'klal_title'
                line = ' '.join(line.split()[2:])  # create klal title from rest of words that aren't klal num
                klal_count += 1

        elif klalNumIsOff(klal_num, klal_count):
            print "KLAL NUMBER OFF", klal_num, klal_count

        else:
            klal_count += 1

    elif tag is 'seif_num':

        comment_num = getGematria(line)

        if comment_num is comment_count + 1 or comment_num is 1:
            comment_count = comment_num

        else:  # TODO: weird case of ראוי here
            print "seif num off", line.strip()
            line = numToHeb(comment_count + 1)
            comment_count += 1

    elif 'comment' in tag:

        line = checkForNaFootnotes(line)

    # can also be footer or klal_title but those don't need to be edited

    return tag, line


def createLinkInsert(insert_offset, klal_link_num, siman_link, continuation_link=None):
    insert_text = u"(חיי אדם {}, {}".format(numToHeb(klal_link_num), getRidOfSofitAndDash(siman_link))
    if continuation_link:
        insert_text += u'-' + getRidOfSofitAndDash(continuation_link)
    return SelfLink(insert_text + u")", insert_offset)


def isContinuationLink(siman_1, siman_2):
    siman_2 = getRidOfSofitAndDash(siman_2)
    return (getGematria(getRidOfSofitAndDash(siman_1)) + 1 ==
            getGematria(siman_2)) and isGematria(siman_2)


def addMultipleSimanim(self_links_t, words, offset, klal_index, klal_link_num):
    # sometimes links to multiple simanim, so get all of them

    continuation_link = None
    separate_link = None

    siman_link = words[offset]

    while len(words) > offset + 1:

        if isContinuationLink(words[offset], words[offset+1]):
            if separate_link:
                separate_link = None
            offset += 1
            continuation_link = words[offset]

        elif u'וסי' in words[offset + 1]:
            if isContinuationLink(words[offset], words[offset+2]):
                if separate_link:
                    self_links_t.append(createLinkInsert(klal_index+offset, klal_link_num, siman_link, continuation_link))
                    siman_link = separate_link
                    separate_link = None
                continuation_link = words[offset + 2]

            else:
                self_links_t.append(createLinkInsert(klal_index+offset, klal_link_num, siman_link, continuation_link))
                separate_link = words[offset + 2]
                siman_link = separate_link

            offset += 2

        elif words[offset + 1][0] == u'ו' and isContinuationLink(words[offset], words[offset+1][1:]):
            if separate_link:
                self_links_t.append(createLinkInsert(klal_index+offset, klal_link_num, siman_link, continuation_link))
                siman_link = separate_link
                separate_link = None
            offset += 1
            continuation_link = words[offset][1:]

        else:
            break

    self_links_t.append(createLinkInsert(klal_index+offset, klal_link_num, siman_link, continuation_link))
    return


def isSiman(siman_word, siman_num):
    return any(sim in siman_word for sim in [u'דין', u"סי'", u'סימן'])\
            and isGematria(siman_num) \
            and getGematria(siman_num) < 58


def isRegularReference(word, comment_words, klal_index):
    return u'כלל' in word \
           and len(comment_words[klal_index:]) > 3 \
           and isSiman(comment_words[klal_index+2], comment_words[klal_index + 3])


def isReferenceToPreviousOrUpcoming(word, comment_words, klal_index):
    return (u'קמן' in word or u'עיל' in word) \
           and len(comment_words[klal_index:]) > 2 \
           and (not (u'כלל' in comment_words[klal_index + 1])) \
           and isSiman(comment_words[klal_index+1], comment_words[klal_index + 2])


def isReferenceToAnotherWork(comment_words, klal_index):
    return any(word in comment_words[klal_index - 1] for word in [u'אדם', u'נ"א', u'ח"א', u'ש"א', u'ת"ח']) \
           or ((len(comment_words[klal_index:]) > 4) and (u'נ"א' in comment_words[klal_index + 4]))


def referencesChelekBet(comment_words, klal_index):
    return any(word in comment_words[klal_index - 1] for word in [u"שבת", u"לולב", u"תענית", u"פסח"])


def isUpcoming(cur_siman, siman_link_num, cur_klal_num=0, klal_link_num=0):
    return klal_link_num > cur_klal_num or \
           (klal_link_num == cur_klal_num and siman_link_num > cur_siman)


def getKlalReferenceNum(comment_words, klal_index, cur_klal_num, cur_siman, addition):
    klal_link_num = getGematria(comment_words[klal_index + 1])

    if u'קודם' in comment_words[klal_index + 1]:
        klal_link_num = cur_klal_num - 1

    elif any(word in comment_words[klal_index - 1] for word in [u"ברכות", u"תפלה"]):
        pass

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

        elif line[1:3] == '22':

            na_footnote_count += 1

            letter = unicode(line[line.index('(')+1:line.index(')')])
            footnote = footnotes[na_footnote_count]

        else:
            print "ERROR what is this", line

with open("ca_parsed.xml") as file_read:

    soup = BeautifulSoup(file_read, 'lxml')

    found_sections = soup.find_all("section")

    start = 1 + CHELEK_BET_ADDITION  # all sections gotten from the text are from chelek bet

    for index, section in enumerate(found_sections):

        # end is 154 if this is last section
        # else find the heading of the last section klal before this next section and set that as klal end

        end = 154 if index + 1 >= len(found_sections) \
            else getKlalNum(found_sections[index+1].parent)

        end += CHELEK_BET_ADDITION
        sections.append(Section(section.text, start, end))
        start = end + 1

    addition = 0

    for klal in soup.find_all("klal")[1:]:  # [1:] because first klal is empty

        klal_num = getKlalNum(klal) + addition

        comments = []

        klal_title_added = False

        for siman, comment in enumerate(klal.find_all("comment")):

            if comment.text.find(u'כלל') != -1:  # check for self links in the text
                getSelfLinks(siman + 1, comment, klal_num, addition)

            if klal_title_added:
                print comment
                print comment.text
                print bleach.clean(comment, tags=['i'], attributes=['data-commentator', 'data-order'], strip=True)
                comments.append(bleach.clean(comment, tags=['i'], attributes=['data-commentator', 'data-order'], strip=True))
            else:
                comments.append(u"<big><strong>{}</strong></big><br>{}".format(klal.find("klal_title").text, comment.text))
                klal_title_added = True
            # if comment.i:
            #     footnotes.append(Footnote(str(klal_num) + '.' + str(index), comments[comment.index('#')+1:comment]))

        klalim_ja.set_element([klal_num - 1], comments, [])

        if klal_num == 69 and addition is 0:  # if the current klal > prev klal it means its the start of chelek bet
            addition = CHELEK_BET_ADDITION
            klal_num += addition


ja_to_xml(nishmat_ja.array(), ["klal", "siman"], "nishmat_output.xml")
ja_to_xml(klalim_ja.array(), ["klal", "siman"], "chayei_output.xml")

index_schema = JaggedArrayNode()
index_schema.add_primary_titles("Chayei Adam", u"חיי אדם")
index_schema.add_structure(["Klal", "Siman"])
index_schema.validate()

na_index_schema = JaggedArrayNode()
na_index_schema.add_primary_titles("Nishmat Adam", u"נשמת אדם")
na_index_schema.add_structure(["Klal", "Siman"])
na_index_schema.validate()

ca_alt_schema = SchemaNode()
na_alt_schema = SchemaNode()

for section in sections:

    map_node = ArrayMapNode()
    map_node.add_title(section.title, "he", True)
    map_node.add_title("temp", "en", True)
    map_node.wholeRef = "Chayei Adam.{}-{}".format(section.start, section.end)
    map_node.includeSections = True
    map_node.depth = 0

    map_node.validate()
    ca_alt_schema.append(map_node)

    na_map_node = map_node.copy()
    na_map_node.wholeRef = "Nishmat Adam.{}-{}".format(section.start, section.end)
    na_alt_schema.append(na_map_node)


ca_index = {
    "title": "Chayei Adam",
    "categories": ["Halakhah"],
    "schema": index_schema.serialize(),
    "alt_structs": { "Topic": ca_alt_schema.serialize() },
    "default_struct": "Topic"
}

na_index = {
    "title": "Nishmat Adam",
    "dependence": "Commentary",
    "categories": ["Halakhah", "Commentary", "Chayei Adam"],
    "schema": na_index_schema.serialize(),
    "alt_structs": { "Topic": na_alt_schema.serialize() },
    "base_text_titles": ["Chayei Adam"],
    "default_struct": "Topic"
}

add_term("Klal", u"כלל", scheme="section_names")

post_index(ca_index)
post_index(na_index)

ca_text_version = {
    'versionTitle': "Chayei Adam, Vilna, 1843",
    'versionSource': "http://primo.nli.org.il/primo_library/libweb/action/dlDisplay.do?vid=NLI&docId=NNL_ALEPH001873955",
    'language': 'he',
    'text': klalim_ja.array()
}

na_text_version = {
    'versionTitle': "Chayei Adam, Warsaw, 1888",
    'versionSource': "http://primo.nli.org.il/primo_library/libweb/action/dlDisplay.do?vid=NLI&docId=NNL_ALEPH001873393",
    'language': 'he',
    'text': nishmat_ja.array()
}

post_text("Chayei Adam", ca_text_version)
post_link(self_links)

post_text("Nishmat Adam", na_text_version)
post_link(na_links)



# TODO: address questions:
'''
Questions:
- should we link from title all from OC kinda, some are siman, other si', others just in (), some link to 2 simanim, some x ad y (e.g 48), some 2 ()
- what is @44

Fixed:
- klalim restart = made it long running count and will have alt struct
- some klalim on other lines - parser splits this
- some klalim listed together (32, 33 #2) - skipped number and put it together
- klal 26 (#2) is empty
- no subtitle or partial (131 or 132 #2)
- klal 61 is miswritten
- what are we doing with the subtitles @11's




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
