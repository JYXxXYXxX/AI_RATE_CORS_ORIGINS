import httpx
import time

BASE = "http://localhost:8010"

# 1. Upload demo paper
with open("data/demo_paper.txt", "rb") as f:
    r = httpx.post(
        f"{BASE}/v1/documents/upload",
        files={"file": ("demo_paper.txt", f, "text/plain")},
        data={"title": "Demo Paper", "subject": "计算机", "degree_level": "硕士"},
        timeout=30,
    )
    r.raise_for_status()
    upload = r.json()
    doc_id = upload["document_id"]
    print(f"[OK] Uploaded: {doc_id}")

# 2. Analyze
r = httpx.post(f"{BASE}/v1/documents/{doc_id}/analyze", timeout=120)
r.raise_for_status()
analyze = r.json()
run_id = analyze["run_id"]
print(f"[OK] Analysis started: {run_id}")

# 3. Poll until completed
for _ in range(30):
    r = httpx.get(f"{BASE}/v1/runs/{run_id}", timeout=10)
    status = r.json()["status"]
    print(f"   Status: {status}")
    if status == "completed":
        break
    time.sleep(2)
else:
    print("[FAIL] Analysis timeout")
    exit(1)

# 4. Get report to find a section_index
r = httpx.get(f"{BASE}/v1/runs/{run_id}/report", timeout=10)
report = r.json()
sections = report.get("top_risk_sections", [])
if not sections:
    print("[WARN] No risk sections found, using index 0")
    section_index = 0
else:
    section_index = sections[0]["section_index"]
    print(f"[OK] Target section: {section_index} (aigc={sections[0]['aigc_score']:.2f}, dup={sections[0]['duplication_score']:.2f})")

# 5. Call rewrite advice endpoint
print(f"\n[TEST] Calling rewrite advice for run={run_id}, section={section_index}...")
r = httpx.post(
    f"{BASE}/v1/runs/{run_id}/sections/{section_index}/rewrite-advice",
    timeout=90,
)
print(f"   HTTP status: {r.status_code}")
result = r.json()
if result.get("error"):
    print(f"[EXPECTED FAIL] LLM error (API Key fake): {result['error']}")
else:
    print(f"[OK] Rewrite advice received!")
    print(f"   Diagnosis: {result.get('diagnosis', '')[:100]}...")
    print(f"   Sentences: {len(result.get('sentences', []))}")
    print(f"   Overall advice: {result.get('overall_advice', '')[:100]}...")
