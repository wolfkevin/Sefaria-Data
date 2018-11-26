# -*- coding: utf-8 -*-
from collections import namedtuple
import json
import codecs
import re
from sources.functions import post_index, post_text
from sefaria.utils.hebrew import strip_nikkud, normalize_final_letters_in_str, gematria, has_cantillation
from data_utilities.util import numToHeb
from sefaria.datatype import jagged_array
from sefaria.model import *
from sefaria.system.exceptions import BookNameError

post = True

def isGematria(txt):
    txt = normalize_final_letters_in_str(txt)
    txt = re.sub(ur'[\', ׳”״”":.\r\n)]', u'', txt)
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

daf_words = ur"(?P<daf_prepend>ב?\u05d3[\u05e3\u05e4\u05f3']\s+)?"
daf_number = ur'(?P<daf_number>[״”״\'ֿ׳\"א-ת]+)'
parentheses = ur'(?P<parentheses>[\(\[{])'
amud_words = ur'(?P<amud>[:.]|(ע(מוד |[”״”"\'ֿ׳]+)|,? )[אב])?'
perek_prepend = ur"(פ['׳]|פרק|[רס][\"”“״׳\']+פ)\s+"
not_siman_words = ur'''(?!\s*ס(י?[\'ֿ׳]|ימן|[”״”"\'ֿ׳]+ס))'''


files_dict = {}
perakim_names = ur'(?P<perek_name>'

perek_to_mesechet_dict = {}
mesechet_to_alt_titles = {}
with codecs.open('perakim.txt', 'r', encoding='utf-8') as fr:
    for line in fr:
        values = line.split(u',')
        ref = Ref(values[0].strip())
        perek_title = values[2].strip()
        if u'?' in perek_title:
            idx = perek_title.index(u'?')
            perek_to_mesechet_dict[perek_title[:idx]+perek_title[idx+1:]] = ref.he_book()
            perek_to_mesechet_dict[perek_title[:idx-1]+perek_title[idx+1:]] = ref.he_book()
        else:
            perek_to_mesechet_dict[perek_title] = ref.he_book()
        mesechet_to_alt_titles[ref.he_book()] = ref.index.all_titles('he')
        perakim_names += values[2].strip() + ur'|'
    perakim_names = perakim_names[:-1] + ur').?.?'
    print(perakim_names)

filler_outside_words = ur'((ו?ב?(סוף|ריש)(\s+הפרק)?|ופ[\u059E\u201C"””״׳\']+ק דבתרא|בברייתא|תנן)\s+)?'
filler_inside_words = ur'(?P<filler_inside>ו?ב?(סוף|ריש)\s+)?'

