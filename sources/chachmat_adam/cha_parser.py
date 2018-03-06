# -*- coding: utf8 -*-
import os, sys

import codecs, string

from collections import namedtuple

from sources.local_settings import *

sys.path.insert(0, SEFARIA_PROJECT_PATH)
os.environ['DJANGO_SETTINGS_MODULE'] = "sefaria.settings"

from data_utilities.util import ja_to_xml, traverse_ja, getGematria, numToHeb
from sefaria.datatype import jagged_array
from sources.functions import post_index, post_text, post_link, removeExtraSpaces
from sefaria.model import *

reload(sys)
sys.setdefaultencoding("utf-8")

shaarim = []
sections = []
Section = namedtuple('Section', ['title', 'start', 'end'])
prev_title = u'הלכות שחיטה'
prev_klal_num = 1

klal_titles = []
KlalTitle = namedtuple('KlalTitle', ['num', 'title'])

footnotes = {}  # needs to be a dict bc of double klalim
Footnote = namedtuple('Footnote', ['klal_num', 'comment_num', 'letter'])

klal_count = 1
comment_count = 0
ca_footnote_count = 0
local_foot_count = 0
cur_comment = ''
cur_klal_tile = u'דין מי הוא ראוי לשחוט'
prev_tag = ''

binat_links = []
self_links = []
chochmat_ja = jagged_array.JaggedArray([[]])

tags = {}
tags['00'] = 'klal_num'
tags['11'] = 'paragraph'
tags['22'] = 'klal_title'
tags['33'] = "reference_line"
tags['44'] = 'seif_num'
tags['55'] = 'begin_bold'
tags['66'] = 'end_bold'
tags['88'] = 'binat_comment'
tags['99'] = 'footer'

mapping = dict.fromkeys(map(ord, u":.\n)"))  # chars to eliminate when parsing Chochmat Adam numbers


def getKlalNum(klal):
    return getGematria(klal.find("klal_num").text.split()[1])

def checkIfWeShouldAddBr(comment):
    if comment != '':
        return comment + u'<br>'
    else:
        return ''

def getRidOfSofit(txt):
    if txt.find("ך") >= 0:
        txt = txt.replace("ך", "כ")
    if txt.find("ם") >= 0:
        txt = txt.replace("ם", "מ")
    if txt.find("ף") >= 0:
        txt = txt.replace("ף", "פ")
    if txt.find("ץ") >= 0:
        txt = txt.replace("ץ", "צ")
    return txt


def selfLink(klal_num, index, klal_link_num, par_index):
    return {
        'refs': [
            "Chochmat Adam.{}.{}".format(klal_num, index),
            "Chochmat Adam.{}.{}".format(klal_link_num, getGematria(getRidOfSofit(par_index)))
        ],
        'type': 'reference',
        'auto': True,
        'generated_by': 'Chochmat Adam self linker'
    }


def Ca2BaLink(ca_klal_num, ca_seif_number, ba_section_title, ba_seif_number):
    return {
        'refs': [
            "Chochmat Adam.{}.{}".format(ca_klal_num, ca_seif_number),
            "Binat Adam, {}.{}".format(ba_section_title, ba_seif_number)
        ],
        'type': 'reference',
        'auto': True,
        'generated_by': 'Chochmat Adam to Binat Adam linker'
    }


def tryAndSetBinatElement(title, count, comment):
    if comment != '' and count > 0:
        if count - 1 > 0 and count - 1 <= binat_shaarim_text[title].last_index(1)[0]:
            print "does this happen"
            return comment
        binat_shaarim_text[title].set_element([count - 1], removeExtraSpaces(comment.strip()))
        comment = ''
    return comment

def checkForFootnotes(line, symbol):
    global klal_count, comment_count, ca_footnote_count, local_foot_count

    while symbol in line:

        footnote_index = line.index(symbol)
        end_footnote = footnote_index + len(symbol) + 1

        while not any(x == line[end_footnote] for x in (string.whitespace + string.punctuation)):
            end_footnote += 1

        letter = line[footnote_index + len(symbol):end_footnote]
        # if local_foot_count + 1 != getGematria(letter):
        #     print(line)
        # else:
        #     local_foot_count += 1

        footnotes[ca_footnote_count] = Footnote(klal_count, comment_count, letter)
        line = line.replace(line[footnote_index:end_footnote],
                            u'<i data-commentator="{}" data-order="{}"></i>'.format("Binat Adam", getGematria(letter)), 1)

        ca_footnote_count += 1

    return line


