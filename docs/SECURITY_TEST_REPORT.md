# CostWise AI security test report

Run date: 26 October 2026  
Environment: local Windows, Python 3.11.3, pytest 8.3.4  
Database: temporary SQLite file created by `backend/tests/conftest.py`  
Command:

```text
cd backend
.venv\Scripts\python.exe -m pytest -v --tb=line
```

Result: **48 passed, 0 failed** (re-run 17 November 2026, Python 3.13; the 48th test covers hosted PostgreSQL URLs). Earlier runs: 47 passed on 16 November. The 26 October run, after the Swagger UI was exempted from the JSON content security policy, completed with exit code 0. One deprecation warning came from Starlette's test client and is unrelated to the assertions.

Frontend, from `frontend`:

```text
npm test
```

Result: **6 passed, 0 failed** (Vitest 3.0.5). The tests cover percentage formatting, rejection of a negative cost, rejection of an end date before the start date, and the labeled sign-in form.

The isolated test database and the accounts created inside the tests are discarded with the temporary file. No real user data was used.

## Required demonstrations

### 1. Invalid file upload

| | |
| --- | --- |
| Test | `test_reject_unsupported_extension` |
| Objective | Reject a file whose extension is not `.csv` or `.xlsx`, and store nothing. |
| Test input | Upload `payload.exe` containing the bytes `MZ not a spreadsheet`. |
| Expected result | HTTP 400. Expense count stays 0. |
| Actual result | Passed. The API returned 400 and the expense table stayed empty. |
| Status | Pass |
| File | `backend/tests/test_security.py` |

| | |
| --- | --- |
| Test | `test_reject_malformed_csv` |
| Objective | Reject CSV content that cannot be parsed. |
| Test input | `broken.csv` with an unterminated quote. |
| Expected result | HTTP 400. No expense rows stored. |
| Actual result | Passed. |
| Status | Pass |
| File | `backend/tests/test_security.py` |

| | |
| --- | --- |
| Test | `test_reject_oversized_upload` |
| Objective | Reject an upload over the configured size limit inside the test environment. |
| Test input | The test lowers `max_upload_bytes` to 180 and uploads a larger CSV. The production default remains 5 MB (`5242880` bytes). |
| Expected result | HTTP 400 or 413. No expense rows stored. |
| Actual result | Passed. The request was rejected and nothing was stored. |
| Status | Pass |
| File | `backend/tests/test_security.py` |

| | |
| --- | --- |
| Test | `test_invalid_rows_are_not_stored` |
| Objective | Keep invalid cost rows out of the database. |
| Test input | A CSV row with a missing name, a negative cost, and an invalid date. |
| Expected result | Preview reports 0 accepted rows and 1 rejected row. Expense count stays 0. |
| Actual result | Passed. |
| Status | Pass |
| File | `backend/tests/test_security.py` |

Related import tests in `backend/tests/test_imports.py` also passed: formula text is not evaluated, Excel formula cells are rejected, duplicates are skipped, cancel writes nothing, and a tampered preview aborts without a partial save (`test_failed_confirm_does_not_leave_partial_rows`).

### 2. Unauthorized project access

| | |
| --- | --- |
| Test | `test_unauthorized_project_access` |
| Objective | Stop one signed-in user from reading, changing, deleting, or exporting another user's project. |
| Test input | User A creates "Private Fiber Build" and one expense. User B calls get, update, and delete on that project, plus expense edit, expense list, PDF export, CSV export, and AI analysis. |
| Expected result | Every call returns HTTP 403. Response bodies do not contain the project name, vendor, or budget. User A's project remains unchanged. |
| Actual result | Passed. All eight calls were forbidden, the private fields were absent from the responses, and the original project and expense remained. |
| Status | Pass |
| File | `backend/tests/test_security.py` |

| | |
| --- | --- |
| Test | `test_pdf_and_csv_export_authorization` |
| Objective | Allow the owner to download reports and deny another user. |
| Test input | Owner exports PDF and CSV. A second user requests the same project id. The CSV includes a vendor value that starts with `=HYPERLINK(...)`. |
| Expected result | Intruder receives HTTP 403 and no PDF bytes. Owner receives a PDF beginning with `%PDF` and a CSV where the formula-like vendor is prefixed with an apostrophe while the numeric cost stays numeric. |
| Actual result | Passed. |
| Status | Pass |
| File | `backend/tests/test_security.py` |