perek_str = perek_prepend + perakim_names + filler_outside_words + parentheses + filler_inside_words + daf_words + daf_number + amud_words + not_siman_words
# print perek_str
# ur"(פ['']|פרק|[רס][\"””״]פ) (?P<perek_name>הורו בית דין|הורה כהן משיח|כהן משיח|לפני אי?די?הן|אין מעמי?דין|כל הצלמים|רבי ישמעאל|ה?שוכר את הפועל|מגילה נקראת|ה?קו?רא למפרע|ה?קו?רא עו?מד|בני ה?עיר|שבועות שתים( קמא)?|ידי?עו?ת ה?טו?מאה|שבו?עו?ת שתים בתרא|שבועת( העדות)?|שבועת הפקדון|שבועת הדייני?ן|כל הנשבעי?ן|ארבעה שו?מרי?ן|מאימתי|היה קורא|מי שמתו|תפלת השחר|אין עו?מדי?ן|כיצד מברכי?ן|שלשה שאכלו|אלו דברים|ה?רואה|הלוקח( עובר חמורו)?|הלוקח עובר פרתו|הלו?קח בהמה|עד כמה|כל פסולי המו?קדשי?ן|על אלו מו?מי?ן|מו?מי?ן אלו|יש בכור|מעשר בהמה|דיני ממונות|כהן גדול|זה בורר|אחד דיני ממונות|היו בודקין|נגמר הדין|ארבע מיתות|בן סורר ומורה|הנשרפין|אלו הן הנחנקין|ה?חלק|כל כנויי נזירות|הריני נזיר|מי שאמר( קמא)?|מי שאמר בתרא|בית שמאי|שלשה מינין|כהן גדול|שני נזירים|הכותים אין להם נזירות|ארבעה אבות|כיצד רגל|המניח|שור שנגח( ד' וה')?|שור שנגח את הפרה|הכונס|מרובה|החובל|הגוזל עצים|הגוזל בתרא|המקנא|היה מביא|היה נוטל|ארוסה|כשם שהמים|מי שקינא|אלו נאמרין|משוח מלחמה|עגלה ערופה|השותפין|לא יחפור|חזקת הבתים|המוכר את הבית|המוכר את הספינה|המוכר פירות|בית כור|יש נוחלין|מי שמת|גט פשוט|שבעת ימים|בראשונה|אמר להם הממונה|טרף בקלפי|הוציאו לו|שני שעירי|בא לו|יום ה?כפורים|קדשי קדשים|חטאת העוף|ולד חטאת|קדשי מזבח|הנהנה מן ההקדש|השליח שעשה שליחותו|שלשים ושש|ארבעה מחוסרי כפרה|אמרו לו|ספק אכל חלב|דם שחיטה|המביא אשם|בשלשה מקומות|ראוהו אחיו|אמר להם הממונה בואו|לא היו כופתין|אמר להם הממונה ברכו|החלו עולים|בזמן שכהן גדול|ה?כל מעריכין|אין נערכין|יש בערכין|השג יד|ה?אומר משקלי עלי|שום היתו?מים|אין מקדי?שין|ה?מקדיש שדהו|ה?מוכר שדהו|שמאי אומר|כל היד|ה?מפלת חתיכה|בנות כותים|יוצא דופן|בא סימן|דם ה?נדה|ה?רואה כתם|ה?אשה שהיא עושה|תינוקת|ה?מביא קמא|ה?מביא בתרא|כל הגט|ה?שולח|הניזקין|ה?אומר התקבל|מי שאחזו|הזורק גט|המגרש|חמש עשרה נשים|כיצד אשת אחיו|ארבעה אחין|החולץ|רבן גמליאל|הבא על יבמתו|אלמנה לכהן גדול|הערל|יש מותרות|האישה רבה|נושאין על האנוסה|מצות חליצה|בית שמאי|חרש שנשא|האשה שלום|האשה בתרא|משקין בית השלחין|מי שהפך|ואלו מגלחין|הכל חייבין|אין דורשין|חומר בקודש|יציאות השבת|במה מדליקין|כירה|במה טומנין|במה בהמה|במה אשה|כלל גדול|המוציא יין|אמר רבי עקיבא|המצניע|הזורק|הבונה|האורג|שמנה שרצים|ואלו קשרים|כל כתבי|כל הכלים|מפנין|רבי אליעזר דמילה|תולין|נוטל אדם את בנו|חבית|שואל|מי שהחשיך|מבוי|עו?שין פסין|ב?כל מערבין|מי שהוציאוהו|כיצד מעברין|הדר|חלון|כיצד משתתפין|כל גגות|ה?מוצא תפילין|שנים אוחזין|אלו מציאות|המפקיד|הזהב|איזהו נשך|ה?שוכר את האומנין|ה?שוכר את הפועלים|השואל את הפרה|ה?מקבל שדה מחבירו|ה?בית והעלייה|כל הזבחים|כל הזבחים שקבלו דמן|כל הפסולין|בית שמאי|איזהו מקומן|קדשי קדשים|חטאת העוף|כל הזבחים שנתערבו|המזבח מקדש|כל התדיר|דם חטאת|טבול יום|ה?שוחט והמעלה|פרת חטאת|ה?אשה נקנית|ה?איש מקדש|ה?אומר לחברו|עשרה יוחסין|ה?כל שוחטין|ה?שוחט|אלו טרי?פות|בהמה המקשה|או?תו ואת בנו|כסוי הדם|גיד הנשה|כל הבשר|ה?עור והרוטב|ה?זרוע והלחיים|ראשית הגז|שילוח הקן|הכל ממי?רין|יש בקרבנות|אלו קדשים|ולד חטאת|כיצד מערי?מין|כל האסו?רין|יש בקדשי מזבח|מאימתי מזכירין|סדר תעניות כיצד|סדר תעניות( אלו)?|ב?שלשה פרקים|יום טוב|אין צדין|המביא כדי יין|משילין|ארבעה ראשי שנים|אם אינן מכירין|ראוהו בית דין|יום טוב|כל כנויי|ו?אלו מו?תרין|ארבעה נדרים|אין בין המודר|השו?תפין שנדרו|ה?נודר( מן המבושל)?|ה?נודר מן הירק|קונם יין|רבי אליעזר|נערה המאורסה|ו?אלו נדרים|כל המנחות|ה?קומץ את ה?מנחה|ה?קומץ רבה|ה?תכלת|כל ה?מנחות באות מצה|רבי ישמעאל|אלו מנחות נקמצות|התודה היתה באה|כל קרבנות ציבור|שתי מדות|שתי הלחם|המנחות והנסכים|הרי עלי עשרון|אור לארבעה עשר|כל שעה|אלו עוברין|מקום שנהגו|תמיד נשחט|אלו דברים|כיצד צולין|האשה|מי שהיה טמא|ערבי פסחים|בתולה נשאת|ה?אשה שנתארמלה|אלו נערות|נערה שנתפתתה|אף על פי|מציאת האשה|ה?מדיר|ה?אשה שנפלו|ה?כותב לאשתו|מי שהיה נשוי|אלמנה ניזונת|ה?נושא את ה?אשה|שני דייני גזירות|הישן|לולב ה?גזול|לולב וערבה|ה?חליל|כיצד העדים|אלו הן הגולין|אלו הן הלוקין).?.?.{4, 15}((ו?ב?(סוף|ריש)( הפרק)?|ופ[\"””״]ק דבתרא|בברייתא|תנן) )?(?P<parentheses>[\(\[{])(?P<filler_inside>ו?ב?(סוף|ריש) )?(?P<daf_prepend>(ב?ד[פף]?\'?)\.? )?(?P<daf_number>[״”״\'\"א-ת]+)(?P<amud>[:.]|(ע(מוד |[”״”\"\']+)|,? )[אב])?"
links_added = 0
base_text = None

