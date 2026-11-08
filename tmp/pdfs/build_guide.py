"""Build an illustrated Hebrew learning guide from the repository's real code."""
from pathlib import Path
import io
import math

from bidi.algorithm import get_display
from PIL import Image, ImageDraw, ImageFont
from pygments import lex
from pygments.lexers import PythonLexer, JsonLexer, BashLexer
from pygments.token import Token
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor, Color
from reportlab.lib.utils import ImageReader
import fitz

ROOT = Path(__file__).resolve().parents[2]
SERVICE = ROOT / 'services/registry-service'
OUT = ROOT / 'output/pdf'
TMP = ROOT / 'tmp/pdfs'
OUT.mkdir(parents=True, exist_ok=True)
FONT = '/System/Library/Fonts/Supplemental/Arial.ttf'
BOLD = '/System/Library/Fonts/Supplemental/Arial Bold.ttf'
MONO = '/System/Library/Fonts/Menlo.ttc'
pdfmetrics.registerFont(TTFont('Hebrew', FONT))
pdfmetrics.registerFont(TTFont('HebrewBold', BOLD))
W, H = 595.28, 841.89
INK = '#17352F'
GREEN = '#167D67'
MUTED = '#566B65'
PAPER = '#F7FAF7'
GOLD = '#E6B74C'
PDF = OUT / 'argopilot-explained-hebrew.pdf'
c = canvas.Canvas(str(PDF), pagesize=(W,H))
c.setTitle('ArgoPilot - מדריך חזותי ופשוט לקוד שבנינו')
c.setAuthor('ArgoPilot learning guide')
page = 0
y = 0
bottoms = []

def rtl(text):
    return get_display(text)

def text_right(text, x, yy, size=12.5, bold=False, color=INK):
    c.setFillColor(HexColor(color))
    c.setFont('HebrewBold' if bold else 'Hebrew', size)
    c.drawRightString(x, yy, rtl(text))

def english(text, x, yy, size=11, color=INK):
    c.setFillColor(HexColor(color))
    c.setFont('Helvetica', size)
    c.drawString(x, yy, text)

def wrap(text, width, size=12.5, bold=False):
    font = 'HebrewBold' if bold else 'Hebrew'
    lines, line = [], ''
    for word in text.split():
        candidate = (line+' '+word).strip()
        if pdfmetrics.stringWidth(rtl(candidate), font, size) > width and line:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    return lines

def para(text, size=12.5, bold=False, color=INK, gap=8, width=W-96):
    global y
    for line in wrap(text, width, size, bold):
        text_right(line, W-48, y, size, bold, color)
        y -= size*1.56
    y -= gap

def sub(text):
    global y
    y -= 3
    para(text, size=15, bold=True, color=GREEN, gap=5)

def box(title, body, fill='#E8F2EC'):
    global y
    lines = wrap(body, W-132, 12)
    height = 48+len(lines)*18
    c.setFillColor(HexColor(fill))
    c.roundRect(42, y-height+14, W-84, height, 12, fill=1, stroke=0)
    text_right(title, W-60, y-8, 13, True, GREEN)
    yy = y-32
    for line in lines:
        text_right(line, W-60, yy, 12)
        yy -= 18
    y -= height+7

def begin(kicker, title, subtitle=None):
    global page, y
    if page:
        end()
    page += 1
    c.setFillColor(HexColor(PAPER))
    c.rect(0,0,W,H,fill=1,stroke=0)
    c.setFillColor(HexColor(GREEN))
    c.rect(W-18,0,18,H,fill=1,stroke=0)
    english('ARGO / PILOT', 44, H-39, 10, GREEN)
    text_right(kicker, W-48, H-39, 10, color=MUTED)
    text_right(title, W-48, H-94, 25, True)
    y = H-128
    if subtitle:
        para(subtitle, size=12, color=MUTED, gap=15)

def end():
    bottoms.append((page,y))
    if y < 63:
        raise RuntimeError(f'Page {page} overflows at {y}')
    c.setStrokeColor(HexColor('#D7E3DB'))
    c.line(44,48,W-44,48)
    english('ArgoPilot | Learning by seeing',44,31,8,MUTED)
    text_right(f'עמוד {page}',W-45,31,9,color=MUTED)
    c.showPage()

