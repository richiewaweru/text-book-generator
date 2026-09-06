# Run 6 network and log summary (sanitized)

## Runtime boundary

- Backend listened on `127.0.0.1:8000` with the existing `--workers 1`
  contract; one serving listener was present.
- Frontend listened on `127.0.0.1:5173` and the browser remained in the
  in-app browser.
- Runtime settings were `GENERATION_PIPELINE_DEFAULT=component_lectio`,
  `GENERATION_MAX_CONCURRENT_PER_USER=1`, and `JSON_LOGS=true`.
- Health/readiness probes were successful after migration `20260906_0035`.

## Retired-surface probes

The pre-generation probes recorded sanitized `410` responses with code
`legacy_pipeline_retired` for `/api/v1/v3/*` and `/api/v1/legacy-units/*`.
The frontend legacy paths returned data-free retirement/404 responses. These
probes are evidence of the retirement contract, not execution fallback.

## Search results

The saved JSON backend log was searched case-insensitively for `/studio`,
`/api/v1/v3`, `legacy`, `fallback`, and `concurrent`.

- `/api/v1/v3`: matches were only the explicit pre-generation retirement
  probes, each HTTP 410.
- `legacy`: matches were only the explicit retirement probes, including the
  retired frontend path probe.
- `/studio`: matches were only the explicit route retirement probes, HTTP 404;
  no generation request used Studio.
- `fallback`: zero matches.
- `concurrent`: zero matches.
- During the generation flow, no request to Studio, a V3 API, or a legacy
  fallback was recorded.

The log also retained the canonical dashboard history request (GET /api/v1/generations → 200)
and Units readback (POST /api/v1/units/constructor/readback → 200). Provider transport details for
the six generation calls were reconciled from `llm_calls`: DeepSeek,
openai-compatible transport, `api.deepseek.com`, standard/fast lanes, six
successes, zero failures.

No concurrency marker, overlapping generation request, or second approval was
observed.
