# ארכיטקטורה וזרימת עבודה

## תרשים מערכת

```text
┌─────────────────┐      ┌──────────────────────┐      ┌──────────────────────────┐
│  Web UI (HTML)  │ ───► │  FastAPI Backend     │ ───► │  LLM (Ollama / OpenAI)   │
│ static/index.html│      │  app/main.py         │      │  תכנון עלילה ונכסים     │
└─────────────────┘      │  app/service.py      │      └──────────────────────────┘
                         │                      │      ┌──────────────────────────┐
┌─────────────────┐      │  app/reader_api.py   │ ───► │  ComfyUI Server          │
│ Tachiyomi / OPDS│ ◄─── │  (LANraragi + OPDS)  │      │  ייצור נכסים ופאנלים    │
└─────────────────┘      └──────────┬───────────┘      └──────────────────────────┘
                                    ▼
                         ┌──────────────────────┐
                         │  outputs/<project>/  │
                         │  + global_assets/    │
                         └──────────────────────┘
```

## זרימת עבודה (Pipeline)

1. **תכנון מקדים (`POST /api/plan`)**:
   - `app/llm_client.py` מבצע תכנון היררכי ורקורסיבי (עד 100 עמודים).
   - מחולצים נכסי רציפות (דמויות ומקומות) עם תיאור ויזואלי באנגלית עבור מחולל התמונות.
   - כל פאנל כולל תיאור סצנה באנגלית, `scene_views` (1–3 פריימים עוקבים), ודיאלוג/קריינות בשפת המשתמש (`he` או `en`).
2. **ייצור אסינכרוני (`POST /api/generate/start`)**:
   - **שלב א' — נכסי רציפות**: יצירת תמונות reference לדמויות ולמקומות ושמירתן ב-`outputs/<project_id>/assets/` וגם בבנק הגלובלי `outputs/global_assets/` (`registry.json`).
   - **שלב ב' — ייצור פאנלים**: הזרקת תיאורי הדמויות והפעולה לתוך ה-Workflow של ComfyUI. אם ה-Workflow תומך ב-`__REFERENCE_IMAGE__` (IPAdapter), תמונת הרפרנס המתאימה מועלית אוטומטית ל-ComfyUI.
   - **שלב ג' — הרכבת טקסט (`app/text_overlay.py`)**: דיאלוג וקריינות מתווספים ברצועות נפרדות מחוץ לאיור באמצעות `Pillow` ו-`python-bidi` (לתיקון RTL בעברית) על הפריים הראשון של הסצנה.
3. **עריכה וייצוא**:
   - ניתן לחדש פאנל בודד (`POST /api/generate/panel`) או לייבא נכסים מבנק הנכסים הגלובלי (`POST /api/assets/import`).
   - ניתן לייצא ל-`CBZ` (כולל `ComicInfo.xml`), `ZIP`, `JSON` או `Markdown`.

## מבנה הקבצים בפרויקט

```text
├── app/
│   ├── main.py             # נקודת הכניסה של FastAPI וכל ה-routes
│   ├── config.py           # טעינת משתני סביבה (.env) והגדרת נתיבים
│   ├── models.py           # מודלי Pydantic לבקשות, תכנון, נכסים ופאנלים
│   ├── llm_client.py       # תקשורת עם LLM (תכנון היררכי וחילוץ JSON)
│   ├── comfyui_client.py   # תקשורת עם ComfyUI API, הזרקת placeholders ובדיקת nodes
│   ├── service.py          # לוגיקת יצירת פרויקטים, jobs, בנק נכסים וייצוא
│   ├── text_overlay.py     # הרכבת דיאלוג וקריינות עם Pillow ותמיכת RTL
│   └── reader_api.py       # שרת קוראים תואם LANraragi API ו-OPDS 1.2
├── static/
│   └── index.html          # ממשק המשתמש המלא (תכנון, יצירה/עריכה, בנק נכסים)
├── workflows/              # תבניות ComfyUI בפורמט API JSON
├── tests/                  # בדיקות יחידה (pytest)
├── ComicsAI.bat            # לוח בקרה אינטראקטיבי להרצה מקומית והגדרת שרתים
├── .env.example            # תבנית הגדרות סביבה
└── requirements.txt        # תלויות Python
```
