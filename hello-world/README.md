# FastAPI Hello World & Core Fundamentals

Hands-on practical lab for **FastAPI**, covering basic routing, HTML file serving (`FileResponse`), path parameters, query parameters, and Pydantic request models.

---

## 📋 Step-by-Step Setup Guide

### Step 1: Navigate to Project Directory
```bash
cd hello-world
```

### Step 2: Create and Activate Virtual Environment (Optional / Recommended)
```bash
# On Windows PowerShell:
python -m venv .venv
.venv\Scripts\Activate.ps1

# On Linux/macOS:
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
# Or directly:
pip install fastapi uvicorn
```

### Step 4: Run the FastAPI App using Uvicorn
```bash
uvicorn main:app --reload
```
* **`main`**: The Python file name (`main.py`) without the `.py` extension.
* **`app`**: The variable name for the `FastAPI()` application instance defined inside `main.py`.
* **`--reload`**: Enables hot-reloading so code edits immediately refresh without restarting the server.

---

## 🌐 Routes & Endpoints to Practice

| Method | Endpoint | Description | Expected Response |
|---|---|---|---|
| `GET` | `/` | Root greeting | JSON: `{"message": "Hello-World"}` |
| `GET` | `/new-home` | Static HTML page | Renders `index.html` card in browser |
| `GET` | `/contact` | Interactive Contact form | Renders `contact.html` with AJAX form |
| `GET` | `/users` | Static users page | JSON: `{"message": "This is user page"}` |
| `GET` | `/users/{id}` | Dynamic path parameter | JSON: `{"message": "This is user {id} page"}` |
| `GET` | `/users/{id}/contact` | Nested path parameter | JSON with user contact info |
| `GET` | `/blog/{id}` | Dynamic blog identifier | JSON: `{"Type": "blog", "id": id}` |
| `GET` | `/blog` | Query parameters | Try: `?limit=10&published=false` |
| `POST`| `/blog` | Pydantic model body | Accepts JSON `{"id": 1, "title": "...", "body": "..."}` |
| `POST`| `/api/contact` | Contact form submission | Accepts JSON `{"name": "...", "email": "...", "message": "..."}` |

---

## 🧪 Interactive Swagger Documentation
Once the server is running:
* **Interactive Docs (Swagger UI)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **ReDoc Technical Manual**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
