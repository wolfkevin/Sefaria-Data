# -*- coding: utf8 -*-
import os, sys

import urllib2, codecs

from collections import namedtuple

from sources.local_settings import *

sys.path.insert(0, SEFARIA_PROJECT_PATH)
os.environ['DJANGO_SETTINGS_MODULE'] = "sefaria.settings"

from data_utilities.util import ja_to_xml
from sefaria.datatype import jagged_array
from sources.functions import post_text, removeExtraSpaces
from sefaria.model import *

reload(sys)
sys.setdefaultencoding("utf-8")

malbim_ja = jagged_array.JaggedArray([[]])  # JA of [Perek[Pasuk, Pasuk]]]

def SetElement(perek_l, pasuk_l, comment_num_l, comment_l):
    if comment_l != '':
        comment_l = comment_l.replace(u':', u':<br>')
        comment_l = comment_l[:-6] + comment_l[-6:].replace(u'<br>', u'')
        malbim_ja.set_element([perek_l, pasuk_l, comment_num_l], removeExtraSpaces(comment_l), "")

perek = -1
pasuk = -1
comment_num = 0
comment = ''

with codecs.open("Malbim on Esther - he - On Your Way.txt") as file_read:

    for line in file_read:

        if u'Chapter' in line:
            SetElement(perek, pasuk, comment_num, comment)
            comment = ''
            perek += 1
            pasuk = -1
            comment_num = 0
        elif u'Verse' in line:
            SetElement(perek, pasuk, comment_num, comment)
            comment = ''
            pasuk += 1
            comment_num = 0
        elif len(line) > 1:
            if u'השאלות' in line:
                SetElement(perek, pasuk, comment_num, line)
                comment = ''
                comment_num += 1
            else:
                comment += line

    malbim_ja.set_element([perek, pasuk], removeExtraSpaces(comment), "")

ja_to_xml(malbim_ja.array(), ["perek", "pasuk", "comment"], "malbim_output.xml")

malbim_text_version = {
    'versionTitle': "On Your Way 2",
    'versionSource': "http://mobile.tora.ws/",
    'language': 'he',
    'text': malbim_ja.array()
}

post_text("Malbim on Esther", malbim_text_version)
