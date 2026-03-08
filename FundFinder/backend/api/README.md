# FundFinder API

Read-only REST API for the FundFinder grants (scholarships) data. Built with NestJS and PostgreSQL. The Python scrapers and pipeline populate the database; this API only reads from the `grants` table.

## Prerequisites

- Node.js 18+
- PostgreSQL with the FundFinder `grants` table (created and populated by the Python pipeline)

### If `npm` or `node` is not found

Node.js (which includes npm) may not be installed or may not be on your `PATH` in this terminal.

1. **Check if Node is installed elsewhere:** Open a **new** terminal and run `node --version` and `npm --version`. If they work there, your shell profile (e.g. nvm in `~/.zshrc`) may not be loaded in the current terminal—try opening a new terminal and running the commands again from `FundFinder/backend/api`.

2. **Install Node.js** (pick one):
   - **Official installer:** [nodejs.org](https://nodejs.org) — download the LTS version and run the installer.
   - **Homebrew (macOS):** `brew install node`
   - **nvm (Node Version Manager):** Install nvm, then run `nvm install 18` and `nvm use 18`. Ensure your `~/.zshrc` (or `~/.bash_profile`) sources nvm so new terminals have `node` and `npm`.

After installing, open a new terminal and run `npm install` again from `FundFinder/backend/api`.

## Setup

1. Go to the API directory (from repo root: `FundFinder/backend/api`):

   ```bash
   cd FundFinder/backend/api
   ```

2. Install dependencies (requires Node.js 18+ and npm):

   ```bash
   npm install
   ```

3. Configure the database:

   Copy `.env.example` to `.env` and set `DATABASE_URL` to your PostgreSQL connection string:

   ```bash
   cp .env.example .env
   ```

   Example `.env`:

   ```
   DATABASE_URL=postgresql://user:password@localhost:5432/fundfinder
   ```

## Running the server

**Before running the API,** make sure the Python pipeline has already created and populated the `grants` table (e.g. run the scraper/pipeline from the project root so the database has grant data to serve).

- Development (watch mode):

  ```bash
  npm run start:dev
  ```

- Production build then run:

  ```bash
  npm run build
  npm run start:prod
  ```

The API listens on port 3000 by default (override with `PORT` in `.env`). Base path is `/api`.

## Example requests

List grants (first page, default sort):

```bash
curl "http://localhost:3000/api/grants?page=1&limit=20"
```

List with search and filters:

```bash
curl "http://localhost:3000/api/grants?q=מצוינות&source_name=reichman&source_name=huji&has_deadline=true&sort_by=deadline&order=asc"
```

Get filter options (source names and currencies):

```bash
curl "http://localhost:3000/api/grants/filters"
```

Get a single grant by ID:

```bash
curl "http://localhost:3000/api/grants/1"
```

Expect 404 for missing grant:

```bash
curl "http://localhost:3000/api/grants/999"
```

## API contract

See [docs/api_design_document.md](../../docs/api_design_document.md) for the full API design.

- `GET /api/grants` — Paginated list with `q`, `source_name` (repeatable), `has_deadline`, `sort_by`, `order`, `page`, `limit`. Returns `description_snippet` in list items.
- `GET /api/grants/filters` — Distinct `source_names` and `currencies`.
- `GET /api/grants/:id` — Full grant details including `description`. Returns 404 with JSON error body when not found.
