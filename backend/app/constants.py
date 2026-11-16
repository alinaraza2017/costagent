"""Shared business rules, security catalog, and deployment checklist definitions."""

CATEGORIES = [
    "Personnel",
    "Equipment",
    "Software",
    "Software & Tools",
    "AI / Cloud API",
    "Travel",
    "Marketing",
    "Infrastructure",
    "Hardware & Infrastructure",
    "Operations",
    "Testing",
    "Documentation & Handover",
    "Other",
]

CURRENCIES = ["PKR", "USD", "EUR", "GBP", "AED", "SAR", "INR"]

PROJECT_STATUSES = ["planning", "active", "on_hold", "completed"]

DUPLICATE_POLICY = (
    "A row is a duplicate when the expense name, category, expense date, estimated cost, "
    "and actual cost match another row in the same file or an existing expense on this project. "
    "The first valid copy is kept. Later duplicates are skipped and are not saved again. "
    "Cancelling a preview writes nothing. Confirming an import saves only the valid, non-duplicate rows "
    "in one database transaction."
)

SAMPLE_TEMPLATE_NOTE = (
    "Required columns: expense_name, category, estimated_cost, actual_cost, expense_date. "
    "Optional columns: description, vendor. Dates must use YYYY-MM-DD. Costs must be zero or positive plain numbers."
)

MIN_ANOMALY_PEERS = 4

DISCLAIMER = (
    "These insights are generated to support review. They may be incomplete or inaccurate and "
    "should be checked before any financial decision. A statistical flag is not evidence of fraud, "
    "waste, or error."
)

THREATS = [
    {
        "id": "idor",
        "name": "Broken access control / IDOR",
        "scenario": "An authenticated user changes a project, expense, import, or report identifier and requests another person's records.",
        "impact": "Private project names, budgets, vendors, and cost records could be read, changed, deleted, or exported.",
        "mitigation": "Every project-specific query loads the record and compares its owner with the authenticated user on the server. Missing authentication returns 401. A matching record owned by someone else returns 403 without the record body. List and analytics queries are filtered by owner id.",
        "status": "implemented",
        "test_case": "backend/tests/test_security.py::test_unauthorized_project_access",
        "future_improvement": "Return the same 404 response for missing and unowned records so identifiers are harder to enumerate, and add object-level authorization tests to continuous integration on every new route.",
    },
    {
        "id": "malicious-upload",
        "name": "Malicious or malformed file uploads",
        "scenario": "A user uploads a renamed executable, a macro workbook, a broken CSV, or a spreadsheet that contains formulas instead of plain values.",
        "impact": "Unsafe parsing could store corrupted costs, exhaust memory, or, in a poorly designed parser, execute active content.",
        "mitigation": "Only .csv and .xlsx extensions are accepted, and the file content must match that type. Macro-enabled workbooks are rejected. Workbooks are opened with formula evaluation disabled, and formula cells are rejected. A 5 MB size limit and a 500-row limit apply. Invalid rows are reported and are not inserted.",
        "status": "implemented",
        "test_case": "backend/tests/test_security.py::test_reject_unsupported_extension",
        "future_improvement": "Scan uploads in an isolated worker with a stricter content sandbox and retain the original file only in short-lived storage when an investigation requires it.",
    },
    {
        "id": "sql-injection",
        "name": "SQL injection",
        "scenario": "A project name or expense description includes SQL metacharacters in an attempt to change the query that reads or deletes records.",
        "impact": "A successful injection could expose or destroy cost data.",
        "mitigation": "Database access goes through SQLAlchemy ORM queries and bound parameters. User text is stored as data and is not concatenated into SQL.",
        "status": "implemented",
        "test_case": "backend/tests/test_security.py::test_sql_injection_stored_as_data",
        "future_improvement": "Give the application database user only the privileges it needs in production and add query logging that records statement templates rather than bound values.",
    },
    {
        "id": "xss",
        "name": "Cross-site scripting (XSS)",
        "scenario": "An expense description contains HTML or script text. Another page displays that description and the browser executes it.",
        "impact": "Script in the page could read the access token from session storage or act as the signed-in user.",
        "mitigation": "The API returns JSON with nosniff and a restrictive content security policy. The React interface inserts expense text as text, not as HTML. PDF text is XML-escaped before it is drawn. CSV text that begins with a formula prefix is neutralized.",
        "status": "implemented",
        "test_case": "backend/tests/test_security.py::test_xss_text_returned_as_json",
        "future_improvement": "Move the access token to an HttpOnly cookie with CSRF protection, and serve the built frontend with its own content security policy.",
    },
    {
        "id": "brute-force",
        "name": "Brute-force login attempts",
        "scenario": "A script repeatedly submits passwords for one email address or many addresses.",
        "impact": "A weak password could be guessed, or the login endpoint could be kept busy.",
        "mitigation": "Passwords are hashed with bcrypt. Login and registration are rate limited per client address. Failed login returns the same message whether the email exists or the password is wrong.",
        "status": "implemented",
        "test_case": "backend/tests/test_security.py::test_login_rate_limit_and_health",
        "future_improvement": "Add multi-factor authentication, breached-password screening, and a temporary lockout that still uses a generic client message.",
    },
    {
        "id": "dos",
        "name": "Denial of service through excessive requests or oversized uploads",
        "scenario": "A client sends a very large request body, a spreadsheet with too many rows, or a burst of requests to a sensitive endpoint.",
        "impact": "The API could become slow for everyone, or a preview could consume excessive memory.",
        "mitigation": "JSON requests are limited to 1 MB and uploads to 5 MB. Imports stop at 500 data rows. Login, registration, imports, analysis, and report downloads have application rate limits. The health endpoint stays available so a login limit does not by itself take the process down.",
        "status": "implemented",
        "test_case": "backend/tests/test_security.py::test_login_rate_limit_and_health",
        "future_improvement": "Enforce connection and request limits again at a reverse proxy, and run file parsing in a separate worker with a hard memory ceiling.",
    },
    {
        "id": "secrets",
        "name": "Exposure of secrets or sensitive financial data",
        "scenario": "An API key, password hash, access token, or detailed financial record is written into a log, an error response, or the frontend bundle.",
        "impact": "Exposed credentials allow account access. Exposed cost records disclose private project information.",
        "mitigation": "Secrets are read from environment variables. The real .env file is gitignored and .env.example contains placeholders. Responses omit password hashes. Logs pass through a redaction filter, and audit records store event types and resource ids rather than amounts, passwords, or tokens. Unhandled errors return a generic message.",
        "status": "implemented",
        "test_case": "backend/tests/test_auth.py::test_profile_omits_password_hash",
        "future_improvement": "Store production secrets in a managed secret store, encrypt database backups, and restrict database network access to the application host.",
    },
    {
        "id": "prompt-injection",
        "name": "AI prompt injection through imported text",
        "scenario": "An imported description tells the model to ignore its instructions, declare fraud, or reveal secrets.",
        "impact": "A model that followed that text could mislead a reviewer or attempt to obtain data the feature should not send.",
        "mitigation": "Anomaly flags are computed with a documented statistical rule and are not taken from model output. Descriptions are not sent to the model. Names sent as untrusted data are length-limited. The model has no database, file, or tool access. Its prose is validated against a schema, and any timeout, rate limit, or malformed response falls back to rule-based text. The interface labels hypotheses and shows a review disclaimer.",
        "status": "implemented",
        "test_case": "backend/tests/test_security.py::test_prompt_injection_does_not_steer_analysis",
        "future_improvement": "Run any external model in a separate account with no production credentials, and keep a human approval step before narrative text is copied into an official report.",
    },
]