# tags['00'] = 'klal_num'
# tags['11'] = 'paragraph'
# tags['22'] = 'klal_title'
# tags['33'] = "reference_line"
# tags['44'] = 'seif_num'
# tags['55'] = 'begin_bold'
# tags['66'] = 'end_bold'
# tags['88'] = 'binat_comment'
# tags['99'] = 'footer'

def checkAndEditTag(tag, line):
    global klal_count, comment_count, ca_footnote_count, local_foot_count, cur_comment

    if tag is 'klal_num':
        chochmat_ja.set_element([klal_count - 1, comment_count - 1], removeExtraSpaces(cur_comment.strip()), u"")
        cur_comment = ''

        # file.write("</klal><klal>")  # adding this makes it much easier to parse klalim

        klal_num = getGematria(line.split()[1])

        if klal_num == 75:
            klal_count += 14

        if klal_num > 74:  # 14 cencored klalim
            klal_num += 14

        if len(line.split()) > 2:  # abnormally long line

            if klal_num + 1 is getGematria(line.split()[2]):  # its a double klal
                print "double klal"
                klal_count += 2

            else:  # klal_title is on same line as klal and should be moved down and split
                print "abnormally long"
                file.write(u"<{}>{}</{}>".format(tag, ' '.join(line.split()[:2]), tag))  # write klal num to file
                tag = 'klal_title'
                line = ' '.join(line.split()[2:])  # create klal title from rest of words that aren't klal num
                klal_count += 1

        elif klal_num is klal_count + 1:
            klal_count += 1

        else:
            print "KLAL NUMBER OFF", klal_num, klal_count

    elif tag is 'paragraph' or tag is 'footer':

        line = checkForFootnotes(line, '@88')

        line = line.replace("@55", u' <b>')
        line = line.replace("@55", u'</b> ')

        cur_comment = checkIfWeShouldAddBr(cur_comment)
        cur_comment += line.strip()

    elif tag is 'klal_title':
        cur_comment = checkIfWeShouldAddBr(cur_comment)
        cur_comment += u'<big><strong>' + line.strip() + u'</strong></big>'

    elif tag is 'reference_line':
        cur_comment = checkIfWeShouldAddBr(cur_comment)
        cur_comment += line.strip()

    elif tag is 'seif_num':

        comment_num = getGematria(line)

        if comment_num != 1:
            chochmat_ja.set_element([klal_count - 1, comment_count - 1], removeExtraSpaces(cur_comment.strip()), u"")
            cur_comment = ''

        if comment_num is comment_count + 1 or comment_num is 1:
            comment_count = comment_num

        else:
            print "klal " + str(klal_count - 14) + " seif num off ", line
            line = numToHeb(comment_count + 1)
            comment_count += 1

    # return tag, line