`test_users_only_see_their_projects` in `backend/tests/test_projects.py` also passed: each user receives only their own project list.

### 3. Excessive requests

| | |
| --- | --- |
| Test | `test_login_rate_limit_and_health` |
| Objective | Enforce the configured login limit without making the rest of the process unavailable. |
| Test input | `LOGIN_RATE_LIMIT` is `5/minute` in the test settings. The test sends 6 login requests for an unknown account, then calls `/api/health` and an unauthenticated project list. This is a local test client, not a flood of an external service. |
| Expected result | The first 5 logins return HTTP 401 with the generic message. The 6th returns HTTP 429. Health returns HTTP 200. The project list returns HTTP 401, showing that the login limit did not turn the whole API into 429. |
| Actual result | Passed. |
| Status | Pass |
| File | `backend/tests/test_security.py` |

## Additional tests that passed

| Test | Objective | Result |
| --- | --- | --- |
| `test_sql_injection_stored_as_data` | Store `Campus'; DROP TABLE expenses;--` as a project name and confirm expenses can still be queried. | Pass |
| `test_xss_text_returned_as_json` | Store script-like description text and return it as JSON with `nosniff`, not as an HTML page. | Pass |
| `test_invalid_project_dates_and_negative_cost` | Reject an end date before the start date and a negative cost. | Pass |
| `test_missing_invalid_and_expired_tokens` | Missing, malformed, and expired bearer tokens return HTTP 401. | Pass |
| `test_malformed_ai_response_falls_back` | A configured model that returns non-JSON falls back to rule-based text and the test key is not echoed. | Pass |
| `test_prompt_injection_does_not_steer_analysis` | An imported description that says to ignore instructions and reveal a key does not change the rule-based narrative. | Pass |
| `test_profile_omits_password_hash` | The profile response omits the password hash, and the stored hash is bcrypt. | Pass |
| `test_login_failure_is_generic` | Unknown email and wrong password return the same 401 message. | Pass |
| `test_checklist_starts_incomplete` | Deployment checklist items are unchecked until the signed-in user marks one. | Pass |
| `test_zero_estimate_percentage_is_null` | Percentage variance is null when the estimate is zero. | Pass |
| `test_project_summary_uses_aggregate_percentage` | Aggregate percentage is 2.97 for the 10/40 and 1000/1000 example, not the average of the row percentages. | Pass |
| `test_rule_based_anomaly_needs_peers_and_flags_outlier` | No anomaly is flagged for a tiny sample. A 900,000 actual is flagged among five closer equipment costs, and the reason says it is not evidence of fraud. | Pass |

## Repeat on the live deployment

On 17 November 2026 the three required demonstrations were repeated against the deployed site, https://costagent.vercel.app, with `backend/scripts/live_security_demo.py` (`COSTWISE_URL=https://costagent.vercel.app`). Fictional users `alice2@example.com` and `bob2@example.com` were used, and the test project was deleted afterwards.

| Test | Live result | Status |
| --- | --- | --- |
| Invalid file upload | `payload.exe` and an EXE renamed to `.csv` both returned HTTP 400; 0 expenses stored | Pass |
| Unauthorized project access | Read, expense list, PDF export and delete of another user's project returned HTTP 403 with no project name in the body; no token returned HTTP 401 | Pass |
| Excessive requests | Login attempts 1–5 returned HTTP 401, attempts 6–7 returned HTTP 429; `/api/health` stayed HTTP 200 | Pass |

The live site also sends HTTPS with `Strict-Transport-Security`, `X-Content-Type-Options: nosniff` and `X-Frame-Options: DENY`.

## What these runs do not prove

- On Vercel each serverless instance keeps its own rate-limit counter, so the login limit is weaker against an attack spread over many instances. Shared rate-limit storage remains future work.
- Database backups and their restore were not exercised. They remain an unchecked deployment-checklist item.
- The oversized-upload test uses a lowered limit so the suite stays small. The same size check enforces the 5 MB default outside tests.
- Frontend component tests passed separately: 6 passed, 0 failed. They do not replace the API security tests above.