def actual(file, start, finish=None):
    lines=(SERVICE/file).read_text().splitlines()
    index=next(i for i,line in enumerate(lines) if line.startswith(start))
    stop=index+1
    if finish:
        stop=next(i for i in range(index+1,len(lines)) if lines[i].startswith(finish))
    else:
        if lines[index].startswith('@'):
            stop+=1
        while stop<len(lines) and (lines[stop].startswith((' ', '\t')) or not lines[stop].strip()):
            stop+=1
    return '\n'.join(lines[index:stop]).rstrip(), index+1

def code(code_text, label, lexer='python', first=1):
    global y
    # Render actual code as a sharp, syntax-colored image, embedded in the PDF.
    lines=code_text.expandtabs(4).splitlines()
    size=25
    f=ImageFont.truetype(MONO,size)
    small=ImageFont.truetype(MONO,18)
    cw=f.getlength('M')
    iw=int(max(950,max(len(line) for line in lines)*cw+115))
    ih=80+len(lines)*38+20
    im=Image.new('RGB',(iw,ih),'#112B26')
    draw=ImageDraw.Draw(im)
    for i,col in enumerate(('#F08275','#E8BA58','#6BC6A5')):
        draw.ellipse((24+i*23,22,37+i*23,35),fill=col)
    draw.text((105,16),label,font=small,fill='#C1D3CD')
    lexer_obj={'python':PythonLexer(),'json':JsonLexer(),'bash':BashLexer()}[lexer]
    for j,line in enumerate(lines):
        yy=65+j*38
        draw.text((18,yy+4),str(first+j),font=small,fill='#789C8F')
        x=82
        for token,value in lex(line,lexer_obj):
            value=value.rstrip('\n')
            col='#E5F0EA'
            if token in Token.Keyword: col='#D1AFF5'
            elif token in Token.Literal.String: col='#B9DB88'
            elif token in Token.Literal.Number: col='#F1C979'
            elif token in Token.Name.Function: col='#79D9CF'
            elif token in Token.Comment: col='#87A899'
            draw.text((x,yy),value,font=f,fill=col)
            x+=f.getlength(value)
    filename=TMP/f'code-{page}-{int(y)}.png'
    im.save(filename)
    height=(W-88)*ih/iw
    c.drawImage(ImageReader(im),44,y-height+8,width=W-88,height=height)
    y-=height+15

def source(file,start,finish=None):
    snippet,line=actual(file,start,finish)
    code(snippet,file,first=line)

def terms(items):
    for name,meaning in items:
        para(f'{name} - {meaning}',size=12,gap=4)

def path_row(labels):
    global y
    width=(W-100)/len(labels)
    for i,label in enumerate(labels):
        x=W-48-(i+1)*width
        c.setFillColor(HexColor('#E6EFE7' if i%2==0 else '#F0E4C7'))
        c.roundRect(x+3,y-47,width-10,48,8,fill=1,stroke=0)
        text_right(label,x+width-17,y-26,11,True)
        if i<len(labels)-1:
            c.setStrokeColor(HexColor(GREEN))
            c.line(x+2,y-23,x-8,y-23)
            c.line(x-8,y-23,x-3,y-19)
            c.line(x-8,y-23,x-3,y-27)
    y-=70


begin('מדריך קריאה חזותי | נובמבר 2026','מה בעצם בנינו?', 'חוות, חלקות וקוד - הסבר פשוט, צעד אחר צעד')
para('דמיין שלחקלאי בשם דני יש מחברת. במחברת הוא רושם את החוות שלו, את החלקות שלהן ומה גדל בכל חלקה.',size=16,gap=15)
para('אנחנו בנינו לו מחברת דיגיטלית עם שומר בכניסה: השומר בודק את הבקשות, והמחברת שומרת את המידע גם אחרי שסוגרים את התוכנה.')
path_row(['דני מבקש','השרת בודק','המסד שומר','דני מקבל תשובה'])
# A simple farm illustration drawn directly, not a fabricated application screenshot.
c.setFillColor(HexColor('#E4EEDB')); c.roundRect(70,y-150,450,142,15,fill=1,stroke=0)
c.setFillColor(HexColor('#B56D48')); c.rect(91,y-79,70,45,fill=1,stroke=0)
c.setFillColor(HexColor('#684E3B')); p=c.beginPath(); p.moveTo(81,y-34);p.lineTo(126,y+1);p.lineTo(171,y-34);p.close();c.drawPath(p,fill=1,stroke=0)
for x,label in [(195,'חלקת עגבניות'),(355,'חלקת פלפלים')]:
    c.setFillColor(HexColor('#91B774'));c.roundRect(x,y-123,140,95,7,fill=1,stroke=0)
    for row in range(3):
        for col in range(6):
            c.setFillColor(HexColor('#34785A'));c.circle(x+15+col*21,y-58-row*22,4,fill=1,stroke=0)
            c.setFillColor(HexColor('#D87957'));c.circle(x+17+col*21,y-56-row*22,2,fill=1,stroke=0)
    text_right(label,x+130,y-143,11,True)