CHECKLIST_ITEMS = [
    {
        "key": "auth-hashing",
        "title": "Authentication and password hashing",
        "guidance": "Confirm bcrypt or Argon2 is still used, the work factor is appropriate for production, and demo accounts are removed or rotated.",
    },
    {
        "key": "authorization",
        "title": "Authorization and project ownership",
        "guidance": "Review every new route that accepts an identifier and confirm the server checks the owner. Do not rely on hidden frontend buttons.",
    },
    {
        "key": "input-validation",
        "title": "Input validation",
        "guidance": "Confirm request schemas reject unexpected types, oversized strings, negative costs, and invalid dates.",
    },
    {
        "key": "file-uploads",
        "title": "File upload validation",
        "guidance": "Confirm extension checks, content checks, size limits, row limits, and formula rejection still match the deployment environment.",
    },
    {
        "key": "sql-injection",
        "title": "SQL injection protection",
        "guidance": "Confirm queries stay in the ORM or use bound parameters, including any new report or search feature.",
    },
    {
        "key": "xss",
        "title": "XSS prevention",
        "guidance": "Confirm the interface does not inject HTML from expense text and that response headers remain in place.",
    },
    {
        "key": "rate-limiting",
        "title": "Rate limiting",
        "guidance": "Set production limits for login and expensive routes, and repeat them at the reverse proxy.",
    },
    {
        "key": "secrets",
        "title": "Secret management",
        "guidance": "Load a unique signing secret and any model key from the environment or a secret manager. Confirm they are not in the image, frontend, or logs.",
    },
    {
        "key": "cors",
        "title": "CORS configuration",
        "guidance": "Allow only the real frontend origin. Do not use a wildcard origin in production.",
    },
    {
        "key": "https",
        "title": "HTTPS",
        "guidance": "Terminate TLS at the proxy or platform. Redirect HTTP to HTTPS and set a strict transport security header there.",
    },
    {
        "key": "errors",
        "title": "Error handling",
        "guidance": "Confirm clients receive safe messages and that stack traces are visible only in protected server logs.",
    },
    {
        "key": "logging",
        "title": "Logging and privacy",
        "guidance": "Confirm logs and audit records still exclude passwords, tokens, API keys, and cost amounts.",
    },
    {
        "key": "dependencies",
        "title": "Dependency vulnerabilities",
        "guidance": "Run the documented pip and npm audit process and update pinned versions that have a fixed advisory.",
    },
    {
        "key": "backup",
        "title": "Database backup and recovery",
        "guidance": "Test a backup and a restore of the production database. Do not keep the only copy on the application disk.",
    },
    {
        "key": "db-permissions",
        "title": "Production database permissions",
        "guidance": "Use a dedicated database account that can access only the application schema, and restrict which hosts can connect.",
    },
    {
        "key": "ai",
        "title": "Secure AI API integration",
        "guidance": "If a model key is set, confirm the key is server-side, timeouts are set, and reports do not silently send data to the provider.",
    },
    {
        "key": "reports",
        "title": "Report download authorization",
        "guidance": "Confirm PDF and CSV downloads repeat the project ownership check and that filenames are generated by the server.",
    },
    {
        "key": "security-testing",
        "title": "Security testing",
        "guidance": "Re-run the automated security tests against the release build and review the written results before go-live.",
    },
    {
        "key": "debug",
        "title": "Debug mode disabled in production",
        "guidance": "Set DEBUG to false, disable interactive tracebacks, and do not expose an open debug console.",
    },
]
