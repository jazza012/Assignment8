"""Find a clean parallel fan-out session (3 researchers)."""
import urllib.request, json

API = "http://localhost:8501"
r = urllib.request.urlopen(f"{API}/api/sessions")
data = json.loads(r.read().decode())

for sid in data["sessions"]:
    r2 = urllib.request.urlopen(f"{API}/api/session/{sid}")
    s = json.loads(r2.read().decode())
    skills = [n["skill"] for n in s["nodes"]]
    # Look for sessions with 5-10 nodes that have researcher fan-out
    if 5 <= s["node_count"] <= 10 and skills.count("researcher") >= 2:
        print(f"\nSession {sid} ({s['node_count']} nodes, {len(s['edges'])} edges)")
        print(f"  Query: {s['query'][:80]}")
        print(f"  Skills: {skills}")
        for e in s["edges"]:
            print(f"    {e['from']} -> {e['to']}")
        
        # Layer analysis
        parents = {}
        children = {}
        for n in s["nodes"]:
            parents[n["id"]] = []
            children[n["id"]] = []
        for e in s["edges"]:
            if e["from"] in children:
                children[e["from"]].append(e["to"])
            if e["to"] in parents:
                parents[e["to"]].append(e["from"])
        
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
        
        for d in sorted(layers):
            node_names = []
            for nid in layers[d]:
                for n in s["nodes"]:
                    if n["id"] == nid:
                        node_names.append(f"{n['skill']}")
            print(f"  L{d}: [{', '.join(node_names)}] (count={len(layers[d])})")
        
        # Check for fan-out
        for d in sorted(layers):
            if d == 0:
                continue
            pc = len(layers.get(d-1, []))
            cc = len(layers[d])
            if pc == 1 and cc > 1:
                print(f"  >>> FAN-OUT at L{d-1}->L{d}")
            elif pc > 1 and cc == 1:
                print(f"  >>> MERGE at L{d-1}->L{d}")
        break