y-=185
box('מה נלמד?','איך בקשה הופכת לרשומה במסד, למה מידע לא תקין נדחה, מה עושה כל קובץ ואיך יודעים שהמערכת עובדת.')
para('התמונות של הקוד נוצרו מתוך קובצי הפרויקט. דוגמאות של בקשות ותשובות מסומנות כדוגמאות; הן אינן צילום של ממשק קיים.',size=10,color=MUTED)

begin('01 | התמונה הגדולה','מי עושה מה?', 'מאקרו = כל המערכת. מיקרו = שורה אחת בתוך המערכת.')
box('במאקרו','בנינו שירות שרת לניהול חוות וחלקות. עדיין אין מסך חקלאי עם כפתורים: אפשר לפנות לשירות דרך בקשות או דרך תיעוד ה־API.')
sub('ארבע דמויות בסיפור')
terms([('הלקוח','מי שמבקש פעולה. למשל דפדפן, תוכנה אחרת או משתמש בתיעוד האינטראקטיבי.'),('השרת','הפקיד שמקבל את הבקשה ומפעיל את הפעולה המתאימה.'),('הבדיקות','השומר שמוודא ששמות, מידות וקשרים הגיוניים.'),('מסד הנתונים','המחברת המסודרת שבה נשמר המידע.')])
sub('הסיפור שילווה אותנו')
para('דני רוצה להוסיף לחווה שלו חלקה בשם South block. שטחה אלף מטרים רבועים, והוא מגדל בה עגבניות. השירות צריך לבדוק את הבקשה, לשמור אותה ולהחזיר מזהה.')
path_row(['בקשת יצירה','בדיקת נתונים','שמירה','תשובת הצלחה'])
box('משפט מפתח','השרת אינו רק מעביר מידע: הוא גם מחליט אם מותר לשמור אותו.')
sub('מה לא בנינו עדיין?')
para('לא בנינו חיזוי מזג אוויר, חיישנים או המלצות השקיה. הבסיס שבנינו הוא ניהול הנתונים שעליו אפשר לבנות בהמשך.',size=12)

begin('02 | הפעלה ובדיקת חיים','האם השרת ער?', 'שלב ראשון: לוודא שהבסיס עובד לפני שמוסיפים יכולות.')
source('main.py','@app.get("/health")')
sub('נקרא את התמונה כמו סיפור')
terms([('@app.get','כאשר מגיעה בקשת קריאה לכתובת הזאת, הפעל את הפונקציה שמתחת.'),('def health','הגדרת פעולה בשם health. שם הפעולה הוא בשביל הקוד.'),('return','החזר למי שפנה אלינו את התוצאה הזאת.')])
code('GET /health\n\n200 OK\n{"status": "ok"}','Illustrative HTTP request and response',lexer='bash')
box('התוצאה המוחשית','אם קיבלנו תשובה תקינה, השרת ער ומסוגל לענות. זה דומה לשיחה שבה שואלים ״אתה שם?״ ומקבלים ״כן״.')
para('חשוב להבין: בדיקת החיים אינה פותחת את המסד. לכן היא יכולה להצליח גם כשהמסד חסר, ובקשות הנתונים ייכשלו.',size=12)
sub('מילות הפעלה')
terms([('uv sync','מכין את סביבת Python ומתקין את החבילות.'),('uvicorn','התהליך שמקשיב לבקשות ומפעיל את האפליקציה.'),('main:app','הקובץ main.py והאפליקציה בשם app שבתוכו.')])