# def getSelfLinks(index, comment, klal_num, addition):
#     comment_words = comment.text.split()
#
#     for klal_index, word in enumerate(comment_words):
#
#         # self links formatted as:  ___ 'כלל ___ סי
#
#         if u'כלל' in word \
#                 and len(comment_words[klal_index:]) > 3 \
#                 and any(word in comment_words[klal_index+2] for word in [u'דין', u"סי'", u'סימן']) \
#                 and getGematria(comment_words[klal_index+1]) < 224 \
#                 and getGematria(comment_words[klal_index+3]) < 58:
#             # and not any(word in comment_words[klal_index-1] for word in [u'אדם', u'ח"א', u'ש"א', u'נ"א']) \
#
#             # if reference to other of his works before reference
#             if any(word in comment_words[klal_index-1] for word in [u'אדם', u'ח"א', u'ש"א', u'נ"א']):
#                 #     for t_word in comment_words[klal_index-3:klal_index+4]:
#                 #         print t_word
#                 #     print "\n"
#                 continue
#
#             # if reference to other work after reference
#             if len(comment_words[klal_index:]) > 4 \
#                     and any(word in comment_words[klal_index+4] for word in [u'נ"א']):
#                 #     for t_word in comment_words[klal_index-2:klal_index+5]:
#                 #         print t_word
#                 #     print "\n"
#                 continue
#
#             klal_link_num = getGematria(comment_words[klal_index+1])
#
#             # print comment_words[klal_index-1]
#             if comment_words[klal_index+1] == u'הקודם':
#                 klal_link_num = klal_num - 1
#
#             elif any(word in comment_words[klal_index-1] for word in [u"ברכות", u"תפלה"]):
#                 if klal_link_num > CHELEK_BET_ADDITION:
#                     print "I thought you were a tefillah or brachot", comment_words[klal_index+1], "in", klal_num, "seif", index+1
#
#             elif any(word in comment_words[klal_index-1] for word in [u"שבת", u"לולב", u"תענית", u"פסח"]):
#                 klal_link_num += CHELEK_BET_ADDITION
#
#             else:
#                 if addition is not 0 and klal_num is not 207:
#                     klal_link_num += CHELEK_BET_ADDITION
#
#                 if u'קמן' in comment_words[klal_index-1] or u'קמן' in comment_words[klal_index-2]:
#                     if klal_num > klal_link_num:
#                        print "you should be more", comment_words[klal_index+1], "in", klal_num, "seif", index+1
#
#                 elif u'עיל' in comment_words[klal_index-1] or u'עיל' in comment_words[klal_index-2]:
#                     if klal_link_num > klal_num:
#                        print "you should be less happenend", comment_words[klal_index+1], "in", klal_num, "seif", index+1
#
#             offset = 3
#
#             # sometimes links to multiple simanim, so get all of them
#             while len(comment_words[klal_index:]) > offset + 2:
#                 if getGematria(getRidOfSofit(comment_words[klal_index+offset])) + 1 \
#                         == getGematria(getRidOfSofit(comment_words[klal_index+offset+1])):
#                     self_links.append(selfLink(klal_num, index+1, klal_link_num, comment_words[klal_index+offset+1]))
#                     offset += 1
#
#                 else:
#                     if u'וסי' in comment_words[klal_index+4]:
#                         self_links.append(selfLink(klal_num, index+1, klal_link_num, comment_words[klal_index+5]))
#                     break
#
#             self_links.append(selfLink(klal_num, index+1, klal_link_num, comment_words[klal_index+3]))

kuntrus_dict = {}
kuntrus_ja = jagged_array.JaggedArray([[]])
section_num = 0

startedKuntrus = False
prev_shaar_title = u'שער איסור והיתר'
start_shaar_num = 1

with codecs.open("chachmat_adam.txt") as file_read:
    for line in file_read:

        if startedKuntrus:
            if '$' in line[:2]:
                kuntrus_ja.set_element([section_num, comment_count - 1], removeExtraSpaces(cur_comment), u"")
                section_num += 1
                # kuntrus_dict[unicode(prev_title)].set_element([comment_count - 1], removeExtraSpaces(cur_comment), u"")
                prev_title = line[1:].strip()
                cur_comment = ''
                kuntrus_dict[unicode(prev_title)] = jagged_array.JaggedArray([])
            elif '@11' in line[:3] or '@77' in line[:3]:
                cur_comment = checkIfWeShouldAddBr(cur_comment)
                cur_comment += line[3:].strip()
            elif '@44' in line[:3]:
                comment_num = getGematria(line[3:])
                if cur_comment != '':
                    kuntrus_ja.set_element([section_num, comment_count - 1], removeExtraSpaces(cur_comment), u"")
                    # kuntrus_dict[unicode(prev_title)].set_element([comment_count - 1], removeExtraSpaces(cur_comment), u"")
                    cur_comment = ''
                if comment_num is comment_count + 1 or comment_num is 1:
                    comment_count = comment_num

        elif line[0] is '$':
            tag = 'section'
            sections.append(Section(prev_title, prev_klal_num, klal_count))
            prev_title = line[1:].strip()
            prev_klal_num = klal_count + 1
            local_foot_count = 0
            if u'קונטרס מצבת משה' in line:
                startedKuntrus = True
                chochmat_ja.set_element([klal_count - 1, comment_count - 1], removeExtraSpaces(cur_comment), u"")
                cur_comment = ''
                kuntrus_dict[unicode(prev_title)] = jagged_array.JaggedArray([])
                
        elif line[0] is '!':
            shaarim.append(Section(prev_shaar_title, start_shaar_num, klal_count))
            prev_shaar_title = line[1:].strip()
            start_shaar_num = klal_count + 1

        elif line[:1] is '@':
            tag = tags[line[1:3]]
            line = line[3:]
            checkAndEditTag(tag, line)

            # tag, line = checkAndEditTag(tag, line, file_write)

        else:
            print "what is this " + line

