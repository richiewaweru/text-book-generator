# Frontend

SvelteKit client for the Textbook Generation Agent.

## Commands

```bash
npm ci
npm run dev
npm run check
npm run build
npm run test
```

## Notes

- API calls use `PUBLIC_API_URL` when set, otherwise they fall back to same-origin paths.
- The textbook viewer fetches authenticated HTML by generation ID and mounts it with `iframe srcdoc`.
