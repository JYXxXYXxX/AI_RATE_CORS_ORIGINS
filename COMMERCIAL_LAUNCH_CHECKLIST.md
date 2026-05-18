# Commercial Launch Checklist

This checklist is the gate for moving PataFix from internal testing to paid public use.

## P0: Must Pass Before Public Traffic

- [ ] Rotate every API key that has ever appeared in chat logs, scripts, screenshots, or git history.
- [ ] Keep all secrets in environment variables or the deployment secret manager.
- [ ] Run secret scanning before every release.
- [ ] Set `AI_RATE_SERVICE_ENV=prod`.
- [ ] Set `AI_RATE_COOKIE_SECURE=true` behind HTTPS.
- [ ] Set `AI_RATE_CORS_ORIGINS` to the exact production domain.
- [ ] Set `AI_RATE_ASYNC_QUEUE_BACKEND=celery`.
- [ ] Run an independent Celery worker service.
- [ ] Confirm Redis is reachable from both API and worker.
- [ ] Confirm `/health` returns database connected and writable storage.
- [ ] Confirm upload, analyze, report, rewrite, export, and original download all work on production.
- [ ] Learning from official reports must be opt-in only.
- [ ] Show a clear privacy notice before collecting official reports for learning.
- [ ] Keep user papers, official reports, and feedback files under the retention policy.
- [ ] Confirm account deletion removes or anonymizes linked user data.

## Security And Privacy

- [ ] Reject unsupported file types with magic-byte validation.
- [ ] Enforce `AI_RATE_MAX_UPLOAD_BYTES` in production.
- [ ] Add upload rate limits for anonymous and logged-in users.
- [ ] Add rewrite rate limits per user and per IP.
- [ ] Add admin endpoints only when `AI_RATE_ADMIN_TOKEN` is configured.
- [ ] Do not log paper text, report text, LLM prompts, API keys, cookies, or payment payload secrets.
- [ ] Store learning samples as anonymized feature records, not full papers.
- [ ] Add a documented data deletion workflow.

## Reliability

- [ ] Worker retries failed analysis tasks with bounded retry count.
- [ ] Stale processing tasks are recovered on startup.
- [ ] Failed tasks expose a user-readable reason.
- [ ] Long-running tasks expose progress.
- [ ] Export failures fall back safely without corrupting the original document.
- [ ] The original uploaded file remains downloadable unchanged.
- [ ] Database migrations are applied in a repeatable order.
- [ ] Backups are enabled for database and uploaded files.

## Document Fidelity

- [ ] DOCX export patches the original file instead of rebuilding a new document whenever possible.
- [ ] DOCX patch failures are visible to the user instead of silently producing a bad file.
- [ ] PDF preview is treated as visual preview, not editable source of truth.
- [ ] Tables, references, formulas, and headings are not changed by one-click rewrite.
- [ ] A sample set of real DOCX papers is exported and visually compared before release.

## Detection And Rewrite Quality

- [ ] Official uploaded reports override local risk colors and priority order.
- [ ] Unmatched official report fragments can be manually mapped by the user.
- [ ] Normal sections are hidden or folded by default.
- [ ] Rewrite output explains the exact risky words or sentence pattern.
- [ ] One-click rewrite only touches actionable high/medium-risk blocks.
- [ ] The UI labels estimated improvement as estimated, not official.
- [ ] A benchmark tracks official-report mapping accuracy, AIGC error, duplication error, rewrite acceptance, and export success.

## Payment And Operations

- [ ] Payment callback signature verification is enabled for real providers.
- [ ] Orders are idempotent and cannot double-credit a user.
- [ ] Admin dashboard can inspect users, orders, tasks, and failures.
- [ ] Monitoring covers request latency, task duration, worker failures, upload failures, LLM errors, and export errors.
- [ ] A rollback plan exists for each release.