kuntrus_ja.set_element([section_num, comment_count - 1], removeExtraSpaces(cur_comment), u"")
# kuntrus_dict[unicode(prev_title)].set_element([comment_count - 1], removeExtraSpaces(cur_comment), u"")

klal_count = 74
comment_count = 0
local_foot_count = 66
cur_comment = ''

with codecs.open("ca_missing.txt") as file_read:
    for line in file_read:
        if len(line) > 2:
            # print line[0]
            # line=line.decode('utf-8','ignore').encode("utf-8")

            if '$' in line or '@' in line:
                if cur_comment != '' and comment_count != 0:
                    chochmat_ja.set_element([klal_count - 1, comment_count - 1], removeExtraSpaces(cur_comment))
                    cur_comment = ''
                if '$' in line:
                    klal_count += 1
                    comment_count = 0
                elif '@' in line:
                    comment_count += 1
                else:
                    print "weird addition " + line

            else:
                if cur_comment != '':
                    cur_comment += u'<br>'

                if '#' in line:
                    cur_comment += u'<big><strong>' + line[1:].strip() + u'</strong></big>'
                else:
                    cur_comment += line.strip()
                    checkForFootnotes(line, '%')

    chochmat_ja.set_element([klal_count - 1, comment_count - 1], removeExtraSpaces(cur_comment))

binat_ja = jagged_array.JaggedArray([[]])  # JA of [Klal[footnote, footnote]]
section_title = u'שער רוב וחזקה'
section_start = 0
siman_count = 0
ba_footnote_count = 0
comment_count = 0
small_title = ''

shaarim_order = []
shaarim_order.append(section_title)

eng_titles_dict = {
    u'שער רוב וחזקה': 'Shaar Rov Vechazaka',
    u'שער הקבוע': 'Shaar haKavua',
    u'שער איסור והיתר': 'Shaar Isur Veheter',
    u'שער בית הנשים': 'Shaar Beit haNashim',
    u'שער משפטי צדק': 'Shaar Mishpetei Tzedek',
    u'שער רנה וישועה': 'Shaar Rinah Vishuah',
    u'שער השמחה': 'Shaar haSimcha',
}

binat_shaarim_text = {}
binat_shaarim_text[section_title] = jagged_array.JaggedArray([])


