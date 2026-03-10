import { Injectable } from '@nestjs/common';
import { DatabaseService } from '../database/database.service';
import { GetGrantsQueryDto } from './dto/get-grants-query.dto';
import { FilterOptions } from './interfaces/filter-options.interface';
import { GrantDetail } from './interfaces/grant-detail.interface';
import { GrantListItem } from './interfaces/grant-list-item.interface';
import { ListResponse } from './interfaces/list-response.interface';

const SORT_BY_WHITELIST = ['deadline', 'created_at', 'updated_at', 'title'] as const;
const ORDER_WHITELIST = ['asc', 'desc'] as const;
const SNIPPET_LENGTH = 200;

interface GrantRow {
  id: number;
  title: string;
  description_snippet?: string;
  description?: string | null;
  source_url: string;
  source_name: string;
  deadline: string | null;
  deadline_text: string | null;
  amount: string | null;
  currency: string | null;
  eligibility: string | null;
  fetched_at: string;
  extra: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

@Injectable()
export class GrantsService {
  constructor(private readonly db: DatabaseService) {}

  async list(query: GetGrantsQueryDto): Promise<ListResponse> {
    const page = query.page ?? 1;
    const limit = query.limit ?? 20;
    const sortBy = SORT_BY_WHITELIST.includes(query.sort_by as (typeof SORT_BY_WHITELIST)[number])
      ? query.sort_by!
      : 'deadline';
    const order = ORDER_WHITELIST.includes(query.order!) ? query.order! : 'asc';
    const sourceNames = Array.isArray(query.source_name)
      ? query.source_name.filter(Boolean)
      : query.source_name
        ? [query.source_name]
        : [];

    const conditions: string[] = [];
    const params: unknown[] = [];
    let paramIndex = 1;

    if (query.q?.trim()) {
      conditions.push(`(title ILIKE $${paramIndex} OR description ILIKE $${paramIndex} OR eligibility ILIKE $${paramIndex})`);
      params.push(`%${query.q.trim()}%`);
      paramIndex++;
    }
    if (sourceNames.length > 0) {
      conditions.push(`source_name = ANY($${paramIndex})`);
      params.push(sourceNames);
      paramIndex++;
    }
    if (query.has_deadline === true) {
      conditions.push('deadline IS NOT NULL');
    } else if (query.has_deadline === false) {
      conditions.push('deadline IS NULL');
    }

    const whereClause = conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : '';
    const countSql = `SELECT COUNT(*)::int AS total FROM grants ${whereClause}`;
    const countResult = await this.db.query<{ total: number }>(countSql, params);
    const totalItems = countResult.rows[0]?.total ?? 0;
    const totalPages = Math.ceil(totalItems / limit) || 1;
    const offset = (page - 1) * limit;

    const nullsClause = sortBy === 'deadline' && order === 'asc' ? ' NULLS LAST' : '';
    const orderClause = `ORDER BY ${sortBy} ${order.toUpperCase()}${nullsClause}`;
    const listParams = [...params, limit, offset];
    const listSql = `
      SELECT
        id, title,
        LEFT(description::text, ${SNIPPET_LENGTH}) AS description_snippet,
        source_url, source_name, deadline, deadline_text, amount, currency, eligibility,
        fetched_at, extra, created_at, updated_at
      FROM grants
      ${whereClause}
      ${orderClause}
      LIMIT $${paramIndex} OFFSET $${paramIndex + 1}
    `;
    const listResult = await this.db.query<GrantRow>(listSql, listParams);
    const items: GrantListItem[] = listResult.rows.map((row) => ({
      id: row.id,
      title: row.title,
      description_snippet: row.description_snippet ?? '',
      source_url: row.source_url,
      source_name: row.source_name,
      deadline: row.deadline,
      deadline_text: row.deadline_text,
      amount: row.amount,
      currency: row.currency,
      eligibility: row.eligibility,
      fetched_at: row.fetched_at,
      extra: row.extra,
      created_at: row.created_at,
      updated_at: row.updated_at,
    }));

    return {
      items,
      pagination: {
        page,
        limit,
        total_items: totalItems,
        total_pages: totalPages,
        has_next: page < totalPages,
        has_prev: page > 1,
      },
    };
  }

  async getFilters(): Promise<FilterOptions> {
    const [sourceResult, currencyResult] = await Promise.all([
      this.db.query<{ source_name: string }>(
        'SELECT DISTINCT source_name FROM grants ORDER BY 1',
      ),
      this.db.query<{ currency: string }>(
        'SELECT DISTINCT currency FROM grants WHERE currency IS NOT NULL ORDER BY 1',
      ),
    ]);
    return {
      source_names: sourceResult.rows.map((r) => r.source_name),
      currencies: currencyResult.rows.map((r) => r.currency),
    };
  }

  async getById(id: number): Promise<GrantDetail | null> {
    const result = await this.db.query<GrantRow>(
      `SELECT id, title, description, source_url, source_name, deadline, deadline_text,
       amount, currency, eligibility, fetched_at, extra, created_at, updated_at
       FROM grants WHERE id = $1`,
      [id],
    );
    const row = result.rows[0];
    if (!row) return null;
    return {
      id: row.id,
      title: row.title,
      description: row.description ?? null,
      source_url: row.source_url,
      source_name: row.source_name,
      deadline: row.deadline,
      deadline_text: row.deadline_text,
      amount: row.amount,
      currency: row.currency,
      eligibility: row.eligibility,
      fetched_at: row.fetched_at,
      extra: row.extra,
      created_at: row.created_at,
      updated_at: row.updated_at,
    };
  }
}