begin('03 | המחברת הדיגיטלית','מה יש בתוך המסד?', 'קובץ אחד בשם registry.db, ובתוכו חמש טבלאות.')
para('טבלה דומה לדף עם עמודות. כל שורה היא דבר אחד: חווה אחת, חלקה אחת או סוג אחד של טפטפת.')
terms([('farms','שתי חוות. למשל Demo cooperative.'),('plots','ארבע חלקות. לכל חלקה יש חווה, שטח ועוד פרטים.'),('crops','שני גידולים: עגבנייה ופלפל מתוק.'),('soils','שלושה סוגי קרקע: חול, Loam ו־Clay loam.'),('emitters','ארבע אפשרויות ספיקה של טפטפות.')])
sub('למה משתמשים במזהים?')
para('במקום לכתוב בכל חלקה את כל פרטי החווה, שומרים בה את מזהה החווה. כמו מספר תלמיד שמקשר בין התלמיד ובין הכיתה שלו.')
code('North block\n  farm_id    -> Demo cooperative\n  crop_id    -> tomato\n  soil_id    -> loam\n  emitter_id -> dripnet-pc-1.0','Conceptual links - labels shown instead of full IDs',lexer='bash')
box('מה יצר סקריפט האתחול?','חמש טבלאות ו־15 רשומות התחלתיות. הרצנו אותו פעם אחת. הרצה נוספת מוחקת את המסד בנתיב היעד ויוצרת אותו מחדש.',fill='#FBF0D7')
para('המסד המקומי אינו מועלה ל־Git. מעלים את סקריפט האתחול, כדי שאפשר יהיה לשחזר את נתוני הדוגמה במחשב אחר.',size=12)

begin('04 | חיבור למסד','פותחים, עובדים וסוגרים', 'הקובץ database.py מרכז את הדרך שבה ניגשים למחברת.')
snippet,line=actual('database.py','    connection = sqlite3.connect')
# Show the relevant body exactly, including its transaction and close behavior.
lines=(SERVICE/'database.py').read_text().splitlines()
idx=next(i for i,s in enumerate(lines) if s.startswith('    connection = sqlite3.connect'))
code('\n'.join(lines[idx:]),'database.py',first=idx+1)
terms([('sqlite3.connect','פתח חיבור לקובץ המסד. mode=rw דורש קובץ קיים.'),('foreign_keys = ON','אסור לקשר חלקה לחווה שאינה קיימת.'),('with connection','הצלחנו? שמור. הייתה שגיאה? בטל את השינויים בטרנזקציה.'),('finally / close','גם כשמשהו נכשל, נסגור את החיבור בסיום.')])
box('טרנזקציה - כמו חבילת פעולות','דמיין העברת ציוד בין שתי קופסאות. לא נרצה להוציא מהראשונה ולהיכשל לפני ההכנסה לשנייה. או שכל החבילה מצליחה, או שמבטלים את מה שנעשה בה.')
para('כאן יש קובץ אחד אמיתי בדיסק. אם שמרנו שינוי בהצלחה, הוא יישאר גם אחרי הפעלה מחדש של השירות.',size=12)

begin('05 | השומר בכניסה','איזה מידע מותר להכניס?', 'Pydantic בודק שמבנה הבקשה והערכים שלה מתאימים לכללים.')
lines=(SERVICE/'schemas.py').read_text().splitlines()
idx=next(i for i,s in enumerate(lines) if s.startswith('Name ='))
code('\n'.join(lines[idx:idx+4]),'schemas.py',first=idx+1)
terms([('min_length=1','אחרי שמסירים רווחים, צריך להישאר לפחות תו אחד בשם.'),('gt=0','המספר חייב להיות גדול מאפס.'),('ge / le','הגבול כלול: קו רוחב בין מינוס תשעים לתשעים.'),('allow_inf_nan=False','דוחים ערכים שאינם מספר סופי רגיל.')])
sub('נראה מה השומר עושה')
code('{"area_m2": 1000}  -> valid size\n{"area_m2": -20}   -> 422 VALIDATION\n{"name": "   "}    -> 422 VALIDATION\n{"lat": 95}        -> 422 VALIDATION','Illustrative field validation - not full plot bodies',lexer='json')
box('עוד בדיקות חשובות','תאריך שתילה אינו יכול להיות בעתיד. ביצירה ובעדכון בודקים גם שהחווה, הגידול, הקרקע והטפטפת קיימים במסד.')
para('יש שלושה סוגי מודלים: מה צריך כדי ליצור, מה מותר לשלוח בעדכון חלקי, ואיך הרשומה נראית בתשובה.',size=12)

