# CostWise AI

CostWise AI is a local web application for reviewing fictional project costs. You can register, keep projects and cost records, import CSV or Excel files, compare estimated and actual amounts, read rule-based cost insights, and download PDF or CSV reports. The API checks that each user can reach only their own projects.

This repository was built as a university lab project. It has not been deployed to a public host.

## What you need

- Windows 10 or 11
- Python 3.11
- Node.js 20 or newer (this project was checked with Node 24)
- PowerShell

Optional: Docker Desktop, if you want to run the compose file.

## Project layout

- `backend/` FastAPI application, SQLite database, and pytest suite
- `frontend/` React, TypeScript, and Vite interface
- `samples/cost_import_template.csv` fictional import file
- `docs/SECURITY_TEST_REPORT.md` results from the automated security tests
- `.env.example` placeholders only

## Configure the environment

From the project root in PowerShell:

```powershell
Copy-Item .env.example .env
```

Open `.env` and replace `SECRET_KEY` with a long random string. Leave `LLM_API_KEY` empty to use the local rule-based analysis. Do not commit `.env`.

SQLite is the local database. The file is created at `backend/data/costwise.db`. To use PostgreSQL later, install a PostgreSQL driver and set:

```text
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/costwise
```

The SQLAlchemy models stay the same. Do not use a temporary disk for production financial records.

## Install and start the backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m app.seed
uvicorn app.main:app --reload --port 8000
```

If PowerShell blocks the virtual environment script, run this once for your user and then activate again:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

The seed command creates one fictional account if it does not already exist:

- Email: `demo@costwise.local`
- Password: `DemoPass123!`

Use that account only on your own machine. Create a normal account from the registration page when you want a separate user.

API documentation is at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

Health check: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health).

## Install and start the frontend

Open a second PowerShell window:

```powershell
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). Vite proxies `/api` to the backend, so the browser talks to the frontend origin during local development.

## How to try the main workflows

1. Sign in with the demo account, or register a new one.
2. Open Projects and create a project. The default currency is PKR. You can choose another currency on the project form. That currency is then used for the project's amounts, charts, and reports.
3. Open the project and add a cost record. Variance is actual minus estimated. Percentage variance is `((actual - estimated) / estimated) x 100`. If the estimate is zero, the percentage is shown as N/A.
4. Open Import data, download the sample CSV, upload it, review the preview, and confirm. Cancel leaves the database unchanged. Duplicate rows, negative costs, bad dates, and spreadsheet formulas are rejected.
5. Open the Dashboard or Cost comparison. The charts read saved records and change when you change the project, category, or date filters.
6. Open PERT analysis, choose a project, and review the expected cost. Records that only have a single estimate can receive a suggested optimistic, most likely, and pessimistic value. You can also type those three costs while adding or editing a record.
7. Open Compare projects and choose two projects. The page shows budget, estimated cost, actual cost, variance, PERT, and a category breakdown.
8. Open AI insights, choose a project, and run the analysis. Without an API key the page is labeled as rule-based. Unusual amounts use a leave-one-out Tukey fence and require at least four other expenses in the same category. The demo network project includes one large equipment cost so a flag is visible. A flag is not a fraud finding.
9. Open Reports and use Export PDF or Export CSV. PDF findings are rule-based even if a model key is set, so generating a PDF does not send project data to an external API.
10. Open Security Center for the threat table and the deployment checklist. Checklist boxes stay empty until you mark them yourself.

## Tests

Backend, from `backend` with the virtual environment active:

```powershell
pytest -q
```

The suite uses its own SQLite file, bcrypt cost 4, and fictional accounts. It does not use `backend/data/costwise.db`.

Frontend, from `frontend`:

```powershell
npm test
```

The latest backend run on 26 October 2026 was **39 passed, 0 failed**. The frontend suite was **5 passed, 0 failed**. Details, including the three required security demonstrations, are in [docs/SECURITY_TEST_REPORT.md](docs/SECURITY_TEST_REPORT.md).

While both servers are running, from the `backend` directory, you can repeat a live check that does not print the access token:

```powershell
.\.venv\Scripts\python.exe scripts\verify_demo.py
```

## Calculations

The backend is the source of the numbers.

