# תיעוד API מלא

## ניהול ותכנון

| Method | Endpoint | תיאור |
|---|---|---|
| `GET` | `/api/health` | בדיקת תקינות השרת ורשימת ה-workflows הזמינים |
| `POST` | `/api/plan` | יצירת תכנון קומיקס מובנה (`BookPlan`) מתוך `PlanRequest` |
| `POST` | `/api/generate` | יצירה סינכרונית של קומיקס שלם |
| `POST` | `/api/generate/start` | התחלת job אסינכרוני (מחזיר `job_id` ו-`project_id`) |
| `GET` | `/api/jobs/{job_id}` | בדיקת סטטוס והתקדמות של job פעיל |
| `POST` | `/api/generate/panel` | ייצור מחדש של פאנל/זווית בודדת בפרויקט קיים |

## Workflows ונכסי רציפות

| Method | Endpoint | תיאור |
|---|---|---|
| `GET` | `/api/workflows` | רשימת קובצי ה-workflow בתיקיית `workflows/` |
| `GET` | `/api/workflows/{name}/validate` | בדיקת תקינות nodes מול שרת ComfyUI |
| `POST` | `/api/workflows/upload` | העלאת קובץ workflow חדש (`.json`) |
| `GET` | `/api/assets` | רשימת כל הנכסים הגלובליים (`outputs/global_assets/registry.json`) |
| `POST` | `/api/assets/import` | ייבוא נכס מבנק הנכסים לתוך פרויקט קיים |

## פרויקטים וייצוא

| Method | Endpoint | תיאור |
|---|---|---|
| `GET` | `/api/projects` | רשימת הפרויקטים השמורים |
| `GET` | `/api/projects/{project_id}` | טעינת `project.json` של פרויקט |
| `POST` | `/api/projects/{project_id}/save` | שמירת שינויים בתכנון הפרויקט |
| `GET` | `/api/projects/{project_id}/export?format={zip\|cbz\|json\|markdown}` | ייצוא הפרויקט בפורמט המבוקש |

## שרת קריאה (LANraragi & OPDS)

| Method | Endpoint | תיאור |
|---|---|---|
| `GET` | `/api/info` | פרטי השרת במבנה LANraragi |
| `GET` | `/api/categories` | רשימת קטגוריות |
| `GET` | `/api/archives` | רשימת כל הפרויקטים הזמינים |
| `GET` | `/api/search` | חיפוש וסינון פרויקטים (`filter`, `start`, `sortby`, `order`) |
| `GET` | `/api/search/random` | שליפת פרויקטים אקראיים |
| `GET` | `/api/archives/{arcid}/metadata` | מטא-דאטה של פרויקט |
| `GET` | `/api/archives/{arcid}/thumbnail` | תמונת השער של הפרויקט |
| `GET` | `/api/archives/{arcid}/files` | רשימת כתובות הדפים של הפרויקט |
| `GET` | `/api/archives/{arcid}/page?path=...` | קבלת קובץ התמונה של עמוד |
| `GET` | `/api/archives/{arcid}/download` | הורדת קובץ `.cbz` |
| `GET` | `/opds` | פיד OPDS 1.2 (Atom XML) |
