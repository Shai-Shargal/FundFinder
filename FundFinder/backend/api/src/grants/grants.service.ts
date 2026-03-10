import { Injectable } from '@nestjs/common';
import { DatabaseService } from '../database/database.service';
import { FilterOptions } from './interfaces/filter-options.interface';
import { GrantDetail } from './interfaces/grant-detail.interface';
import { GrantListItem } from './interfaces/grant-list-item.interface';
import { ListResponse } from './interfaces/list-response.interface';

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

  async list(): Promise<ListResponse> {
    const listSql = `
      SELECT
        id, title,
        LEFT(description::text, ${SNIPPET_LENGTH}) AS description_snippet,
        source_url, source_name, deadline, deadline_text, amount, currency, eligibility,
        fetched_at, extra, created_at, updated_at
      FROM grants
      ORDER BY id ASC
    `;
    const listResult = await this.db.query<GrantRow>(listSql);
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

    return { items };
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
