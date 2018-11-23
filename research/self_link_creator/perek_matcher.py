# -*- coding: utf-8 -*-
from collections import namedtuple
import json
import codecs
import re
from sources.functions import post_index, post_text
from sefaria.utils.hebrew import strip_nikkud, normalize_final_letters_in_str, gematria
from data_utilities.util import numToHeb
from sefaria.datatype import jagged_array
from sefaria.model import *

self_ref_words = [u'לקמן', u'לעיל', u'להלן', u'עיין', u'ע\"ל', u"ע'", u"לק'", u'באר']
siman_words = [u"סי'", u'סימן', u'ס\"ס', u'ס"ס', u"ס''ס"]
position_words = [u'ריש', u'סוף']
seif_words = [u'סעי', u"ס'"]
daf_words = [u"ד'", u'דף']
AMUD_WORDS = [u'עמוד', u'']

SelfLink = namedtuple('SelfLink', ['insert', 'offset'])

post = True

# siman_length = []

# TODO: DEFINE THESE
SELF_REF_WORDS = self_ref_words
D1_WORDS = daf_words
D2_WORDS = None
SHORTHAND_LETTER = u'ס'

TEXT_JA = None
BASE_TEXT = None
BASE_TEXT_JA = None


def convert_index_to_daf(index):
    amud = u"b" if index % 2 else u'a'
    daf = (index/2) + 1
    return unicode(daf) + amud


def convert_daf_to_index(daf, amud):
    return (daf*2)-2 if amud == u"." else (daf*2)-1


def isGematria(txt):
    txt = normalize_final_letters_in_str(txt)
    txt = re.sub('[\', ":.\n)]', u'', txt)
    if txt.find(u"טו") >= 0:
        txt = txt.replace(u"טו", u"יה")
    elif txt.find(u"טז") >= 0:
        txt = txt.replace(u"טז", u"יו")

    if len(txt) == 0:
        print "not gematria " + txt
        return False
    try:
        while txt[0] == u'ת':
            txt = txt[1:]
    except:
        return False

    if len(txt) == 1:
        if txt[0] < u'א' or txt[0] > u'ת':
            print "not gematria " + txt
            return False
    elif len(txt) == 2:
        if txt[0] < u'י' or (txt[0] < u'ק' and txt[1] > u'ט'):
            print "not gematria " + txt
            return False
    elif len(txt) == 3:
        if txt[0] < u'ק' or txt[1] < u'י' or txt[2] > u'ט':
            print "not gematria " + txt
            return False
    else:
        return False
    return True
#skip (להלן|לעיל|לקמן) ((ילפ|ב|פ(\'|\")).{0,30}) (\(|\[)?((דף|ד\')(\.)? )?[א-ת]*
self_ref_words = u'(להלן|לעיל|לקמן)'
# filler_words = u"(ילפ|ב|פ(\'|\"))"
daf_words = ur"(?P<daf_prepend>(ב?ד[פף]?\'?)\.? )?"
daf_number = ur'(?P<daf_number>[\'\"א-ת]+)'
parentheses = ur'(?P<parentheses>[\(\[{])'
amud_words = ur'(?P<amud>:|\.|((ע\"|עמוד )[אב]))?'
perek_prepend = ur"(פ'|פרק|[רס]\"פ) "

files_dict = {}
perakim_names = ur'(?P<perek_name>'

perek_to_mesechet_dict = {}
mesechet_to_alt_titles = {}
with codecs.open('perakim.txt', 'r', encoding='utf-8') as fr:
    for line in fr:
        values = line.split(u',')
        ref = Ref(values[0].strip())
        perek_to_mesechet_dict[values[2].strip()] = ref.he_book()
        mesechet_to_alt_titles[ref.he_book()] = ref.index.all_titles('he')
        perakim_names += values[2].strip() + ur'|'
    perakim_names = perakim_names[:-1] + ur').?.?'
    print(perakim_names)

filler_outside_words = ur'((ו?ב?(סוף|ריש)( הפרק)?|ופ"ק דבתרא|בברייתא|תנן) )?'
filler_inside_words = ur'(?P<filler_inside>ו?ב?(סוף|ריש) )?'

