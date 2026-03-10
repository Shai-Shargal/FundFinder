import { GrantListItem } from './grant-list-item.interface';
import { Pagination } from './pagination.interface';

export interface ListResponse {
  items: GrantListItem[];
  pagination: Pagination;
}
