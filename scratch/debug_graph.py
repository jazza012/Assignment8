import networkx as nx

g = nx.DiGraph()
g.add_node("n:7", skill="planner", status="complete")
g.add_node("n:8", skill="coder", status="pending")
g.add_node("n:9", skill="critic", status="pending")
g.add_node("n:10", skill="formatter", status="pending")

# n:7 completed, adding n:8, n:9, n:10.
# Pass 2 of extend_from("n:7") adds:
g.add_edge("n:8", "n:9")
g.add_edge("n:9", "n:10")

print("Before extend_from('n:8'):")
print("Edges:", list(g.edges()))
print("n:8 successors:", list(g.successors("n:8")))

# Simulate extend_from("n:8"):
src_nid = "n:8"
internal_successors = ["sandbox_executor"]

last_nid = src_nid
internal_added = []
# Simulate add_node inside extend_from:
# For child_skill = "sandbox_executor", inputs=[last_nid]
new_id = "n:11"
g.add_node(new_id, skill="sandbox_executor", status="pending")
g.add_edge(last_nid, new_id)  # adds n:8 -> n:11

internal_added.append(new_id)
last_nid = new_id

if internal_added and last_nid != src_nid:
    downstream = [c for c in g.successors(src_nid) if c not in internal_added]
    print("Downstream of n:8:", downstream)
    for child_nid in downstream:
        g.remove_edge(src_nid, child_nid)
        g.add_edge(last_nid, child_nid)

print("\nAfter extend_from('n:8'):")
print("Edges:", list(g.edges()))
