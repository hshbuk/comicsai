# Comics AI Studio

אפליקציית Web מקומית ליצירת קומיקס בעזרת AI: מודל שפה (LLM) מתכנן את הסיפור, הדמויות, המקומות והפאנלים; **ComfyUI** מייצר את האיורים ונכסי הרציפות; **Pillow + python-bidi** מרכיבים טקסט ודיאלוג (כולל RTL בעברית) מחוץ לתמונה; והשרת חושף גם **API תואם LANraragi ו-OPDS** לגישה ישירה מקוראי קומיקס כמו **Tachiyomi / Mihon / Aniyomi** ברשת הביתית.

---

## יכולות עיקריות

- **תכנון סיפור היררכי (עד 100 עמודים)**: פירוק אוטומטי של בריף קצר לעלילה, צ'פטרים, דפים ופאנלים (1–3 פריימים עוקבים לסצנה) בעברית או באנגלית (`app/llm_client.py`).
- **בנק נכסי רציפות (Global & Project Assets)**: יצירת תמונות reference לדמויות ולמקומות לפני יצירת הדפים, שמירתם בספריית הפרויקט ובבנק הגלובלי (`outputs/global_assets`), ואפשרות לייבא אותם לקומיקסים חדשים.
- **עבודה עם ComfyUI Workflows**: תמיכה ב-SDXL, IPAdapter לרפרנס תמונתי, Flux, ו-H3, כולל בדיקת תקינות nodes ושחרור זיכרון GPU בין שלבים (`app/comfyui_client.py`).
- **הרכבת טקסט נקייה (Pillow + RTL)**: בועות דיאלוג וקריינות מתווספות ברצועות ייעודיות מחוץ לאיור כדי למנוע ג'יבריש או הסתרת ציור (`app/text_overlay.py`).
- **חידוש פאנל בודד**: אפשרות לייצר מחדש פאנל/זווית ספציפית מתוך הממשק או ה-API (`POST /api/generate/panel`).
- **ייצוא למספר פורמטים**:
  - `CBZ` עם `ComicInfo.xml` ומספור עמודים עוקב (מותאם ל-Tachiyomi / Aniyomi).
  - `ZIP` מלא של תיקיית הפרויקט.
  - `JSON` (תכנון ומטא-דאטה).
  - `Markdown` (תסריט מלא).
- **שרת ספרייה מקומי לקוראי קומיקס**:
  - **LANraragi-compatible API** (`/api/info`, `/api/search`, `/api/archives/...`) לחיבור ישיר מהטלפון דרך ההרחבה הרשמית של **Tachiyomi / Mihon / Aniyomi**.
  - **OPDS 1.2 Catalog** (`/opds`) להורדת קבצי `.cbz` ישירות מקוראים תומכי OPDS.

---

## ארכיטקטורה וזרימת עבודה

```
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

1. **תכנון מקדים (`POST /api/plan`)**: ה-LLM מחלץ דמויות, מקומות, ודפים עם תיאורי סצנה באנגלית עבור מחולל התמונות ודיאלוג/קריינות בשפת המשתמש (`he` / `en`).
2. **ייצור אסינכרוני (`POST /api/generate/start`)**:
   - שלב א': ייצור תמונות reference לנכסים ושמירה ב-`outputs/<project_id>/assets/` וב-`outputs/global_assets/`.
   - שלב ב': ייצור הפאנלים תוך הזרקת תיאורי הדמויות ושימוש ב-IPAdapter (אם ה-workflow תומך ב-`__REFERENCE_IMAGE__`).
   - שלב ג': הוספת טקסט דיאלוג/קריינות באמצעות `compose_panel()`.
3. **קריאה וייצוא**: צפייה בממשק הדפדפן, ייצוא `CBZ`/`ZIP`/`JSON`/`Markdown`, או גישה ישירה דרך Tachiyomi/OPDS ברשת הביתית.

---

## מבנה הפרויקט

```text
├── app/
│   ├── main.py             # נקודת הכניסה של FastAPI וכל ה-routes
│   ├── config.py           # טעינת משתני סביבה (.env) והגדרת נתיבים
│   ├── models.py           # מודלי Pydantic לבקשות, תכנון, נכסים ופאנלים
│   ├── llm_client.py       # תקשורת עם LLM (תכנון היררכי וחילוץ JSON)
│   ├── comfyui_client.py   # תקשורת עם ComfyUI API, הזרקת placeholders ובדיקת nodes
│   ├── service.py          # לוגיקת יצירת פרויקטים, jobs, בנק נכסים וייצוא (CBZ/ZIP/MD)
│   ├── text_overlay.py     # הרכבת דיאלוג וקריינות עם Pillow ותמיכת RTL
│   └── reader_api.py       # שרת קוראים תואם LANraragi API ו-OPDS 1.2
├── static/
│   └── index.html          # ממשק המשתמש המלא (תכנון, יצירה/עריכה, בנק נכסים)
├── workflows/              # תבניות ComfyUI בפורמט API JSON
│   ├── single_panel_sdxl_api.json
│   ├── single_panel_sdxl_ipadapter_api.json
│   ├── h3_single_panel_api.json
│   ├── example_flux_txt2img_api.json
│   └── comic_page_make_api.json
├── tests/
│   ├── conftest.py
│   ├── test_core.py
│   └── test_reader_api.py
├── ComicsAI.bat            # לוח בקרה אינטראקטיבי להרצה מקומית והגדרת שרתים מרוחקים
├── .env.example            # תבנית הגדרות סביבה
├── requirements.txt        # תלויות Python
└── README.md
```

---

## התקנה והפעלה

### דרישות מוקדמות
- Python 3.11 ומעלה
- שרת LLM תואם OpenAI API (כגון Ollama מקומי או מרוחק)
- שרת ComfyUI פעיל (מקומי או על מחשב/GPU מרוחק)

### התקנה ידנית
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

ערכו את `.env` לפי הצורך (ניתן להפנות לכתובת מקומית או לשרת מרוחק):
```env
LLM_BASE_URL=http://127.0.0.1:11434/v1
LLM_MODEL=gemma3n:e4b
LLM_API_KEY=local
COMFYUI_BASE_URL=http://127.0.0.1:8188
COMFYUI_TIMEOUT_SECONDS=300
OUTPUT_DIR=outputs
WORKFLOW_DIR=workflows
```

### הפעלה דרך שורת הפקודה
- **גישה מהמחשב בלבד**:
  ```powershell
  python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
  ```
- **גישה גם מהרשת הביתית (עבור Tachiyomi / OPDS בטלפון)**:
  ```powershell
  python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
  ```

### הפעלה דרך לוח הבקרה האינטראקטיבי (`ComicsAI.bat`)
הפעלת `ComicsAI.bat` (או קיצור הדרך על שולחן העבודה) פותחת תפריט אינטראקטיבי הכולל:
- הצגת סטטוס השרת המקומי, ה-LLM ו-ComfyUI.
- הצגת כתובת הרשת הביתית (`http://<LAN_IP>:8000`) לחיבור ב-Tachiyomi / OPDS.
- הפעלה במצב מקומי (`127.0.0.1`) או במצב רשת ביתית (`0.0.0.0`).
- עריכת כתובות LLM ו-ComfyUI (מקומי או מרוחק) ישירות בקובץ `.env` ובדיקת חיבור.