with codecs.open("binat_adam.txt") as file_read:

    for line in file_read:
        # print line

        if line[1:3] == '00':
            if cur_comment != '':
                binat_shaarim_text[section_title].set_element([comment_count - 1], removeExtraSpaces(cur_comment))
                cur_comment = ''
            # binat_sections.append(Section(section_title, section_start, comment_count))
            section_title = line[3:].strip()
            # section_start = comment_count
            comment_count = 0
            binat_shaarim_text[section_title] = jagged_array.JaggedArray([])
            if section_title != u'כללי ספק ספיקא ממנחת יעקב':
                shaarim_order.append(section_title)

        elif line[1:3] == '11' or line[1:3] == '55' or line[1:3] == '88' or line[1:3] == '99':
            if small_title != '':
                cur_comment = checkIfWeShouldAddBr(cur_comment)
                cur_comment += small_title
                small_title = ''
            line = line[3:].strip()
            cur_comment = checkIfWeShouldAddBr(cur_comment)
            cur_comment += u'<b>' + line.replace(u'@12', u"</b> ", 1)
            cur_comment = cur_comment.replace(u'@56', u'</b> ', 1)

        elif line[1:3] == '22' and len(binat_shaarim_text) > 3 and section_title != u'שער משפטי צדק':
            letter = line[3:line.index(' ', 3)]
            cur_comment = checkIfWeShouldAddBr(cur_comment)
            cur_comment += u'<b>' + line[3:].strip() + u'</b>'
            if footnotes[ba_footnote_count].letter != letter:
                print "ca letter " + footnotes[ba_footnote_count].letter + " " + str(footnotes[ba_footnote_count].klal_num) + " " + str(footnotes[ba_footnote_count].comment_num) + " vs footnote we think we are up to " + line
                
            else:
                ba_footnote_count += 1
                binat_links.append(Ca2BaLink(footnotes[ba_footnote_count].klal_num, footnotes[ba_footnote_count].klal_num, eng_titles_dict[unicode(section_title)], comment_count))
                if len(line) > 11:
                    binat_links.append(Ca2BaLink(footnotes[ba_footnote_count].klal_num, footnotes[ba_footnote_count].klal_num, eng_titles_dict[unicode(section_title)], comment_count))
                    ba_footnote_count += 1               

        elif line[1:3] == '66' or line[1:3] == '22':
            if cur_comment != '' and comment_count > 0:
                binat_shaarim_text[section_title].set_element([comment_count - 1], removeExtraSpaces(cur_comment))
                cur_comment = ''
                if small_title != '':
                    cur_comment += small_title
                    small_title = ''
            letter = line[line.index('(', 3):line.index(')', 3)] if line[1:3] == '66' else line[3:line.index(' ', 3)] 
            if getGematria(letter) == comment_count + 1:
                comment_count += 1
                if line.find('44', 5) > 0:
                    cur_comment = checkIfWeShouldAddBr(cur_comment)
                    cur_comment += u'<big><strong>' + line[line.index('44', 5)+2:].strip() + u'</strong></big>'
                elif len(line.strip()) > 11:
                    comment_count += 1                        
            else:
                print "comment count off " + line
                comment_count = getGematria(letter)
        elif line[1:3] == '77':
            small_title = u'<b>' + line[3:].strip() + u'</b>'
            if u'לכלל' in small_title:
                klal_idx_1 = small_title.index(' ', 8)
                klal_idx_2 = small_title.index(' ', klal_idx_1+1)
                klal_num = getGematria(small_title[klal_idx_1+1:klal_idx_2])
                siman_idx_1 = small_title.index(' ', klal_idx_2+1)
                siman_idx_2 = small_title.index(u'<', siman_idx_1)
                siman_num = getGematria(small_title[siman_idx_1+1:siman_idx_2])
                binat_links.append(Ca2BaLink(klal_num, siman_num, eng_titles_dict[unicode(section_title)], comment_count + 1))
            
        else:
            print "what is " + line
            
        # elif line[1:3] == '22':
        #
        #     na_footnote_count += 1
        #
        #     letter = unicode(line[line.index('(') + 1:line.index(')')])
        #     footnote = footnotes[na_footnote_count]

        # else:
        #     print "ERROR what is this", line

    # binat_sections.append(Section(section_title, section_start, siman_count))
    # binat_shaarim_text[section_title].set_element([comment_count - 1], removeExtraSpaces(cur_comment.strip()))

for item in binat_shaarim_text:
    ja_to_xml(binat_shaarim_text[item].array(), ["siman"], item + "_output.xml")

#
#             else:

ja_to_xml(chochmat_ja.array(), ["klal", "siman"], "chochmat_output.xml")
# ja_to_xml(later_jas[0].array(), ["siman"], "mmi_output.xml")
# ja_to_xml(later_jas[1].array(), ["siman"], "mm_output.xml")
# ja_to_xml(later_jas[2].array(), ["siman"], "cki_output.xml")
# ja_to_xml(later_jas[3].array(), ["siman"], "ck_output.xml")

ja_to_xml(binat_ja.array(), ["klal", "siman"], "binat_output.xml")

ca_index_schema = SchemaNode()
ca_index_schema.add_primary_titles("Chochmat Adam", u"חכמת אדם")

