# התקנה והגדרות

## דרישות מוקדמות
- **Python 3.11** ומעלה
- **שרת LLM** תואם OpenAI Chat Completions API (כגון Ollama מקומי או מרוחק)
- **שרת ComfyUI** פעיל (מקומי או על מחשב/GPU מרוחק)

## התקנה ידנית

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

## הגדרת קובץ `.env`

המערכת תומכת בהרצת האפליקציה מקומית לחלוטין, תוך הפניה ל-LLM ול-ComfyUI מקומיים או מרוחקים (למשל מחשב אחר ברשת או שרת GPU):

```env
LLM_BASE_URL=http://127.0.0.1:11434/v1
LLM_MODEL=gemma3n:e4b
LLM_API_KEY=local
COMFYUI_BASE_URL=http://127.0.0.1:8188
COMFYUI_TIMEOUT_SECONDS=300
OUTPUT_DIR=outputs
WORKFLOW_DIR=workflows
```

## הרצה דרך שורת הפקודה

- **גישה מהמחשב בלבד**:
  ```powershell
  python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
  ```
- **גישה גם מהרשת הביתית (לחיבור Tachiyomi / OPDS מהטלפון)**:
  ```powershell
  python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
  ```

## שימוש בלוח הבקרה האינטראקטיבי (`ComicsAI.bat`)

הפעלת `ComicsAI.bat` פותחת תפריט אינטראקטיבי הכולל:
1. תצוגת סטטוס חיה של השרת המקומי, שרת ה-LLM ושרת ComfyUI.
2. זיהוי והצגה של כתובת ה-LAN המקומית (`http://<LAN_IP>:8000`) לחיבור מ-Tachiyomi או OPDS.
3. הפעלה במצב רשת ביתית (`0.0.0.0`) או מקומי בלבד (`127.0.0.1`).
4. עריכת כתובות ה-LLM ו-ComfyUI בקובץ `.env` ובדיקת חיבור ישירה.

## הרצת בדיקות

```powershell
python -m pytest -v
```