---

## חיבור קוראי קומיקס (Tachiyomi / Mihon / Aniyomi / OPDS)

1. הפעילו את השרת במצב רשת ביתית (`--host 0.0.0.0 --port 8000` או אפשרות `[1]` ב-`ComicsAI.bat`).
2. ודאו שהטלפון והמחשב מחוברים לאותה רשת Wi-Fi ביתית (ושפורט `8000` מאושר בחומת האש של Windows אם נדרש).
3. באפליקציית **Tachiyomi / Mihon / Aniyomi**:
   - התקינו את ההרחבה הרשמית **LANraragi**.
   - בהגדרות ההרחבה הזינו את כתובת ה-LAN שמופיעה ב-`ComicsAI.bat` (למשל `http://192.168.1.25:8000`), ללא סיסמה.
   - כל הפרויקטים שיצרתם יופיעו עם כריכה, תקציר ודפים לקריאה או להורדה.
4. בקוראי **OPDS** (כגון KOReader / Panels / Moon+ Reader):
   - הוסיפו קטלוג בכתובת `http://<LAN_IP>:8000/opds`.

---

## תיעוד API

### ניהול ותכנון
- `GET /api/health` — בדיקת תקינות ורשימת workflows זמינים.
- `POST /api/plan` — יצירת תכנון קומיקס מובנה (`BookPlan`) מתוך `PlanRequest`.
- `POST /api/generate` — יצירה סינכרונית של קומיקס שלם.
- `POST /api/generate/start` — התחלת job אסינכרוני להפקת קומיקס (מחזיר `job_id` ו-`project_id`).
- `GET /api/jobs/{job_id}` — מעקב התקדמות של job פעיל.
- `POST /api/generate/panel` — ייצור מחדש של פאנל/זווית בודדת בפרויקט קיים.

### Workflows ונכסים
- `GET /api/workflows` — רשימת קובצי ה-workflow בתיקיית `workflows/`.
- `GET /api/workflows/{name}/validate` — בדיקת nodes חסרים מול שרת ComfyUI.
- `POST /api/workflows/upload` — העלאת workflow חדש בפורמט API JSON.
- `GET /api/assets` — רשימת כל הנכסים הגלובליים השמורים (`outputs/global_assets/registry.json`).
- `POST /api/assets/import` — ייבוא נכס קיים מבנק הנכסים לתוך פרויקט.

### פרויקטים וייצוא
- `GET /api/projects` — רשימת הפרויקטים השמורים.
- `GET /api/projects/{project_id}` — טעינת פרטי פרויקט (`project.json`).
- `POST /api/projects/{project_id}/save` — שמירת שינויים בתכנון הפרויקט.
- `GET /api/projects/{project_id}/export?format={zip|cbz|json|markdown}` — ייצוא הפרויקט.

### שרת קריאה (LANraragi & OPDS)
- `GET /api/info` — פרטי השרת במבנה LANraragi.
- `GET /api/search` / `GET /api/archives` — חיפוש ורשימת פרויקטים.
- `GET /api/archives/{arcid}/metadata` — מטא-דאטה של פרויקט.
- `GET /api/archives/{arcid}/thumbnail` — תמונת השער.
- `GET /api/archives/{arcid}/files` — רשימת כתובות העמודים.
- `GET /api/archives/{arcid}/page?path=...` — קבלת קובץ התמונה של עמוד.
- `GET /api/archives/{arcid}/download` — הורדת קובץ `.cbz`.
- `GET /opds` — פיד OPDS 1.2 (Atom XML).

---

## התאמת Workflows של ComfyUI

המערכת תומכת ב-placeholders הבאים בתוך קובצי JSON בפורמט **API** של ComfyUI:
- `__PROMPT__` — הפרומפט של הפאנל/נכס.
- `__NEGATIVE_PROMPT__` — הפרומפט השלילי.
- `__SEED__` — seed מספרי.
- `__REFERENCE_IMAGE__` — שם קובץ תמונת הרפרנס שהועלתה ל-ComfyUI (עבור IPAdapter).

---

## בדיקות

```powershell
python -m pytest
```