begin('06 | קריאת קטלוגים','בוחרים מתוך רשימה מוכרת', 'קטלוג הוא כמו תפריט: אפשר לראות מה יש ולבחור מזהה מתאים.')
source('catalogs.py','@router.get("/crops",')
catalog_lines=(SERVICE/'catalogs.py').read_text().splitlines()
catalog_start=next(i for i,s in enumerate(catalog_lines) if s.startswith('def get_catalog_item'))
code('\n'.join(catalog_lines[catalog_start:catalog_start+5]),'catalogs.py - query excerpt',first=catalog_start+1)
terms([('GET','בקשת קריאה. מבקשים מידע בלי לשנות אותו.'),('response_model','הצורה שבה התשובה צריכה להיראות.'),('SELECT','פקודת SQL שבוחרת מידע מהטבלה.'),('WHERE id = ?','החזר רק את הפריט שהמזהה שלו תואם לערך שנשלח.')])
box('למה יש סימן שאלה בשאילתה?','את ערך המזהה מוסרים בנפרד מהפקודה. כך הערך נשאר נתון לחיפוש, ולא הופך לחלק מהוראות SQL.')
para('למשל, בקשת GET /v1/crops/tomato תחזיר קוד 200 ואת המזהה tomato והשם Tomato. זוהי דוגמת תשובה מנתוני האתחול.',size=12)
para('פריט חסר מחזיר 404. ניסיון ליצור, לעדכן או למחוק פריט קטלוג מחזיר 405. כך שומרים על רשימת ערכים מוסכמת.',size=12)

begin('07 | ניהול חוות','נוסיף חווה חדשה', 'POST מבקש ליצור דבר חדש. השרת מייצר את המזהה שלו.')
source('farms.py','@router.post', '@router.get')
terms([('201','הבקשה הצליחה ונוצרה רשומה חדשה.'),('uuid4','יוצר מזהה חדש. אפשר לחשוב עליו כמספר זיהוי של החווה.'),('INSERT INTO','הוסף שורה חדשה לטבלה.'),('return farm','החזר ללקוח את החווה שנוצרה, כולל המזהה.')])
code('POST /v1/farms\n{"name": "My farm"}\n\n201 Created\n{"id": "8c6a2e70-26c4-4f8e-9c1d-91ab1286f002",\n "name": "My farm"}','Illustrative request and response - generated ID is an example',lexer='bash')
box('ומה עם מחיקה?','חווה ריקה אפשר למחוק. חווה שיש בה חלקות מקבלת שגיאת 409, כדי שלא נאבד את הקשר בין החלקות לחווה.')

begin('08 | ניהול חלקות','מסלול של בקשת יצירה', 'חלקה צריכה יותר פרטים מחווה, כי היא קשורה לכמה סוגי מידע.')
snippet,line=actual('plots.py','@router.post','@router.get')
code(snippet,'plots.py',first=line)
terms([('body.model_dump','הפוך את המודל שנבדק למילון נתונים לעבודה עם המסד.'),('BEGIN IMMEDIATE','התחל טרנזקציית כתיבה לפני בדיקת הקשרים והשם.'),('validate_references','בדוק שהמזהים מפנים לרשומות שקיימות.'),('validate_unique_name','בדוק שאין בחווה חלקה אחרת באותו שם.')])
box('למה כל הבדיקות באותה טרנזקציה?','כדי שכתיבה אחרת לא תשנה את המצב בין הבדיקה שלנו ובין השמירה. אם הבדיקה נכשלת, לא נוצרת חלקה חלקית.')
para('התוצאה הצפויה: תשובת 201 עם כל פרטי החלקה והמזהה החדש שלה. את גוף הבקשה המלא נראה בעמוד הבא.',size=12)

begin('09 | דוגמה שאפשר לדמיין','כך נראית בקשה מלאה', 'גוף JSON לדוגמה: החווה והקטלוגים כבר קיימים בנתוני האתחול.')
payload='''{
  "farm_id": "b7e2c0a0-3c1d-4f0a-9a11-0c5d2e6f1001",
  "name": "South block",
  "area_m2": 1000,
  "crop_id": "tomato",
  "planting_date": "2026-03-01",
  "soil_id": "loam",
  "row_spacing_m": 1.5,
  "emitter_spacing_m": 0.4,
  "emitter_id": "dripnet-pc-1.0",
  "lat": 31.25,
  "lon": 34.79
}'''
code(payload,'Example body for POST /v1/plots',lexer='json')
terms([('area_m2','אלף מטרים רבועים. זה שטח החלקה.'),('row_spacing_m','מטר וחצי בין שורות הגידול.'),('emitter_spacing_m','ארבעים סנטימטרים בין טפטפות.'),('lat / lon','נקודת המיקום של החלקה במפה.')])
box('מה נראה אחרי הצלחה?','בתשובה יופיעו השדות ששלחנו ושדה id חדש. בקשת GET לרשימת החלקות תכלול עכשיו גם את South block. זו תוצאה צפויה לדוגמה; המדריך לא יצר רשומה חדשה במסד שלך.')

