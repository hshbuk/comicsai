# Comics AI Studio

אפליקציית Web מקומית ליצירת קומיקס בעזרת AI: מודל שפה (LLM) מתכנן את הסיפור והדמויות, **ComfyUI** מייצר את האיורים ונכסי הרציפות, **Pillow** מרכיב דיאלוג וקריינות (כולל תמיכה ב-RTL בעברית) מחוץ לתמונה, והשרת המובנה מאפשר קריאה ישירה דרך **Tachiyomi / Aniyomi** ו-**OPDS** ברשת הביתית.

## יכולות עיקריות

- **תכנון סיפור היררכי** (עד 100 עמודים) בעברית או באנגלית.
- **בנק נכסי רציפות** (Project & Global Assets) לשימוש חוזר בדמויות ובמקומות בין פרויקטים.
- **חידוש פאנל בודד** ועריכת תכנון לפני ואחרי יצירה.
- **ייצוא ל-`CBZ`** (כולל `ComicInfo.xml`), `ZIP`, `JSON` ו-`Markdown`.
- **שרת קריאה מקומי** תואם **LANraragi** ו-**OPDS** לגישה מ-Tachiyomi / Mihon / Aniyomi ברשת הביתית.

## התחלה מהירה

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

לאחר ההפעלה פתחו בדפדפן: `http://127.0.0.1:8000` (או השתמשו ב-[`ComicsAI.bat`](ComicsAI.bat) לניהול אינטראקטיבי, הגדרת שרתי LLM/ComfyUI מרוחקים והצגת כתובת הרשת הביתית ל-Tachiyomi).

## תיעוד מלא (GitHub Wiki)

כל התיעוד המפורט נמצא בלשונית ה-**Wiki** של הפרויקט:

- [דף הבית של ה-Wiki](https://github.com/hshbuk/comicsai/wiki)
- [ארכיטקטורה וזרימת עבודה](https://github.com/hshbuk/comicsai/wiki/Architecture)
- [התקנה, `.env` ולוח הבקרה](https://github.com/hshbuk/comicsai/wiki/Installation-and-Configuration)
- [Workflows של ComfyUI](https://github.com/hshbuk/comicsai/wiki/ComfyUI-Workflows)
- [חיבור ל-Tachiyomi / Aniyomi / OPDS](https://github.com/hshbuk/comicsai/wiki/Reader-Server-Tachiyomi-OPDS)
- [תיעוד API מלא](https://github.com/hshbuk/comicsai/wiki/API-Reference)

## בדיקות

```powershell
python -m pytest -v
```
