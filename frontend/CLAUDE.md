# Frontend (SvelteKit)

## Stack

- SvelteKit 2 + Svelte 5 (Runes syntax: `$props()`, `$state()`, `$derived()`)
- Tailwind CSS 4 (Vite plugin, not PostCSS)
- TypeScript strict mode
- pnpm package manager
- chart.js for data visualization

## Commands

```bash
pnpm install          # install deps
pnpm dev              # dev server
pnpm build            # production build → build/
pnpm check            # svelte-check + TypeScript
```

## Project Structure

- `src/routes/` — SvelteKit file-based routing (+page.svelte, +page.server.ts, +layout.svelte)
- `src/lib/components/` — components organized by feature (ui/, icons/, navigation/, dashboard/, condition/, biometrics/, charts/)
- `src/lib/api.ts` — browser-side fetch client (relative `/api/*` paths, Nginx proxies)
- `src/lib/server/api.ts` — SSR fetch client (uses `INTERNAL_API_URL` env for Docker-internal calls)
- `src/lib/types/` — TypeScript type definitions
- `src/lib/stores/` — Svelte stores (`.svelte.ts` runes-based)

## API Communication

- Browser: `$lib/api.ts` → relative path → Nginx → Go API
- SSR (load functions): `$lib/server/api.ts` → `INTERNAL_API_URL` (http://api:8080) → Go API directly

## Adapter

Node.js adapter (`@sveltejs/adapter-node`), outputs to `build/`.
