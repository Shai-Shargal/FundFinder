export interface GrantListItem {
  id: number;
  title: string;
  description_snippet: string;
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
