import os
from typing import Optional
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 1. Create an Application Instance
app = FastAPI(
    title="FastAPI Hello World Web App",
    description="Hands-on learning by doing: routing, HTML file serving, dynamic path parameters, query parameters, and Pydantic validation.",
    version="1.0.0"
)

# 2. App decorator for HTTP GET request at ROOT URL "/"
@app.get("/")
def read_root():
    return {"message": "Hello-World"}

# 3. Serve Static HTML Pages via FileResponse
@app.get("/new-home")
def read_home():
    return FileResponse(os.path.join(BASE_DIR, "index.html"))

@app.get("/contact")
def read_contact():
    return FileResponse(os.path.join(BASE_DIR, "contact.html"))

# 4. Basic Static Route
@app.get("/users")
def read_users():
    return {"message": "This is user page"}

# 5. Dynamic Route and Type Validation (Path Parameters)
@app.get("/users/{id}")
def read_user(id: int):
    return {"message": f"This is user {id} page"}

@app.get("/users/{id}/contact")
def read_user_contact(id: int):
    return {"message": f"This is user {id} contact page. His contact no. is 911"}

# 6. Dynamic Route for Blog
@app.get("/blog/{id}")
def get_blog(id: int):
    return {"Type": "blog", "id": id}

@app.get("/blog/{id}/comments")
def get_blog_comments(id: int):
    return {"Type": "Comments", "Blog-id": id}

# 7. Query Parameters (with default values and optional types)
@app.get("/blog")
def list_blogs(
    limit: int = 5,
    published: bool = True,
    num_comments: Optional[int] = None,
    sort: Optional[bool] = None
):
    return {
        "Type": "blog",
        "limit": limit,
        "Published": published,
        "no. Of comments": num_comments,
        "sort": sort
    }

# 8. Pydantic Model for POST Request Body
class Blog(BaseModel):
    id: int
    title: str
    body: str
    published: Optional[bool] = True

@app.post("/blog")
def create_blog(new_blog: Blog):
    return {
        "message": "Blog is saved",
        "Title": new_blog.title,
        "Body": new_blog.body,
        "id": new_blog.id
    }

# 9. Contact Form POST Handler for AJAX Submission
class ContactMessage(BaseModel):
    name: str
    email: str
    message: str

@app.post("/api/contact")
def submit_contact(contact: ContactMessage):
    return {
        "status": "success",
        "message": f"Thank you, {contact.name}! Your message has been received."
    }

if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 70)
    print("🚀 FastAPI Hello-World App Running")
    print("📍 URL: http://127.0.0.1:8000")
    print("📖 Docs: http://127.0.0.1:8000/docs")
    print("=" * 70 + "\n")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
