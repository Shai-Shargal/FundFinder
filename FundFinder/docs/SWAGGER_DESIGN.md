# Swagger (OpenAPI) Integration Design Document

**Project:** FundFinder Backend API  
**Date:** March 2025  
**Status:** Design Only (No Implementation Yet)

---

## 1. Goal

### Why We Are Adding Swagger

- **Developer experience:** Allow developers to explore, understand, and test the API interactively via Swagger UI without writing custom scripts or using tools like Postman.
- **Documentation:** Keep API documentation in sync with the code. Swagger derives docs from DTOs and decorators, reducing manual maintenance and drift.
- **Onboarding:** New team members and external consumers can quickly grasp available endpoints, request/response shapes, and query parameters.
- **Interoperability:** OpenAPI is a standard format. Generated specs can be used for client SDK generation, mocking, or integration with API gateways.

### Problems It Solves

| Problem | Solution with Swagger |
|---------|------------------------|
| No central place to see all endpoints | Swagger UI lists all routes at `/docs` |
| Unclear query params for `GET /grants` | DTO decorators document `page`, `limit`, `q`, `source_name`, etc. |
| Unknown response shapes | Response schemas can be documented |
| Manual testing friction | "Try it out" in Swagger UI allows live requests |
| Outdated external docs | Docs live in code; changes require code updates |

---

## 2. Architecture

### How Swagger Integrates with NestJS

| Component | Purpose |
|-----------|---------|
| **SwaggerModule** | Nest's wrapper that wires the OpenAPI spec and serves Swagger UI. |
| **DocumentBuilder** | Configures the top-level OpenAPI document (title, version, description, servers, tags). |
| **Swagger decorators** | `@ApiTags()`, `@ApiOperation()`, `@ApiParam()`, `@ApiQuery()`, `@ApiResponse()` — add metadata to controllers and handlers. |
| **DTO integration** | `@nestjs/swagger` provides `@ApiProperty()` / `@ApiPropertyOptional()` for DTO fields. These plug into `class-validator` and `class-transformer` so schemas are inferred from existing decorators where possible. |

### Data Flow

```
main.ts
  └─> SwaggerModule.setup('/docs', app, document)
        └─> DocumentBuilder creates OpenAPI JSON
        └─> Nest scans controllers for Swagger decorators
        └─> DTOs with @ApiProperty() contribute to request/response schemas
        └─> Swagger UI served at /docs, fetches spec from same server
```

### NestJS-Specific Notes

- Nest uses `@nestjs/swagger`, which wraps `swagger-ui-express` (or similar) and generates the OpenAPI document by scanning route metadata and DTO properties.
- `ValidationPipe` and `class-validator` are already in use. Swagger decorators supplement these for documentation; they do not replace validation.
- The global prefix `api` means all routes are under `/api`. The Swagger doc will reflect this (e.g. `/api/grants`).

---

## 3. Implementation Plan

### Step 1: Install Dependencies

```bash
npm install @nestjs/swagger
```

No additional packages required; `@nestjs/swagger` brings in what it needs (e.g. `swagger-ui-express`).

### Step 2: Configure Swagger in `main.ts`

- Import `SwaggerModule` and `DocumentBuilder` from `@nestjs/swagger`.
- After `app.setGlobalPrefix('api')` (or after creating the app), build the OpenAPI document using `DocumentBuilder`.
- Call `SwaggerModule.setup('/docs', app, document)` to:
  - Expose Swagger UI at `http://localhost:<port>/docs`
  - Serve the OpenAPI JSON spec (Swagger UI fetches it automatically).
- Use `documentBuilder.setBasePath('/api')` so paths in the spec include the prefix.

### Step 3: Set Up the Swagger Document

Configure the document with:

- **Title:** e.g. `FundFinder API`
- **Description:** Short summary of the API (grants/scholarships discovery).
- **Version:** e.g. `0.1.0` (match `package.json`).
- **Base path:** `/api` (optional, depending on how NestJS generates paths).
- **Tags:** e.g. `Grants` — used to group endpoints in Swagger UI.

### Step 4: Expose Swagger UI Endpoint

- Swagger UI will be available at `GET /docs` (no `/api` prefix by convention, so `http://localhost:3000/docs`).
- The OpenAPI spec is typically served at a path like `/docs-json` (configurable in `SwaggerModule.setup`).

### Step 5: Add Decorators to DTOs and Controllers