intro_node = JaggedArrayNode()
intro_node.add_primary_titles("Author's Introduction", u"הקדמת המחבר")
intro_node.add_structure(['Comment'])
intro_node.validate()
ca_index_schema.append(intro_node)

ca_default = JaggedArrayNode()
ca_default.add_structure(["Klal", "Siman"])
ca_default.key = "default"
ca_default.default = True
ca_default.validate()
ca_index_schema.append(ca_default)

matzevet_moshe_schema = SchemaNode()
matzevet_moshe_schema.add_primary_titles("Kuntres Matzevet Moshe", u"קונטרס מצבת משה")

matzevet_moshe_default = JaggedArrayNode()
matzevet_moshe_default.add_structure(["Klal", "Siman"])
matzevet_moshe_default.key = "default"
matzevet_moshe_default.default = True
matzevet_moshe_schema.append(matzevet_moshe_default)
ca_index_schema.append(matzevet_moshe_schema)

ca_index_schema.validate()

ca_halacha_schema = SchemaNode()

alt_intro_node = ArrayMapNode()
alt_intro_node.add_primary_titles("Author's Introduction", u"הקדמת המחבר")
alt_intro_node.wholeRef = "Chochmat Adam, Author's Introduction"
alt_intro_node.depth = 0
ca_halacha_schema.append(alt_intro_node)

for section in sections:
    if section.start == 51:  # censored section makes you have to do this manually
        censored_map_node_1 = ArrayMapNode()
        censored_map_node_1.add_primary_titles("temp", section.title)
        censored_map_node_1.wholeRef = "Chochmat Adam.{}-{}".format(section.start, 64)
        censored_map_node_1.includeSections = True
        censored_map_node_1.depth = 0
        ca_halacha_schema.append(censored_map_node_1)
        censored_map_node_2 = ArrayMapNode()
        censored_map_node_2.add_primary_titles("temp", u'הלכות מאכלי עכו"ם')
        censored_map_node_2.add_title("temp", "en", True)
        censored_map_node_2.wholeRef = "Chochmat Adam.{}-{}".format(65, 74)
        censored_map_node_2.includeSections = True
        censored_map_node_2.depth = 0
        ca_halacha_schema.append(censored_map_node_2)
        censored_map_node_3 = ArrayMapNode()
        censored_map_node_3.add_primary_titles("temp", u'הלכות יין נסך')
        censored_map_node_3.wholeRef = "Chochmat Adam.{}-{}".format(75, 83)
        censored_map_node_3.includeSections = True
        censored_map_node_3.depth = 0
        ca_halacha_schema.append(censored_map_node_3)
        censored_map_node_4 = ArrayMapNode()
        censored_map_node_4.add_primary_titles("temp", u'הלכות עבודת כוכבים')
        censored_map_node_4.wholeRef = "Chochmat Adam.{}-{}".format(84, section.end)
        censored_map_node_4.includeSections = True
        censored_map_node_4.depth = 0
        ca_halacha_schema.append(censored_map_node_4)
    else:
        map_node = ArrayMapNode()
        map_node.add_primary_titles("temp", section.title)
        map_node.wholeRef = "Chochmat Adam.{}-{}".format(section.start, section.end)
        map_node.includeSections = True
        map_node.depth = 0
        map_node.validate()
        ca_halacha_schema.append(map_node)

map_node = ArrayMapNode()
map_node.add_primary_titles("Kuntres Matzevet Moshe", u"קונטרס מצבת משה")
map_node.wholeRef = "Chochmat Adam, Kuntres Matzevet Moshe.{}-{}".format(1, 1)
map_node.includeSections = True
map_node.depth = 0
map_node.validate()
ca_halacha_schema.append(map_node)

map_node = ArrayMapNode()
map_node.add_primary_titles("temp", u"הנהגת חברה קדישא")
map_node.wholeRef = "Chochmat Adam, Kuntres Matzevet Moshe.{}-{}".format(2, 2)
map_node.includeSections = True
map_node.depth = 0
map_node.validate()
ca_halacha_schema.append(map_node)

