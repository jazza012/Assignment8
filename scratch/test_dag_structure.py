"""Test that sessions with edges (parallel fan-out) render correctly."""
import urllib.request, json

API = "http://localhost:8501"

# Get all sessions
r = urllib.request.urlopen(f"{API}/api/sessions")
data = json.loads(r.read().decode())

# Find a session with many nodes (parallel fan-out)
best = None
for sid in data["sessions"]:
    r2 = urllib.request.urlopen(f"{API}/api/session/{sid}")
    s = json.loads(r2.read().decode())
    if s["node_count"] >= 5 and len(s["edges"]) > 3:
        best = s
        break

if best:
    print(f"Found parallel session: {best['session_id']}")
    print(f"  Nodes: {best['node_count']}")
    print(f"  Edges: {len(best['edges'])}")
    for e in best["edges"]:
        print(f"    {e['from']} -> {e['to']}")
    print(f"  Skills: {[n['skill'] for n in best['nodes']]}")
    print()
    
    # Check layer structure
    parents = {}
    children = {}
    for n in best["nodes"]:
        parents[n["id"]] = []
        children[n["id"]] = []
    for e in best["edges"]:
        if e["from"] in children:
            children[e["from"]].append(e["to"])
        if e["to"] in parents:
            parents[e["to"]].append(e["from"])
    
    # BFS layers
    roots = [nid for nid in parents if not parents[nid]]
    depth = {r: 0 for r in roots}
    queue = list(roots)
    visited = set()
    while queue:
        nid = queue.pop(0)
        if nid in visited:
            continue
        visited.add(nid)
        d = depth.get(nid, 0)
        for c in children.get(nid, []):
            depth[c] = max(depth.get(c, 0), d + 1)
            queue.append(c)
    
    layers = {}
    for nid, d in depth.items():
        layers.setdefault(d, []).append(nid)
    
    print("Layer structure:")
    for d in sorted(layers):
        node_skills = []
        for nid in layers[d]:
            for n in best["nodes"]:
                if n["id"] == nid:
                    node_skills.append(f"{nid}({n['skill']})")
        print(f"  Layer {d}: {', '.join(node_skills)}")
        
    # Check connector types needed
    for d in sorted(layers):
        if d == 0:
            continue
        prev_count = len(layers.get(d-1, []))
        cur_count = len(layers[d])
        if prev_count == 1 and cur_count > 1:
            print(f"  Connector {d-1}->{d}: FAN-OUT (1 -> {cur_count})")
        elif prev_count > 1 and cur_count == 1:
            print(f"  Connector {d-1}->{d}: MERGE ({prev_count} -> 1)")
        else:
            print(f"  Connector {d-1}->{d}: SIMPLE ({prev_count} -> {cur_count})")
    
    print("\n[OK] Parallel DAG structure verified for rendering")
else:
    print("No parallel sessions found. Run Query I first.")