- Variance = actual cost - estimated cost
- Percentage variance = `((actual - estimated) / estimated) x 100`
- If the estimated total is zero, the percentage is null and the interface shows N/A
- A positive variance means the actual cost exceeded the estimate
- A negative variance means the actual cost was below the estimate
- Zero means the actual cost matched the estimate
- Project and dashboard percentages use the summed estimated and actual totals. They are not an average of the individual percentages
- PERT expected cost = `(optimistic + 4 x most likely + pessimistic) / 6`
- PERT standard deviation for one activity = `(pessimistic - optimistic) / 6`
- Project standard deviation is the square root of the sum of those activity variances. The budget chance uses a normal curve around the expected cost. It is a planning aid, not a guarantee
- Compare projects subtracts the first project's amounts from the second when both use the same currency. Different currencies are shown separately and are not subtracted

## Import rules

Accepted files are `.csv` and `.xlsx` only. The content is checked as well as the extension. The size limit is 5 MB and the row limit is 500. Workbook macros are rejected. Formula cells are not evaluated.

A row is a duplicate when the expense name, category, date, estimated cost, and actual cost match another row in the same file or an expense already saved on the project. The first valid copy is kept. Later copies are reported and skipped.

Preview does not save expenses. Confirm saves the valid rows in one transaction. If confirmation fails, the transaction is rolled back.

CSV exports keep real numbers as numbers. Text that begins with `=`, `+`, `-`, or `@` is prefixed with an apostrophe so a spreadsheet does not treat it as a formula.

## Optional model API

Set these in `.env` only if you want an external narrative:

```text
LLM_API_KEY=your-key
LLM_API_BASE=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
LLM_TIMEOUT_SECONDS=20
```

The key stays on the server. The analysis request sends totals, category names, and short expense names. It does not send descriptions. The model has no database or file access. Its reply must match a fixed schema. Timeouts, rate limits, and malformed replies fall back to the rule-based text. If the key is empty, the app never calls the provider.

## Security controls in this codebase

- Passwords are hashed with bcrypt. Login failures use one message for an unknown email and a wrong password.
- Access tokens are signed JWTs from `SECRET_KEY`. Logout stores the token id until it expires.
- Private routes require the bearer token. Project, expense, import, chart, analysis, and report routes compare the owner on the server.
- Another user's existing project returns HTTP 403 without the project body. A missing project returns HTTP 404. A missing or invalid token returns HTTP 401.
- Requests are validated with Pydantic. Queries use SQLAlchemy.
- Login, registration, imports, analysis, and report downloads are rate limited.
- CORS allows only the origins in `CORS_ORIGINS`.
- API responses set `nosniff`, a frame denial, and a content security policy suitable for a JSON API.
- Unexpected errors return a generic message. Logs pass through a redaction filter, and audit records store event types and ids rather than passwords, tokens, or amounts.
- Authentication uses the Authorization header, not a cookie, so a browser will not attach the token on a cross-site request. A cookie-based design would also need CSRF protection.

The Security Center page separates these implemented controls from later production work such as HTTPS at a proxy, a managed secret store, and database backups.

## Dependency review

Versions are pinned in `backend/requirements.txt` and `frontend/package.json`. `package-lock.json` is created by `npm install`.

Before a shared deployment, review the current pins:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pip install pip-audit
.\.venv\Scripts\python.exe -m pip-audit -r requirements.txt
cd ..\frontend
npm audit
```

Update a pin when the advisory has a fixed release that still works with the rest of the stack. This README does not claim that a vulnerability scan found zero issues.

On 26 October 2026, `npm install` reported 14 vulnerabilities in the frontend tree (5 moderate, 7 high, 2 critical). They were left in place because `npm audit fix --force` can move packages off the pinned versions. Review `npm audit` before any shared deployment and upgrade only the packages that remain compatible.

## Docker

From the project root, after `.env` exists:

```powershell
docker compose up --build
```

The compose file publishes the API on port 8000 and the Vite dev server on port 5173. The SQLite file is stored in a Docker volume, not in a container layer that disappears on every start. This is a local demonstration setup, not a production deployment.

## Production notes

A suitable production layout is:

- The built frontend (`npm run build`) on a static host or Nginx
- This FastAPI app on a Python host behind HTTPS
- PostgreSQL with a persistent volume, a dedicated database user, and backups that have been restored in a test
- `SECRET_KEY` and `LLM_API_KEY` in the host's secret store
- `CORS_ORIGINS` set to the real frontend origin only
- `DEBUG=false`
- Rate limits repeated at the reverse proxy
- The deployment checklist in Security Center reviewed and marked by a person

No public deployment was performed for this project.

## Screenshots

Local page screenshots are in `docs/screenshots/`. They show sign-in, registration, the dashboard, projects, a project cost table, import, charts, rule-based insights, reports, the Security Center, settings, and the Swagger UI.