perek_str = perek_prepend + perakim_names + filler_outside_words + parentheses + filler_inside_words + daf_words + daf_number + amud_words
depth = 3
with codecs.open('perek_summary1' + '.tsv', 'wb+', 'utf-8') as csvfile:
    csvfile.write(u'Text\t# of Links Added\tVersion\n')
    # for depth in range(1, 4):
    # or title in IndexSet({"$and": [{"categories": "Halakha"}, {"schema.depth": depth}, {"title": "Beit Yosef"}]}):
    for title in IndexSet({"$and": [{"categories": "Tur and Commentaries"}]}):
        for section in title.schema['nodes']:
            text_changed = False
            links_added = 0
            ref = Ref(title.title+u', '+section['titles'][0]['text'])
            text_chunk = TextChunk(ref, 'he')
            # BASE_TEXT = Ref(ref.index.base_text_titles[0])
            BASE_TEXT_JA = TextChunk(ref, 'he').text
            text_len = len(BASE_TEXT_JA)
            if section['depth'] == 3:
                new_text_ja = jagged_array.JaggedArray([])
                for d1_idx, d1 in enumerate(text_chunk.text):   
                    for d2_idx, d2 in enumerate(d1):
                        for d3_idx, og_text in enumerate(d2):
                            seg_text = u''
                            pre_idx = 0
                            offset = 0
                            for match in re.finditer(perek_str, og_text):
                                daf = match.group('daf_number')
                                talmud_title = perek_to_mesechet_dict[match.group('perek_name')]
                                # alt_titles = mesechet_to_alt_titles[talmud_title]
                                if (isGematria(daf) and Ref().is_ref(talmud_title + u' ' + daf)) or daf == u'שם':
                                    text_changed = True
                                    links_added += 1
                                    indx = match.end('parentheses')
                                    if og_text[match.end()] == u')' or og_text[match.end()] == u']':
                                        seg_text += og_text[pre_idx:match.start('parentheses')] + u'(' + talmud_title + u' ' + og_text[indx:match.end()] + u')'
                                        pre_idx = match.end() + 1
                                    else:
                                        seg_text += og_text[pre_idx:indx] + talmud_title + u' ' + og_text[indx:match.end()]  
                                        pre_idx = match.end()
                                    csvfile.write(u'{}\t{}\t{}\n'.format(
                                        (ref.normal() + u' ' + unicode(d1_idx+1)+u'.'+unicode(d2_idx+1)),
                                        og_text[match.start():match.end()+1].strip(),
                                        seg_text[match.start()+offset:].strip()))
                                    offset += len(talmud_title)+1
                                else:
                                    print ref.normal() + u' ' + unicode(d1_idx+1)+u'.'+unicode(d2_idx+1)
                            seg_text += og_text[pre_idx:]
                            new_text_ja.set_element([d1_idx, d2_idx, d3_idx], seg_text, u'')
            # elif depth == 2:
            #     new_text_ja = jagged_array.JaggedArray([])
            #     for d1_idx, d1 in enumerate(text_chunk.text):   
            #         for d2_idx, seg_text in enumerate(d1):
            #             og_text = seg_text
            #             offset = 0
            #             for match in re.finditer(perek_str, seg_text):
            #                 try:
            #                     indx = match.group('filler inside')
            #                 except:
            #                     indx = match.group('parentheses')
            #                 
            #                 if (match.group(2) or match.group(17)) and isGematria(match.group(16)) and (text_len >= gematria(match.group(16))*2-1) and (gematria(match.group(16)) > 1):
            #                     insert = u'{} '.format(ref.he_normal()) 
            #                     if u'"' in match.group(16):
            #                         if not match.group(17) and not match.group(9) and not match.group(14):
            #                             if re.search(ur'ע"[אב]', match.group(16)):
            #                                 insert += u'{} '.format(numToHeb(convert_index_to_daf(d1_idx)[:-1]))
            #                             else:
            #                                 continue
            #                     text_changed = True
            #                     links_added += 1
            #                     for group_num in [9, 14, 16]:
            #                         # group 9 or 14 and if neither then before group 16
            #                         if match.start(group_num) > 0:
            #                             start = match.start(group_num) + offset
            #                             break
            #                     # if match.group(7) or match.group(12):
            #                     assert start
            #                     if match.group(7) or match.group(11) or match.group(12) or (seg_text[match.start()+offset-1] == u'(') or (u')' in re.sub(ur'(.*?)[\s$].*', ur'\1', seg_text[match.end()+offset:])):
            #                         # check for before and after for parentheses
            #                         seg_text = seg_text[:start] + insert + seg_text[start:]
            #                     else:
            #                         seg_text = seg_text[:start] + u'(' + insert + seg_text[start:match.end()+offset] + u')' + seg_text[match.end()+offset:]
            #                         offset += 2
            #                     
            #                     # csvfile.write(u'{}\t{}\t{}\n'.format(
            #                     #     (ref.normal() + u' ' + convert_index_to_daf(d1_idx)+u'.'+unicode(d1_idx)),
            #                     #     og_text[match.start()-20:match.end()+len(insert)+1].strip(),
            #                     #     seg_text[match.start()-1+offset:match.end()+offset+len(insert)+1].strip()))
            #                     offset += len(insert)
            #             new_text_ja.set_element([d1_idx, d2_idx], seg_text, u'')
            # elif depth == 1:
            #     new_text_ja = jagged_array.JaggedArray([])
            #     for d1_idx, seg_text in enumerate(text_chunk.text):   
            #         og_text = seg_text
            #         offset = 0
            #         for match in re.finditer(perek_str, seg_text):
            #             if (match.group(2) or match.group(17)) and isGematria(match.group(16)) and (text_len >= gematria(match.group(16))*2-1) and (gematria(match.group(16)) > 1):
            #                 insert = u'{} '.format(ref.he_normal()) 
            #                 if u'"' in match.group(16):
            #                     if not match.group(17) and not match.group(9) and not match.group(14):
            #                         if re.search(ur'ע"[אב]', match.group(16)):
            #                             insert += u'{} '.format(numToHeb(convert_index_to_daf(d1_idx)[:-1]))
            #                         else:
            #                             continue
            #                 text_changed = True
            #                 links_added += 1
            #                 for group_num in [9, 14, 16]:
            #                     # group 9 or 14 and if neither then before group 16
            #                     if match.start(group_num) > 0:
            #                         start = match.start(group_num) + offset
            #                         break
            #                 # if match.group(7) or match.group(12):
            #                 assert start
            #                 if match.group(7) or match.group(11) or match.group(12) or (seg_text[match.start()+offset-1] == u'(') or (u')' in re.sub(ur'(.*?)[\s$].*', ur'\1', seg_text[match.end()+offset:])):
            #                     # check for before and after for parentheses
            #                     seg_text = seg_text[:start] + insert + seg_text[start:]
            #                 else:
            #                     seg_text = seg_text[:start] + u'(' + insert + seg_text[start:match.end()+offset] + u')' + seg_text[match.end()+offset:]
            #                     offset += 2
            #                 
            #                 # csvfile.write(u'{}\t{}\t{}\n'.format(
            #                 #     (ref.normal() + u' ' + convert_index_to_daf(d1_idx)+u'.'+unicode(d1_idx)),
            #                 #     og_text[match.start()-20:match.end()+len(insert)+1].strip(),
            #                 #     seg_text[match.start()-1+offset:match.end()+offset+len(insert)+1].strip()))
            #                 offset += len(insert)
            #         new_text_ja.set_element([d1_idx], seg_text, u'')
            # if title.title == 'Steinsaltz on Sanhedrin':
            if text_changed and post:
                try:
                    text_version = {
                        'versionTitle': text_chunk._versions[0].versionTitle,
                        'versionSource': text_chunk._versions[0].versionSource,
                        'language': 'he',
                        'text': new_text_ja.array(),
                    }
                    print post_text(ref.normal(), text_version)
                    # csvfile.write(u'{}\t{}\t{}\n'.format(title.title, links_added, text_chunk._versions[0].versionTitle))
                    print "Changed: " + title.title + ' ' + text_chunk._versions[0].versionTitle + " Version: " + text_chunk._versions[0].versionSource
                except Exception as e:
                    print(e)
                    print title.title + " is a merged text"
                    # csvfile.write(u'{}\t{}\t{}\n'.format(title.title, links_added, 'MERGED TEXT'))
            
    # ''' 
    # Test Suite
    # בפרק הרואה כתם ובסוף הפרק (דף נח:)
    # בפ"ק דנדה
    # בפרק האשה שהיא עושה צרכיה (נט:) תנן 
    # משנה פרק הרואה (נז:) כתם על
    #  בגיטין בסוף השולח (דף מז.) למאן
    # ם בפ' כיצד צולין (פג:) ובתר הכי (צג:)
    #  בענין חזקה בכתובות פ"ק (יב:)
    # תענית (פ"ב דף טז: ולקמן דף סג.) אשאש
    # (לקמן דף מט:) אשאש
    # (לקמן כו.) אשאש
    # (לקמן ד' כט.) אשאש
    # לעיל בפירקין (דף נב.) אשאש
    # לקמן בפרק בית שמאי (דף מג.) אשאש
    # לקמן באיזהו מקומן (דף מח.) אשאש
    # לקמן בכל הזבחים שנתערבו (דף פב.) אשאש
    # לקמן ילפינן לה בפירקין (כג:) אשאש
    # תרי גווני הצעות יש דלקמן פ' אע"פ (דף נב.) אשאש
    #  אשאשואמרינן לקמן (דף ה') אבל
    # קורין בט"ו ועד כמה (לעיל דף ב ע"ב) א"ר
    # והיינו כברייתא דלקמן צ"ה
    # דפרישית בריש המניח (לעיל דף כ': ושם.):
    # אינו רוצה כדפרישית לעיל (י"ח. ד"ה הא):
    # מש בה, וכאותה שאמרו לקמן (מא, ב) שלשה
    # ותלמידיו דלעיל פ"ו דף לט
    
    
    # (פ'|פרק|[רס]\"פ) (הורו בית דין|הורה כהן משיח|כהן משיח|לפני אידיהן|אין מעמידין|כל הצלמים|רבי ישמעאל|השוכר את הפועל|מגילה נקראת|הקורא למפרע|הקורא עומד|בני העיר|שבועות שתים קמא|ידיעות הטומאה|שבועות שתים בתרא|שבועת העדות|שבועת הפקדון|שבועת הדיינין|כל הנשבעין|ארבעה שומרין|מאימתי|היה קורא|מי שמתו|תפלת השחר|אין עומדין|כיצד מברכין|שלשה שאכלו|אלו דברים|הרואה|הלוקח עובר חמורו|הלוקח עובר פרתו|הלוקח בהמה|עד כמה|כל פסולי המוקדשין|על אלו מומין|מומין אלו|יש בכור|מעשר בהמה|דיני ממונות|כהן גדול|זה בורר|אחד דיני ממונות|היו בודקין|נגמר הדין|ארבע מיתות|בן סורר ומורה|הנשרפין|אלו הן הנחנקין|חלק|כל כנויי נזירות|הריני נזיר|מי שאמר קמא|מי שאמר בתרא|בית שמאי|שלשה מינין|כהן גדול|שני נזירים|הכותים אין להם נזירות|ארבעה אבות|כיצד רגל|המניח|שור שנגח ד' וה'|שור שנגח את הפרה|הכונס|מרובה|החובל|הגוזל עצים|הגוזל בתרא|המקנא|היה מביא|היה נוטל|ארוסה|כשם שהמים|מי שקינא|אלו נאמרין|משוח מלחמה|עגלה ערופה|השותפין|לא יחפור|חזקת הבתים|המוכר את הבית|המוכר את הספינה|המוכר פירות|בית כור|יש נוחלין|מי שמת|גט פשוט|שבעת ימים|בראשונה|אמר להם הממונה|טרף בקלפי|הוציאו לו( את הכף)?|שני שעירי|בא לו|יום הכפורים|קדשי קדשים|חטאת העוף|ולד חטאת|קדשי מזבח|הנהנה מן ההקדש|השליח שעשה שליחותו|שלשים ושש|ארבעה מחוסרי כפרה|אמרו לו|ספק אכל חלב|דם שחיטה|המביא אשם|בשלשה מקומות|ראוהו אחיו|אמר להם הממונה בואו|לא היו כופתין|אמר להם הממונה ברכו|החלו עולים|בזמן שכהן גדול|הכל מעריכין|אין נערכין|יש בערכין|השג יד|האומר משקלי עלי|שום היתומים|אין מקדישין|המקדיש שדהו|המוכר שדהו|שמאי אומר|כל היד|המפלת חתיכה|בנות כותים|יוצא דופן|בא סימן|דם הנדה|הרואה כתם|האשה שהיא עושה( צרכיה)?|תינוקת|המביא קמא|המביא בתרא|כל הגט|השולח|הניזקין|האומר התקבל|מי שאחזו|הזורק גט|המגרש|חמש עשרה נשים|כיצד אשת אחיו|ארבעה אחין|החולץ|רבן גמליאל|הבא על יבמתו|אלמנה לכהן גדול|הערל|יש מותרות|האישה רבה|נושאין על האנוסה|מצות חליצה|בית שמאי|חרש שנשא|האשה שלום|האשה בתרא|משקין בית השלחין|מי שהפך|ואלו מגלחין|הכל חייבין|אין דורשין|חומר בקודש|יציאות השבת|במה מדליקין|כירה|במה טומנין|במה בהמה|במה אשה|כלל גדול|המוציא יין|אמר רבי עקיבא|המצניע|הזורק|הבונה|האורג|שמנה שרצים|ואלו קשרים|כל כתבי|כל הכלים|מפנין|רבי אליעזר דמילה|תולין|נוטל אדם את בנו|חבית|שואל( אדם)?|מי שהחשיך|מבוי|עושין פסין|בכל מערבין|מי שהוציאוהו|כיצד מעברין|הדר|חלון|כיצד משתתפין|כל גגות|המוצא תפילין|שנים אוחזין|אלו מציאות|המפקיד|הזהב|איזהו נשך|השוכר את האומנין|השוכר את הפועלים|השואל את הפרה|המקבל שדה מחבירו|הבית והעלייה|כל הזבחים|כל הזבחים שקבלו דמן|כל הפסולין|בית שמאי|איזהו מקומן|קדשי קדשים|חטאת העוף|כל הזבחים שנתערבו|המזבח מקדש|כל התדיר|דם חטאת|טבול יום|השוחט והמעלה|פרת חטאת|האשה נקנית|האיש מקדש|האומר לחברו|עשרה יוחסין|הכל שוחטין|השוחט|אלו טרפות|בהמה המקשה|אותו ואת בנו|כסוי הדם|גיד הנשה|כל הבשר|העור והרוטב|הזרוע והלחיים|ראשית הגז|שילוח הקן|הכל ממירין|יש בקרבנות|אלו קדשים|ולד חטאת|כיצד מערימין|כל האסורין|יש בקדשי מזבח|מאימתי מזכירין|סדר תעניות כיצד|סדר תעניות אלו|בשלשה פרקים|יום טוב|אין צדין|המביא כדי יין|משילין|ארבעה ראשי שנים|אם אינן מכירין|ראוהו בית דין|יום טוב|כל כנויי|ואלו מותרין|ארבעה נדרים|אין בין המודר|השותפין שנדרו|הנודר מן המבושל|הנודר מן הירק|קונם יין|רבי אליעזר|נערה המאורסה|ואלו נדרים|כל המנחות|הקומץ את המנחה|הקומץ רבה|התכלת|כל המנחות באות מצה|רבי ישמעאל|אלו מנחות נקמצות|התודה היתה באה|כל קרבנות ציבור|שתי מדות|שתי הלחם|המנחות והנסכים|הרי עלי עשרון|אור לארבעה עשר|כל שעה|אלו עוברין|מקום שנהגו|תמיד נשחט|אלו דברים|כיצד צולין|האשה|מי שהיה טמא|ערבי פסחים|בתולה נשאת|האשה שנתארמלה|אלו נערות|נערה שנתפתתה|אף על פי|מציאת האשה|המדיר|האשה שנפלו|הכותב לאשתו|מי שהיה נשוי|אלמנה ניזונת|הנושא את האשה|שני דייני גזירות|הישן|לולב הגזול|לולב וערבה|החליל|כיצד העדים|אלו הן הגולין|אלו הן הלוקין) [^ֿֿ\[(].{0,30}[(\[]

    # '''
    
