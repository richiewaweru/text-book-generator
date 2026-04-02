# Phase P6 Railway Backend Deployment

**Date:** 2026-04-02  
**Classification:** major  
**Subsystems:** Railway deployment config, backend container runtime, production operator workflow

## Progress

- [x] Confirmed the current repo still needed Railway-specific Docker/runtime alignment
- [x] Established a validation baseline before changes
- [x] Expanded `railway.toml` into a complete backend deployment contract
- [x] Updated the backend container to honor Railway's dynamic `PORT`
- [x] Added a backend smoke-test helper and `Makefile` smoke targets
- [x] Updated env/docs for Railway backend deployment and frontend follow-on wiring
- [x] Ran final validation
- [x] Recorded local Railway-compatibility smoke evidence

## Summary

This phase finishes the repo-side work needed to deploy the backend to Railway reliably. The backend image now binds to Railway's injected `PORT`, `railway.toml` defines the Docker build and readiness contract, a smoke-test script checks the deployed backend's core surface, and the repo docs now explain the exact Railway variables and post-deploy workflow. The frontend remains a follow-on deployment, with this phase documenting the correct `PUBLIC_API_URL` and `VITE_API_TARGET` wiring rather than implementing Vercel deployment itself.

## Railway Backend Variables

Set these on the Railway backend service:

| Variable | Required | Notes |
| --- | --- | --- |
| `APP_ENV=production` | yes | canonical production environment flag |
| `DATABASE_URL` | yes | use `postgresql+asyncpg://...`, not Railway's default `postgres://` |
| `JWT_SECRET_KEY` | yes | generate a real secret; placeholder values are rejected |
| `GOOGLE_CLIENT_ID` | yes | required by backend auth validation in production |
| `ANTHROPIC_API_KEY` | yes | required for generation |
| `FRONTEND_ORIGIN` | yes | exact future frontend origin, including `https://` |
| `LESSON_BUILDER_PUBLIC_URL` | yes | exact future public frontend URL |
| `JSON_LOGS=true` | yes | recommended for Railway log explorer |
| `LOG_LEVEL=INFO` | yes | raise only for active debugging |
| `LECTIO_CONTRACTS_DIR=/app/backend/contracts` | recommended | matches the image layout |
| `GENERATION_MAX_CONCURRENT_PER_USER` and `PIPELINE_*` runtime vars | recommended | keep explicit production policy values |

For Railway Postgres, create `DATABASE_URL` from plugin variables:

```text
postgresql+asyncpg://${PGUSER}:${PGPASSWORD}@${PGHOST}:${PGPORT}/${PGDATABASE}
```

## Frontend Follow-on

- When the frontend is deployed later, point it at the Railway backend with:
  - `PUBLIC_API_URL=https://your-backend.up.railway.app`
  - `VITE_API_TARGET=https://your-backend.up.railway.app`
- Then update Railway's `FRONTEND_ORIGIN` and `LESSON_BUILDER_PUBLIC_URL` to that exact frontend URL.
- Add the same frontend origin to Google OAuth authorized JavaScript origins.

## Deployment Checklist

1. Create a Railway project from the GitHub repo.
2. Add a PostgreSQL plugin.
3. Set the backend variables listed above.
4. Deploy from `main`.
5. Confirm Railway health check uses `/health/ready`.
6. Run:
   - `python scripts/smoke_test.py https://your-backend.up.railway.app`
7. Verify Google auth and one end-to-end generation manually after the frontend is connected.

## Common Failure Modes

- Build succeeds but app never becomes healthy:
  - verify Railway is using the repo-root [railway.toml](/C:/Projects/Textbook%20agent/railway.toml)
  - verify `PORT` is not hardcoded elsewhere
- App crashes on startup with config validation:
  - replace placeholder `JWT_SECRET_KEY`
  - ensure `APP_ENV=production`
  - ensure `FRONTEND_ORIGIN` and `LESSON_BUILDER_PUBLIC_URL` are not localhost values
- DB connection errors:
  - ensure `DATABASE_URL` uses `postgresql+asyncpg://`
- CORS/login failures after frontend hookup:
  - ensure the frontend origin exactly matches Railway backend `FRONTEND_ORIGIN`
  - update Google OAuth origins to the final frontend URL

## Validation Evidence

Baseline and final repo validation:

- `python tools/agent/check_architecture.py --format text`
- `python tools/agent/validate_repo.py --scope all`
- Focused smoke helper coverage: `cd backend && uv run pytest tests/test_smoke_test_script.py tests/core/health/test_health_routes.py tests/core/test_app.py tests/core/test_logging.py -q`

Observed results:

- Architecture check passed
- Full repo validation passed
- Backend pytest passed as part of repo validation: `229 passed`
- Focused smoke-helper validation passed: `21 passed`

## Local Railway-Compatibility Smoke Evidence

Existing local Docker stack:

- `GET http://localhost:8000/health` returned `200`
- `GET http://localhost:8000/health/ready` returned `status = "ok"`
- `python scripts/smoke_test.py http://localhost:8000` passed

Railway-style dynamic port check:

- Rebuilt the backend image from the updated [backend/Dockerfile](/C:/Projects/Textbook%20agent/backend/Dockerfile)
- Started the backend image with:
  - `PORT=8010`
  - `APP_ENV=production`
  - secure `JWT_SECRET_KEY`
  - production-style `FRONTEND_ORIGIN` and `LESSON_BUILDER_PUBLIC_URL`
  - `DATABASE_URL=postgresql+asyncpg://textbook:textbook@db:5432/textbook_agent`
- `GET http://localhost:8010/health/ready` returned `200` with `status = "ok"`
- `python scripts/smoke_test.py http://localhost:8010` passed

## Notes

- The first non-default-port probe surfaced a stale cached backend image that still used the pre-phase hardcoded `--port 8000` command. Rebuilding the backend image picked up the new dynamic `PORT` contract and resolved the issue.
- Railway deployment itself was not executed from this workstation; the repo-side config, runtime proof, and operator procedure are ready for dashboard deployment.