| Location | Decorators to Add |
|----------|-------------------|
| **GetGrantsQueryDto** | `@ApiPropertyOptional()` on each field with `description`, `example`, and `enum` where applicable (e.g. `sort_by`, `order`). |
| **GrantsController** | `@ApiTags('Grants')`, `@ApiOperation({ summary: '...' })` on each handler, `@ApiQuery()` for complex query params if needed, `@ApiParam({ name: 'id' })` for `getById`, `@ApiResponse()` for success and error cases. |
| **Future DTOs** | Same pattern: `@ApiProperty()` for required fields, `@ApiPropertyOptional()` for optional ones. |

---

## 4. Folder Impact

### Files to Modify

| File | Changes |
|------|---------|
| **`package.json`** | Add `@nestjs/swagger` dependency (via `npm install`). |
| **`src/main.ts`** | Import `SwaggerModule`, `DocumentBuilder`; build document; call `SwaggerModule.setup('/docs', app, document)`. |
| **`src/grants/dto/get-grants-query.dto.ts`** | Add `@ApiPropertyOptional()` (and where relevant `@ApiProperty()`) to each property with descriptions and examples. |
| **`src/grants/grants.controller.ts`** | Add `@ApiTags('Grants')`, `@ApiOperation()` on each route, `@ApiParam()` for `:id`, `@ApiResponse()` for success (200) and errors (404). |

### Files Not Modified (Initial Pass)

- `grants.service.ts` — no changes (Swagger documents the API surface, not internal logic).
- `grants.module.ts` — no changes.
- `app.module.ts` — no changes (Swagger is configured in `main.ts`, not via a dynamic module in `AppModule` unless desired).
- Interface files — can remain as TypeScript interfaces; DTOs are the source of truth for request/response schema docs. If we add response DTOs later, those would get `@ApiProperty()`.

---

## 5. Example API Documentation

### How the Grants Endpoints Will Appear in Swagger UI

#### `GET /api/grants`

- **Summary:** List grants with optional filters and pagination  
- **Query parameters:**
  - `page` (optional, number, default: 1) — Page number  
  - `limit` (optional, number, default: 20, max 50) — Items per page  
  - `q` (optional, string) — Search in title, description, eligibility  
  - `source_name` (optional, array of strings) — Filter by source(s)  
  - `has_deadline` (optional, boolean) — Filter by presence of deadline  
  - `sort_by` (optional, enum: `deadline`, `created_at`, `updated_at`, `title`, default: `deadline`)  
  - `order` (optional, enum: `asc`, `desc`, default: `asc`)  
- **Responses:** 200 — Paginated list of grants with `items` and `pagination`

#### `GET /api/grants/filters`

- **Summary:** Get filter options (source names and currencies)  
- **Responses:** 200 — `{ source_names: string[], currencies: string[] }`

#### `GET /api/grants/{id}`

- **Summary:** Get a single grant by ID  
- **Path parameters:** `id` (required, integer)  
- **Responses:**  
  - 200 — Grant detail object  
  - 404 — `{ error: { code: 'NOT_FOUND', message: string } }`

---

## 6. Future Improvements

| Enhancement | Description |
|-------------|-------------|
| **Response schemas** | Define response DTOs with `@ApiProperty()` and reference them in `@ApiResponse({ schema: GrantDetailDto })` for full schema documentation. |
| **Authentication** | Add `@ApiBearerAuth()` or `@ApiBasicAuth()` and configure security schemes in `DocumentBuilder` for protected endpoints. |
| **Tags for modules** | Use `@ApiTags('Grants')`, `@ApiTags('Users')` etc. to group endpoints by domain. |
| **API descriptions** | Add `description` and `example` to `@ApiOperation()` and `@ApiProperty()` for richer docs. |
| **Versioning** | If API versioning is added (e.g. `/api/v1/grants`), reflect it in the Swagger document and tags. |
| **Exclude endpoints** | Use `exclude` in `SwaggerModule.setup` or `@ApiExcludeEndpoint()` to hide internal routes from the public spec. |

---

## Summary

Swagger will be integrated by:

1. Installing `@nestjs/swagger`.
2. Configuring `DocumentBuilder` and `SwaggerModule.setup('/docs', app, document)` in `main.ts`.
3. Annotating `GetGrantsQueryDto` and `GrantsController` with OpenAPI decorators.
4. Serving Swagger UI at `/docs` for interactive API exploration and testing.

No code has been written yet; this document is the design for implementation.
