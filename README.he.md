<div dir="rtl">

**שפה:** [English](README.md) | עברית

# Comics AI Studio

אפליקציית אינטרנט מקומית ליצירת קומיקס באמצעות בינה מלאכותית. מודל השפה מתכנן את הפרקים, הפאנלים ונכסי הרציפות; שרת ה־ComfyUI מייצר את האיורים; ספריות Pillow ו־python-bidi מרכיבות פסי קריינות ודיאלוג מחוץ לאיור עם תמיכה מלאה בעברית מימין לשמאל; והשרת המובנה חושף ממשק תואם LANraragi וקטלוג OPDS לגישה ישירה מתוך אפליקציות קריאה כמו Tachiyomi, Mihon ו־Aniyomi ברשת הביתית.

## יכולות עיקריות

- **תכנון סיפור היררכי**: תכנון רקורסיבי ללא הגבלת מספר פרקים או פאנלים לפרק, עם תמיכה בעברית ובאנגלית.
- **בנק נכסי רציפות**: יצירת תמונות ייחוס לדמויות ולמקומות ושמירתן גם בתיקיית הפרויקט וגם במאגר הגלובלי לשימוש חוזר בקומיקסים נוספים.
- **חידוש פאנל בודד**: עריכת התכנון לפני או אחרי הייצור ויצירה מחדש של פאנל או זווית ספציפית.
- **הרכבת טקסט נקייה**: הצבת קריינות ודיאלוג ברצועות ייעודיות מחוץ לתמונה כדי למנוע הסתרה של האיור או שיבוש אותיות.
- **ייצוא למגוון פורמטים**: תמיכה בפורמט CBZ הכולל קובץ מטא־דאטה ComicInfo.xml ומספור עמודים עוקב, וכן ZIP, JSON ו־Markdown.
- **שרת קריאה ברשת הביתית**: חיבור ישיר לקוראי קומיקס דרך פרוטוקול LANraragi או קטלוג OPDS 1.2.

## התחלה מהירה

</div>

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

<div dir="rtl">

לאחר ההפעלה פתחו בדפדפן את הכתובת `http://127.0.0.1:8000`. ניתן גם להשתמש בקובץ [`ComicsAI.bat`](ComicsAI.bat) לניהול אינטראקטיבי של השרת, להגדרת כתובות מקומיות או מרוחקות לשרתי החישוב ולהצגת כתובת הרשת הביתית לחיבור מהטלפון.

## תיעוד מלא ב־Wiki

- [דף הבית בעברית](https://github.com/hshbuk/comicsai/wiki/Home-HE)
- [ארכיטקטורה וזרימת עבודה](https://github.com/hshbuk/comicsai/wiki/Architecture-HE)
- [התקנה והגדרות](https://github.com/hshbuk/comicsai/wiki/Installation-and-Configuration-HE)
- [תבניות ComfyUI](https://github.com/hshbuk/comicsai/wiki/ComfyUI-Workflows-HE)
- [שרת קריאה לטאצ'יומי ו־OPDS](https://github.com/hshbuk/comicsai/wiki/Reader-Server-Tachiyomi-OPDS-HE)
- [תיעוד ממשק ה־API](https://github.com/hshbuk/comicsai/wiki/API-Reference-HE)

## הרצת בדיקות

</div>

```powershell
python -m pytest -v
```