ca_shaar_schema = SchemaNode()

ca_shaar_schema.append(alt_intro_node)

for shaar in shaarim:
    map_node = ArrayMapNode()
    map_node.add_primary_titles(eng_titles_dict[unicode(shaar.title)], shaar.title)
    map_node.wholeRef = "Chochmat Adam.{}-{}".format(shaar.start, shaar.end)
    map_node.includeSections = True
    map_node.depth = 0
    map_node.validate()
    ca_shaar_schema.append(map_node)

ca_index = {
    "title": "Chochmat Adam",
    "categories": ["Halakhah"],
    "schema": ca_index_schema.serialize(),
    "alt_structs": {
        "Topic": ca_halacha_schema.serialize(),
        "Shaar": ca_shaar_schema.serialize(),
    },
    "default_struct": "Topic"
}

ca_text_version = {
    'versionTitle': "Hokhmat Adam, Vilna, 1844",
    'versionSource': "http://dlib.rsl.ru/viewer/01006560322#?page=5",
    'language': 'he',
    'text': chochmat_ja.array()
}
ca_kuntres_text_version = {
    'versionTitle': "Hokhmat Adam, Vilna, 1844",
    'versionSource': "http://dlib.rsl.ru/viewer/01006560322#?page=5",
    'language': 'he',
    'text': kuntrus_ja.array()
}

post_ca = True
if post_ca:
    
    post_index(ca_index)
    post_text("Chochmat Adam", ca_text_version)
    post_text("Chochmat Adam, Kuntres Matzevet Moshe", ca_kuntres_text_version)
    # post_link(self_links)
    
post_ba = False
if post_ba:
    ba_index_schema = SchemaNode()
    ba_index_schema.add_primary_titles("Binat Adam", u"בינת אדם")
    
    for shaar_title in shaarim_order:
        if shaar_title == u'שער הקבוע':
            shaar_hakavua_schema = SchemaNode()
            ba_index_schema.add_primary_titles(eng_titles_dict[unicode(shaar_title)], shaar_title)
            ba_ja = JaggedArrayNode()
            ba_ja.add_structure(["Siman"])
            ba_ja.key = 'default'
            ba_ja.default = True
            ba_ja.validate()
            shaar_hakavua_schema.append(ba_ja)
            ss_ja = JaggedArrayNode()
            ss_ja.add_structure(["Siman"])
            ss_ja.key = 'Principles of Double Doubt from Minchat Yaakov'
            ss_ja.validate() 
            shaar_hakavua_schema.append(ss_ja)
            ba_index_schema.append(shaar_hakavua_schema)
            
        else: 
            ba_ja = JaggedArrayNode()
            ba_ja.add_structure(["Siman"])
            ba_ja.key = eng_titles_dict[unicode(shaar_title)]
            ba_ja.validate()
            ba_index_schema.append(ba_ja)

    ba_index = {
        "title": "Binat Adam",
        "dependence": "Commentary",
        "categories": ["Halakhah", "Commentary"],
        "schema": ba_index_schema.serialize(),
        "base_text_titles": ["Chochmat Adam"],
    }
    post_index(ba_index)
    
    for shaar_title, shaar_text in binat_shaarim_text:
        ba_text_version = {
            'versionTitle': "Hokhmat Adam, Vilna, 1844",
            'versionSource': "http://dlib.rsl.ru/viewer/01006560322#?page=5",
            'language': 'he',
            'text': shaar_text.array()
        }
        
        if shaar_title == u'כללי ספק ספיקא ממנחת יעקב':
            post_text("Binat Adam, Shaar haKavua, Principles of Double Doubt from Minchat Yaakov", ba_text_version)
        else:
            post_text("Binat Adam, " + eng_titles_dict[unicode(shaar_title)], ba_text_version)
        
    post_link(binat_links)


# TODO: address questions:
'''
DATA:

CA:
Klalim - 64 or 138
Seifim - 57

Questions:
- where is the second half of the printed
- how are we spelling chochma

BA:
Comments - up to 62 but not only on one klal

- how do we structure it when its half comments and half explanation of concepts
- has two numbering systems @66 & @22


checked
all @22 only have a number

'''
