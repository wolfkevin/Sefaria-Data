# -*- coding: utf-8 -*-
import django
django.setup()
from sefaria.model import *
import codecs
import pickle
import re
from sefaria.system.exceptions import InputError

for idx in IndexSet():
    title_changed = False
    for title in idx.all_titles(lang='he'):
        new_title = re.sub(ur'([\u0590-\u05FF])([\u2018\u2019\u0027][\u2018\u2019\u0027]|[\"“”])([\u0590-\u05FF])', ur'\1״\3', title)
        new_title = re.sub(ur'([\u2018\u2019\u0027][\u2018\u2019\u0027]|[“”])', ur'"', new_title)
        new_title = re.sub(ur'[\u2018\u2019]', ur'׳', new_title)        
        if title != new_title:
            print(title)
            print(new_title)
            idx.nodes.add_title(new_title, 'he')
            title_changed = True
    if title_changed:
        idx.save()