def walk_thru_action(s, tref, heTref, version):
    global base_text
    global links_added
    global csvfile
    seg_text = u''
    pre_idx = 0
    offset = 0
    if re.search(ur'[א-ת](\'\'|[\"“”])[א-ת]', s):
        re.sub(ur'[א-ת](\'\'|[\"“”])[א-ת]', ur'״', s)
        text_changed = True
    text_changed = False
    if has_cantillation(s, detect_vowels=True):
        s = strip_nikkud(s)
        for match in re.finditer(perek_str, s):  
            daf = match.group('daf_number')
            talmud_title = perek_to_mesechet_dict[match.group('perek_name')]
            # alt_titles = mesechet_to_alt_titles[talmud_title]
            if (isGematria(daf) and Ref().is_ref(talmud_title + u' ' + daf)) or daf == u'שם':
                text_changed = True
                links_added += 1
                indx = match.end('parentheses')
                if s[match.end()] == u')' or s[match.end()] == u']':
                    seg_text += s[pre_idx:match.start('parentheses')] + u'(' + talmud_title + u' ' + s[indx:match.end()] + u')'
                    pre_idx = match.end() + 1
                else:
                    seg_text += s[pre_idx:indx] + talmud_title + u' ' + s[indx:match.end()]  
                    pre_idx = match.end()
                csvfile.write(u'{}\t{}\t{}\n'.format(
                    tref, s[match.start():match.end()+1].strip(),
                    seg_text[match.start()+offset:].strip()))
                offset += len(talmud_title)+1
            else:
                pass
                # print tref
    seg_text += s[pre_idx:]
    if re.search(ur'ֿֿ[\(\[](ריש|סוף)', seg_text):
        print u"SEG TEXT: {}".format(seg_text) 
    if text_changed and post:
        try:
            text_version = {
                'versionTitle': version.versionTitle,
                'versionSource': version.versionSource,
                'language': 'he',
                'text': seg_text,
            }
            print post_text(tref, text_version)
        except:
            print u"Issue posting: {}".format(tref)
    return 


with codecs.open('newest12' + '.tsv', 'wb+', 'utf-8') as csvfile:
        # s is the segment string
        # tref is the segment's english ref
        # heTref is the hebrew ref
        # version is the segment's version object. use it to get the version title and language```
    
    # vs = VersionSet({"title": "Responsa Rav Pealim"})
    # vs = VersionSet({"title": "Nachal Eitan on Mishneh Torah, Divorce"})
    vs = VersionSet({"language": "he"})
    for v in vs:
        if v.title != u'Shulchan Arukh, Choshen Mishpat':
            try:
                i = v.get_index()
                # if i.is_dependant_text():
                #     base_text = i.base_text_titles[0]
                #     if len(i.base_text_titles) > 1:
                #         print i.title + u' has multiple base texts'
                v.walk_thru_contents(walk_thru_action, heTref=i.get_title('he'), schema=i.schema)
            except BookNameError:
                print u"Skipping {}, {}".format(v.title, v.versionTitle)
                continue
            except Exception as e:
                print e, v.title, v.versionTitle
                continue
    print u"Links Added: {}".format(links_added)
    
