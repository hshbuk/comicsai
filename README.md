# Comics AI Studio

אפליקציית Web מקומית ליצירת קומיקס בעזרת AI: מודל שפה (LLM) מתכנן את הצ׳פטרים, הפאנלים ונכסי הרציפות; **ComfyUI** מייצר את האיורים; **Pillow + python-bidi** מרכיבים קריינות ודיאלוג (כולל תמיכה ב-RTL בעברית) מחוץ לתמונה; והשרת המובנה חושף API תואם **LANraragi** ו-**OPDS** לקריאה ישירה דרך **Tachiyomi / Mihon / Aniyomi** ברשת הביתית.

## יכולות עיקריות

- **תכנון סיפור היררכי**: תכנון רקורסיבי של כמות בלתי מוגבלת של צ׳פטרים (`pages >= 1`) עם **1–16 פאנלים בצ׳פטר** (ועד **3 `scene_views`** לפאנל) בעברית או באנגלית.
- **בנק נכסי רציפות (Project & Global Assets)**: יצירת תמונות reference לדמויות ולמקומות ושמירתן גם בספריית הפרויקט וגם בבנק הגלובלי (`outputs/global_assets/`) לייבוא לקומיקסים אחרים.
- **חידוש פאנל בודד**: עריכת תכנון לפני/אחרי יצירה וייצור מחדש של פאנל או זווית ספציפית.
- **הרכבת טקסט נקייה מחוץ לאיור**: פס קריינות עליון ורצועות דיאלוג תחתונות עם תמיכה בעברית דו־כיוונית (`python-bidi`).
- **ייצוא**: `CBZ` (עם `ComicInfo.xml` ומספור `0001.png`...), `ZIP`, `JSON` ו-`Markdown`.
- **שרת קריאה לרשת הביתית**: תאימות **LANraragi API** ו-**OPDS 1.2** לגישה מ-Tachiyomi / Mihon / Aniyomi.

## התחלה מהירה

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

לאחר ההפעלה פתחו בדפדפן: `http://127.0.0.1:8000`.  
אפשר גם להריץ את [`ComicsAI.bat`](ComicsAI.bat) לניהול אינטראקטיבי של השרת המקומי, הגדרת שרתי LLM ו-ComfyUI (מקומיים או מרוחקים) והצגת כתובת ה-LAN לחיבור מהטלפון.

## תיעוד מלא (GitHub Wiki)

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
