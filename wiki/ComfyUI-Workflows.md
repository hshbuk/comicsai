# Workflows של ComfyUI

כל ה-Workflows של ComfyUI נשמרים בתיקיית `workflows/` בפורמט **API JSON** (Export API מתוך ComfyUI, ולא קובץ ה-UI הרגיל).

## Workflows מובנים

- `single_panel_sdxl_api.json` — ייצור פאנל יחיד במודל SDXL.
- `single_panel_sdxl_ipadapter_api.json` — ייצור פאנל יחיד עם IPAdapter לשימוש בתמונת reference של דמות/מקום (דורש CLIP Vision מותקן ב-ComfyUI).
- `h3_single_panel_api.json` — תבנית H3 לפאנל יחיד.
- `example_flux_txt2img_api.json` — דוגמה ל-Flux.
- `comic_page_make_api.json` — ניסיוני (משתמש ב-node `Generate Comic` ליצירת עמוד שלם; אינו ברירת המחדל).

## Placeholders נתמכים

בתוך קובץ ה-JSON של ה-Workflow ניתן להציב את המחרוזות הבאות, והשרת יחליף אותן אוטומטית בזמן אמת:

| Placeholder | משמעות |
|---|---|
| `__PROMPT__` | הפרומפט החיובי של הפאנל או הנכס |
| `__NEGATIVE_PROMPT__` | הפרומפט השלילי |
| `__SEED__` | ערך ה-seed המספרי |
| `__REFERENCE_IMAGE__` | שם הקובץ של תמונת הרפרנס שהועלתה ל-ComfyUI |

## בדיקת תקינות Workflow
לפני יצירה ניתן לבדוק דרך הממשק או דרך `GET /api/workflows/{name}/validate` שכל ה-nodes הנדרשים ב-Workflow אכן מותקנים בשרת ComfyUI.