begin('10 | עדכון וסינון','משנים רק את מה שביקשנו', 'PATCH דומה לתיקון שורה במחברת, בלי לכתוב את כל הדף מחדש.')
lines=(SERVICE/'plots.py').read_text().splitlines()
idx=next(i for i,s in enumerate(lines) if s.startswith('def update_plot'))
code('\n'.join(lines[idx:idx+7]),'plots.py',first=idx+1)
terms([('exclude_unset=True','השתמש רק בשדות שהלקוח שלח בפועל.'),('find_plot','חפש את החלקה הקיימת. אם אינה קיימת, החזר 404.'),('plot.update','מזג לתוכה את הערכים החדשים.')])
code('Before: {"name": "South block", "area_m2": 1000}\nPATCH:  {"area_m2": 2000}\nAfter:  {"name": "South block", "area_m2": 2000}','Illustration - only two fields shown',lexer='json')
box('לא שלחתי לעומת שלחתי null','שדה שלא נשלח נשאר כפי שהיה. שדה שנשלח עם null נדחה, מפני שבמסד השדות האלה נדרשים. בקשת עדכון ריקה מותרת ואינה משנה דבר.')
begin('10ב | סינון','מוצאים רק את מה שצריך', 'רשימה קטנה וממוקדת במקום כל החלקות במערכת.')
sub('רק החלקות של חווה מסוימת')
para('אפשר להוסיף לבקשת הרשימה פרמטר farm_id. השירות יחזיר רק חלקות ששייכות לאותו מזהה. אם אין התאמות, נקבל רשימה ריקה עם קוד 200.',size=12)
source('plots.py','def list_plots', '@router.get')
code('GET /v1/plots?farm_id=<farm UUID>\n\n200 OK\n[]','Example for a farm with no matching plots',lexer='bash')
box('איך חושבים על סינון?','כמו לבקש מהמורה רק את המחברות של כיתה אחת. הבקשה אינה מוחקת מחברות אחרות; היא רק בוחרת מה להראות בתשובה.')

begin('11 | הסבר כשמשהו נכשל','שגיאה היא תשובה שימושית', 'במקום ״לא עובד״, הלקוח מקבל מספר והסבר שאפשר לפעול לפיהם.')
terms([('200 / 201 / 204','הצלחה: קראנו או עדכנו / יצרנו / מחקנו ללא גוף תשובה.'),('422 VALIDATION','המידע בבקשה לא תקין. למשל שטח שלילי.'),('404 NOT_FOUND','הרשומה שביקשנו בכתובת אינה קיימת.'),('409 CONFLICT','למשל שם חלקה כפול בחווה או מחיקת חווה עם חלקות.'),('503 UNAVAILABLE','יש בעיה בגישה למסד. התשובה מציעה לנסות שוב בעוד חמש שניות.'),('405 METHOD_NOT_ALLOWED','הפעולה אינה מותרת בנתיב הזה. למשל מחיקת גידול מהקטלוג.')])
code('HTTP 409\nContent-Type: application/problem+json\n\n{\n  "type": "about:blank",\n  "title": "Conflict",\n  "status": 409,\n  "detail": "Cannot delete a farm with plots.",\n  "instance": "/v1/farms/<farm UUID>",\n  "code": "CONFLICT"\n}','Illustrative error response - URL ID is a placeholder',lexer='json')
box('משפט מפתח','קוד HTTP אומר איזה סוג תוצאה קיבלנו. שדה code מסווג את הבעיה עבור התוכנה. שדה detail מסביר אותה לאדם.')

