import sqlite3
import json

conn = sqlite3.connect('gateway/gateway_v8.db')
c = conn.cursor()

# Get the last 3 calls where agent='researcher'
c.execute("SELECT provider, model, latency_ms, status, error, response_body FROM calls WHERE agent='researcher' ORDER BY id DESC LIMIT 3;")
calls = c.fetchall()

for i, call in enumerate(calls):
    provider, model, latency, status, error, resp_body_raw = call
    print(f"\n================ CALL {i+1} ================")
    print(f"Provider: {provider} | Model: {model} | Latency: {latency}ms | Status: {status}")
    if error:
        print(f"Error: {error}")
    
    if resp_body_raw:
        try:
            resp_body = json.loads(resp_body_raw)
            # Print the tool calls or reply text
            choices = resp_body.get("choices", [])
            if choices:
                msg = choices[0].get("message", {})
                print("Text response:")
                print(msg.get("content", ""))
                tool_calls = msg.get("tool_calls", [])
                if tool_calls:
                    print("Tool Calls:")
                    for tc in tool_calls:
                        print(f"  ID: {tc.get('id')} | Name: {tc.get('function', {}).get('name')} | Args: {tc.get('function', {}).get('arguments')}")
        except Exception as e:
            print("Error parsing response body:", e)
conn.close()
