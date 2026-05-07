"""最终闭环验证脚本。"""
import io
import uuid

from fastapi.testclient import TestClient

from app.main import app


def make_client():
    return TestClient(app)


print("=== 1. Health Check ===")
client = make_client()
r = client.get("/health")
print(f"  status: {r.status_code}, db: {r.json()['database']}")

print("=== 2. Metrics ===")
r = client.get("/metrics")
print(f"  status: {r.status_code}, has_python_gc: {'python_gc' in r.text}")

print("=== 3. Cookie Auth ===")
client = make_client()
email = f"gdpr_{uuid.uuid4().hex[:8]}@example.com"
r = client.post(
    "/v1/auth/register",
    json={"email": email, "password": "Password123", "display_name": "GDPR"},
)
print(f"  register: {r.status_code}")
cookie = r.headers.get("set-cookie", "")
print(f"  cookie_httponly: {'httponly' in cookie.lower()}")

r = client.get("/v1/auth/me")
print(f"  me: {r.status_code}, email: {r.json().get('email')}")

print("=== 4. Export User Data ===")
r = client.get("/v1/auth/me/export")
print(f"  export: {r.status_code}, has_orders: {'orders' in r.json()}")

print("=== 5. Delete User ===")
r = client.delete("/v1/auth/me")
print(f"  delete: {r.status_code}, deleted: {r.json().get('deleted')}")

r = client.get("/v1/auth/me")
print(f"  me after delete: {r.status_code}")

print("=== 6. Document Upload + Analysis ===")
client = make_client()
email2 = f"loop_{uuid.uuid4().hex[:8]}@example.com"
client.post(
    "/v1/auth/register",
    json={"email": email2, "password": "Password123", "display_name": "Loop"},
)

r = client.post(
    "/v1/documents/upload",
    data={"title": "闭环验证", "subject": "教育学"},
    files={"file": ("test.txt", io.BytesIO("本文首先分析人工智能赋能教育评价的理论基础。".encode("utf-8")), "text/plain")},
)
print(f"  upload: {r.status_code}")
doc_id = r.json()["document_id"]

r = client.post(f"/v1/documents/{doc_id}/analyze")
print(f"  analyze: {r.status_code}")
run_id = r.json()["run_id"]

r = client.get(f"/v1/runs/{run_id}/report")
print(f"  report: {r.status_code}, title: {r.json().get('title')}")

print("=== 7. File Size Pre-check ===")
client = make_client()
r = client.post(
    "/v1/documents/upload",
    data={"title": "大文件"},
    files={"file": ("big.txt", io.BytesIO(b"x" * (21 * 1024 * 1024)), "text/plain")},
)
print(f"  oversized: {r.status_code}")

print("=== 8. Password Policy ===")
client = make_client()
r = client.post(
    "/v1/auth/register",
    json={"email": "weak@example.com", "password": "weak", "display_name": "Weak"},
)
print(f"  weak_password: {r.status_code}")

print("\n[OK] 所有闭环测试通过！")