begin('12 | איך יודעים שזה עובד?','בדיקות וביצועים', 'לא מסתפקים בפעם אחת שבה הצלחנו ללחוץ על כפתור.')
sub('בדיקות אוטומטיות: מבחן חוזר למערכת')
para('כתבנו 12 בדיקות. בחלקן בודקים הרבה דוגמאות שונות: שטח אפס, תאריך עתידי, מזהה חסר ושם כפול. בדקנו גם שהצלחה באמת נשמרת במסד ושמחיקה מחזירה גוף ריק.')
source('tests/test_api.py','    async def test_malformed_json', '    async def test_unavailable_database')
terms([('assert_problem','ודא שקיבלנו את קוד השגיאה ואת הפורמט הצפויים.'),('מסד זמני','מחברת ניסוי שנמחקת בסיום. הנתונים המקומיים שלך נשארים במקומם.')])
sub('בדיקת ביצועים: מבחן עם שעון')
box('מה נמדד בפועל?','600 בקשות קריאה במשך דקה, בקצב כולל של עשר לשנייה. לא היו שגיאות. ה־p95 הגבוה ביותר מבין הנתיבים היה בערך 14.6 מילישניות, מול יעד של 100.')
para('דמיין מאה בקשות מסודרות מהמהירה לאטית. p95 הוא הזמן של הבקשה במקום 95. הוא מספר לנו על רוב הבקשות, ולא רק על הממוצע.',size=12)
para('המגבלה: המדידה הייתה מקומית מול מסד הדוגמה הקטן. עשר בקשות לשנייה חולקו בין עשרה נתיבים; לא נשלחו עשר לכל נתיב בנפרד.',size=11,color=MUTED)

begin('13 | שמירה ושיתוף','מה Git ו־GitHub נותנים?', 'כמו משחק עם נקודות שמירה, מסלול עבודה ומקום לשתף בו את הקוד.')
terms([('Git','שומר היסטוריה של גרסאות הקוד במחשב.'),('Commit','נקודת שמירה עם תיאור של השינוי.'),('Branch','ענף עבודה שבו אפשר להכין שינוי בנפרד.'),('Push','העלאת ה־commits מהמחשב למאגר המרוחק.'),('Pull Request','מקום להציג שינוי ולהסתכל עליו לפני השילוב.'),('Merge','שילוב השינוי בענף היעד, למשל main.'),('GitHub Actions','מנגנון שמפעיל בדיקות אוטומטיות כשיש שינוי.')])
path_row(['שינוי בקוד','Commit','Push','בדיקה ושילוב'])
sub('מה קרה בפרויקט שלנו?')
para('המימוש עלה ל־GitHub ומוזג ל־main. גם הגדרת הבדיקות האוטומטיות נמצאת שם. היא מריצה את הבדיקות על Python בגרסאות 3.12 ו־3.13.')
box('הבדל שכדאי לזכור','GitHub שומר את קוד התוכנה. הוא לא הופך מעצמו לשרת API פעיל באינטרנט. כדי שהשרת יעבוד, צריך להפעיל אותו במחשב או בסביבת אירוח.')
para('קובץ המסד המקומי הוחרג מ־Git; הסקריפט שיוצר נתוני דוגמה כן נמצא במאגר.',size=12)

begin('14 | מפת הקבצים','איפה מחפשים כל דבר?', 'כשתרצה להבין שינוי, התחל בקובץ שאחראי לחלק שלו בסיפור.')
terms([('main.py','דלת הכניסה. יוצר אפליקציה ומחבר נתיבים ושגיאות.'),('database.py','חיבור למסד, טרנזקציות וסגירה.'),('schemas.py','השדות והכללים של הבקשות והתשובות.'),('errors.py','הפורמט האחיד של השגיאות.'),('catalogs.py','קריאת גידולים, קרקעות וטפטפות.'),('farms.py','יצירה, קריאה, עדכון ומחיקה של חוות.'),('plots.py','פעולות החלקות, קשרים, שמות וסינון.'),('tests/test_api.py','בדיקות שמוכיחות שההתנהגות הצפויה מתקיימת.'),('benchmark.py','מדידת זמני תגובה של נתיבי הקריאה.'),('README.md','הוראות שימוש והרצה.'),('docs/judgment-log.md','יומן בחירות והסיבות לביצוע שלהן.')])
box('מה למדנו כאן במאקרו?','מערכת טובה משלבת נתונים מסודרים, כללים ברורים, פעולות שימושיות, תשובות מובנות ובדיקות. כל קובץ מטפל באחריות מוגדרת בתוך הסיפור הזה.')

