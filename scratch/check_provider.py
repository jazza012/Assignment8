import sqlite3

conn = sqlite3.connect('gateway/gateway_v8.db')
c = conn.cursor()
c.execute("SELECT id, ts, provider, model, latency_ms, status, error, call_role, router_decision FROM calls ORDER BY id DESC LIMIT 5;")
for row in c.fetchall():
    print(row)
conn.close()
