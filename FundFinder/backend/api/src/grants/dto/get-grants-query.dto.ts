import {
  IsIn,
  IsOptional,
  IsBoolean,
  IsString,
  IsArray,
  Min,
  Max,
} from 'class-validator';
import { Transform, Type } from 'class-transformer';

const SORT_BY_WHITELIST = ['deadline', 'created_at', 'updated_at', 'title'] as const;
const ORDER_WHITELIST = ['asc', 'desc'] as const;

function toArray(value: unknown): string[] {
  if (value == null) return [];
  if (Array.isArray(value)) return value.filter((v): v is string => typeof v === 'string');
  return typeof value === 'string' ? [value] : [];
}

function toBoolean(value: unknown): boolean | undefined {
  if (value === undefined || value === null) return undefined;
  if (typeof value === 'boolean') return value;
  if (value === 'true') return true;
  if (value === 'false') return false;
  return undefined;
}

export class GetGrantsQueryDto {
  @IsOptional()
  @Min(1)
  @Type(() => Number)
  page?: number = 1;

  @IsOptional()
  @Min(1)
  @Max(50)
  @Type(() => Number)
  limit?: number = 20;

  @IsOptional()
  @IsString()
  q?: string;

  @IsOptional()
  @Transform(({ value }) => toArray(value))
  @IsArray()
  @IsString({ each: true })
  source_name?: string[];

  @IsOptional()
  @Transform(({ value }) => toBoolean(value))
  @IsBoolean()
  has_deadline?: boolean;

  @IsOptional()
  @IsIn(SORT_BY_WHITELIST)
  sort_by?: string = 'deadline';

  @IsOptional()
  @IsIn(ORDER_WHITELIST)
  order?: 'asc' | 'desc' = 'asc';
}