begin('15 | נסה להסביר בעצמך','חמש שאלות קטנות', 'מותר לחזור לעמודים הקודמים. המטרה היא להבין, לא לשנן.')
sub('השאלות')
para('1. למה אסור ליצור חלקה עם שטח שלילי?')
para('2. מה יקרה לשם החלקה אם נשלח בעדכון רק שטח חדש?')
para('3. למה אי אפשר למחוק חווה שיש בה חלקות?')
para('4. האם הצלחה של בדיקת החיים מוכיחה שהמסד נגיש?')
para('5. האם שמירת הקוד ב־GitHub אומרת שהשרת פעיל באינטרנט?')
sub('תשובות בשפה פשוטה')
para('1. זה ערך שאינו מתאים לשטח אמיתי. השומר דוחה אותו עם 422.',size=12,gap=6)
para('2. השם נשאר כפי שהיה. עדכון חלקי משנה רק את מה ששלחנו.',size=12,gap=6)
para('3. החלקות צריכות להישאר קשורות לחווה קיימת. לכן נקבל 409.',size=12,gap=6)
para('4. לא. בדיקת החיים בודקת שהאפליקציה מגיבה; היא אינה פותחת את המסד.',size=12,gap=6)
para('5. לא. שמירת קוד והרצת שרת הן שתי פעולות שונות.',size=12,gap=6)
box('המשפט שכדאי לקחת איתך','אני יודע לספר איך בקשה נכנסת, איך בודקים אותה, איפה המידע נשמר ואיך חוזרת תשובה. כשאני מבין את הדרך, הקוד כבר פחות מסתורי.')

begin('16 | להרגיש את המערכת','איך רואים תוצאה במחשב?', 'תרגיל קריאה בלבד, שמשתמש בנתונים שכבר קיימים אצלך.')
sub('פתח טרמינל בתיקיית השירות והפעל')
code('uv run uvicorn main:app --host 127.0.0.1 --port 8000','Run from services/registry-service',lexer='bash')
para('אם יש שרת שכבר פועל בכתובת הזאת, השתמש בו. כאשר עובדים עם קוד מעודכן, חשוב שגם השרת יופעל מחדש.',size=12)
sub('פתח בדפדפן את הכתובת הזאת')
code('http://127.0.0.1:8000/docs','Interactive API documentation',lexer='bash')
para('בחר את GET /v1/farms, לחץ Try it out ואז Execute. תראה את שתי החוות. לאחר מכן נסה GET /v1/plots כדי לראות את ארבע החלקות מנתוני האתחול.',size=12)
box('מה אמור להופיע?','קוד תגובה 200 ורשימת JSON. לכל חווה יש id ו־name. לכל חלקה יש גם farm_id שמסביר לאיזו חווה היא שייכת.')
sub('על מה המדריך מבוסס?')
para('קטעי הקוד נלקחו מקובצי הפרויקט המקומיים. נתוני הדוגמה מבוססים על seed_registry.sh. תוצאות הביצועים מבוססות על docs/registry-benchmark.json ועל דוח המדידה. סטטוס GitHub Actions נמסר בשיחה על ידך.',size=10.5)
para('המדריך נוצר ב־8 בנובמבר 2026. תמונות הקוד הן עיבוד חזותי של קוד אמיתי, והאיור של החווה הוא המחשה בלבד. דוגמאות הבקשות אינן רישום של פעולות חדשות שבוצעו במסד.',size=10.5,color=MUTED)
end()
c.save()
doc=fitz.open(PDF)
for index,p in enumerate(doc):
    p.get_pixmap(matrix=fitz.Matrix(1.3,1.3)).save(TMP/f'page-{index+1:02d}.png')
thumbs=[]
for index in range(len(doc)):
    im=Image.open(TMP/f'page-{index+1:02d}.png').convert('RGB')
    im.thumbnail((298,422))
    thumbs.append(im)
sheet=Image.new('RGB',(298*4,450*math.ceil(len(thumbs)/4)),'#D8DDD9')
d=ImageDraw.Draw(sheet)
for index,im in enumerate(thumbs):
    x=(index%4)*298; yy=(index//4)*450
    sheet.paste(im,(x,yy));d.text((x+10,yy+425),str(index+1),fill='black')
sheet.save(TMP/'contact-sheet.png')
print(f'Created {PDF}; pages={len(doc)}; lowest text baseline={min(v for _,v in bottoms):.1f}')
