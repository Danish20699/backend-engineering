"""
Automated Test Suite for FastAPI Hello-World Lab
=================================================
Tests all routes: Root, FileResponse, Path parameters, Query parameters, and Pydantic POST bodies.
Run:
    python test_hello_world.py
"""

import sys
from fastapi.testclient import TestClient
from main import app

# Force UTF-8 on Windows
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

client = TestClient(app)

def run_tests():
    print("=" * 70)
    print("🧪 TESTING FASTAPI HELLO-WORLD LAB ENDPOINTS")
    print("=" * 70)

    # 1. Root
    r = client.get("/")
    assert r.status_code == 200 and r.json() == {"message": "Hello-World"}
    print("  [PASS] GET / -> {\"message\": \"Hello-World\"}")

    # 2. FileResponse index.html
    r = client.get("/new-home")
    assert r.status_code == 200 and "Hello from FastAPI" in r.text
    print("  [PASS] GET /new-home -> Serves index.html successfully")

    # 3. FileResponse contact.html
    r = client.get("/contact")
    assert r.status_code == 200 and "Get in Touch" in r.text
    print("  [PASS] GET /contact -> Serves contact.html successfully")

    # 4. Users static route
    r = client.get("/users")
    assert r.status_code == 200 and r.json() == {"message": "This is user page"}
    print("  [PASS] GET /users -> {\"message\": \"This is user page\"}")

    # 5. Dynamic user path parameter
    r = client.get("/users/42")
    assert r.status_code == 200 and r.json() == {"message": "This is user 42 page"}
    print("  [PASS] GET /users/42 -> {\"message\": \"This is user 42 page\"}")

    # 6. Invalid user path parameter (string instead of int -> 422)
    r = client.get("/users/not-an-int")
    assert r.status_code == 422
    print("  [PASS] GET /users/not-an-int -> 422 Unprocessable Entity (Type Validation)")

    # 7. Nested path parameter
    r = client.get("/users/42/contact")
    assert r.status_code == 200 and "911" in r.json()["message"]
    print("  [PASS] GET /users/42/contact -> Contact message verified")

    # 8. Dynamic blog id
    r = client.get("/blog/101")
    assert r.status_code == 200 and r.json() == {"Type": "blog", "id": 101}
    print("  [PASS] GET /blog/101 -> Blog dynamic ID verified")

    # 9. Query parameters
    r = client.get("/blog?limit=15&published=false")
    assert r.status_code == 200 and r.json()["limit"] == 15 and r.json()["Published"] is False
    print("  [PASS] GET /blog?limit=15&published=false -> Query parameters verified")

    # 10. POST Blog with Pydantic model
    blog_data = {"id": 1, "title": "Mastering FastAPI", "body": "FastAPI is incredible!"}
    r = client.post("/blog", json=blog_data)
    assert r.status_code == 200 and r.json()["message"] == "Blog is saved"
    print("  [PASS] POST /blog -> Pydantic request validation verified")

    # 11. POST Contact Form
    contact_data = {"name": "Danish", "email": "danish@example.com", "message": "Practicing FastAPI!"}
    r = client.post("/api/contact", json=contact_data)
    assert r.status_code == 200 and "Danish" in r.json()["message"]
    print("  [PASS] POST /api/contact -> Contact form submission verified")

    print("=" * 70)
    print("🎉 ALL 11 TESTS PASSED! Your Hello-World app is ready to practice!")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()
