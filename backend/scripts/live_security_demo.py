"""Live demonstration of the three required security tests against a running local API.

Run while the backend is on http://127.0.0.1:8000:
    python scripts/live_security_demo.py
Uses only fictional accounts. Waits about a minute before test 3 so the
earlier sign-ins do not count toward the login rate limit.
"""
import httpx
c=httpx.Client(base_url="http://127.0.0.1:8000",timeout=30)
def tok(e):
    c.post("/api/auth/register",json={"email":e,"full_name":e.split("@")[0].title(),"password":"TestPass123!"})
    return {"Authorization":"Bearer "+c.post("/api/auth/login",json={"email":e,"password":"TestPass123!"}).json()["access_token"]}
print("$ python live_security_demo.py   (fictional users alice2@example.com and bob2@example.com)\n")
a=tok("alice2@example.com"); b=tok("bob2@example.com")
pid=c.post("/api/projects",headers=a,json={"name":"Alice Private Project","description":"","start_date":"2026-01-01","budget":5000,"currency":"PKR","status":"active"}).json()["id"]
print("TEST 1  Invalid file upload")
r=c.post(f"/api/projects/{pid}/imports/preview",headers=a,files={"file":("payload.exe",b"MZ not a spreadsheet","application/octet-stream")}); print(f"  upload payload.exe            -> HTTP {r.status_code}  {r.json()['detail']}")
r=c.post(f"/api/projects/{pid}/imports/preview",headers=a,files={"file":("costs.csv",b"MZ\x90\x00\x03\x00\x00\x00\x04\x00","text/csv")}); print(f"  upload EXE renamed to .csv    -> HTTP {r.status_code}  {r.json()['detail']}")
n=c.get(f"/api/projects/{pid}/expenses",headers=a).json()["total"]; print(f"  expenses stored after uploads -> {n}\n")
print("TEST 2  Unauthorized project access (Bob tries Alice's project)")
for m,path in [("GET",f"/api/projects/{pid}"),("GET",f"/api/projects/{pid}/expenses"),("GET",f"/api/projects/{pid}/reports/pdf"),("DELETE",f"/api/projects/{pid}")]:
    r=c.request(m,path,headers=b); print(f"  {m:6} {path:32} -> HTTP {r.status_code}  leaked name: {'Alice Private Project' in r.text}")
r=c.get(f"/api/projects/{pid}"); print(f"  GET    {'/api/projects/'+str(pid)+' (no token)':32} -> HTTP {r.status_code}\n")
import time; time.sleep(62)
print("TEST 3  Excessive requests (rapid wrong logins, limit 5/minute)")
for i in range(1,8):
    r=c.post("/api/auth/login",json={"email":"nobody@example.com","password":"wrong"}); print(f"  login attempt {i} -> HTTP {r.status_code}  {r.json()['detail']}")
print(f"  /api/health after limit -> HTTP {c.get('/api/health').status_code}")
