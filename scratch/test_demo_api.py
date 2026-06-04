"""Quick smoke-test for all demo API endpoints."""
import urllib.request, json

API = "http://localhost:8501"

# Test 1: sessions endpoint
r = urllib.request.urlopen(f"{API}/api/sessions")
data = json.loads(r.read().decode())
count = len(data["sessions"])
print(f"[OK] Sessions: {count} found")

# Test 2: load a specific session
sid = data["sessions"][-1]
r2 = urllib.request.urlopen(f"{API}/api/session/{sid}")
s = json.loads(r2.read().decode())
print(f"[OK] Session {sid}: {s['node_count']} nodes")
print(f"     Query: {s['query'][:60]}...")
print(f"     Edges: {len(s['edges'])}")
fa = s.get("final_answer", "") or ""
print(f"     Answer: {fa[:80]}..." if fa else "     (no final answer)")

# Test 3: load a node detail
if s["nodes"]:
    n = s["nodes"][0]
    r3 = urllib.request.urlopen(f"{API}/api/session/{sid}/node/{n['id']}")
    nd = json.loads(r3.read().decode())
    print(f"[OK] Node {n['id']}: skill={nd['skill']}, status={nd['status']}")

# Test 4: kill endpoint (nothing running)
req = urllib.request.Request(f"{API}/api/kill", method="POST", data=b"",
                             headers={"Content-Type": "application/json"})
r4 = urllib.request.urlopen(req)
kd = json.loads(r4.read().decode())
print(f"[OK] Kill endpoint: killed={kd['killed']} (expected false)")

# Test 5: main page loads
r5 = urllib.request.urlopen(f"{API}/")
html = r5.read().decode()
assert "DAG Agent" in html
assert "dag-canvas" in html
assert "killProcess" in html
assert "resumeQuery" in html
print(f"[OK] HTML page loads ({len(html)} bytes), all key elements present")

# Test 6: CSS loads
r6 = urllib.request.urlopen(f"{API}/style.css")
css = r6.read().decode()
assert "dag-connector" in css
assert "nodeEntrance" in css
assert "welcome-orb" in css
assert "btn-danger" in css
print(f"[OK] CSS loads ({len(css)} bytes), all new styles present")

print()
print("=== All 6 API smoke tests passed! ===")
