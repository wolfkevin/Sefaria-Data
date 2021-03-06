# encoding=utf-8

import os
from os.path import dirname as loc
from sources.Shulchan_Arukh.ShulchanArukh import *

root_dir = loc(loc(loc(os.path.abspath(__file__))))
xml_loc = os.path.join(root_dir, 'Yoreh_Deah.xml')

filenames = [
    u"txt_files/Yoreh_Deah/part_1/שולחן ערוך יורה דעה חלק  א פתחי תשובה.txt",
    u"txt_files/Yoreh_Deah/part_2/שולחן ערוך יורה דעה חלק ב 1 פתחי תשובה.txt",
    u"txt_files/Yoreh_Deah/part_3/פתחי תשובה שולחן ערוך יורה דעה חלק ג.txt",
    u"txt_files/Yoreh_Deah/part_4/שולחן ערוך יורה דעה חלק ד פתחי תשובה.txt"
]
filenames = dict(zip(range(1, 5), [os.path.join(root_dir, f) for f in filenames]))

root = Root(xml_loc)
commentaries = root.get_commentaries()
pithei = commentaries.get_commentary_by_title(u"Pithei Teshuva")
assert isinstance(pithei, Commentary)

for vol_num in range(1, 5):
    print 'vol {}'.format(vol_num)
    pithei.remove_volume(vol_num)
    with codecs.open(filenames[vol_num], 'r', 'utf-8') as fp:
        volume = pithei.add_volume(fp.read(), vol_num)
    assert isinstance(volume, Volume)

    volume.mark_simanim(u'@22([\u05d0-\u05ea]{1,3})')
    volume.validate_simanim(complete=False)
    print "Validating Seifim"
    errors = volume.mark_seifim(u'@11\(([\u05d0-\u05ea]{1,3})\)')
    for e in errors:
        print e
    volume.validate_seifim()
    errors = volume.format_text(u'@32', u'@33', u'dh')
    for e in errors:
        print e

    volume.set_rid_on_seifim()
    if vol_num == 2:
        volume.unlink_seifim([u'b0-c5-si110-ord{}'.format(i) for i in range(13, 18)])
    base = root.get_base_text()
    b_vol = base.get_volume(vol_num)
    assert isinstance(b_vol, Volume)
    root.populate_comment_store(verbose=True)
    errors = b_vol.validate_all_xrefs_matched(lambda x: x.name == 'xref' and re.search(u'@74', x.text) is not None)
    for e in errors:
        print e
root.export()
