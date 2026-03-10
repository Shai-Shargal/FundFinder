import {
  IsIn,
  IsOptional,
  IsBoolean,
  IsString,
  IsArray,
  Min,
  Max,
} from 'class-validator';
import { ApiPropertyOptional } from '@nestjs/swagger';
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
  @ApiPropertyOptional({ description: 'Page number', example: 1, default: 1 })
  @IsOptional()
  @Min(1)
  @Type(() => Number)
  page?: number = 1;

  @ApiPropertyOptional({
    description: 'Items per page (max 50)',
    example: 20,
    default: 20,
  })
  @IsOptional()
  @Min(1)
  @Max(50)
  @Type(() => Number)
  limit?: number = 20;

  @ApiPropertyOptional({
    description: 'Search in title, description, eligibility',
    example: 'scholarship',
  })
  @IsOptional()
  @IsString()
  q?: string;

  @ApiPropertyOptional({
    description: 'Filter by source name(s)',
    example: ['government', 'university'],
    type: [String],
  })
  @IsOptional()
  @Transform(({ value }) => toArray(value))
  @IsArray()
  @IsString({ each: true })
  source_name?: string[];

  @ApiPropertyOptional({
    description: 'Filter by presence of deadline',
    example: true,
  })
  @IsOptional()
  @Transform(({ value }) => toBoolean(value))
  @IsBoolean()
  has_deadline?: boolean;

  @ApiPropertyOptional({
    description: 'Sort field',
    enum: ['deadline', 'created_at', 'updated_at', 'title'],
    default: 'deadline',
  })
  @IsOptional()
  @IsIn(SORT_BY_WHITELIST)
  sort_by?: string = 'deadline';

  @ApiPropertyOptional({
    description: 'Sort order',
    enum: ['asc', 'desc'],
    default: 'asc',
  })
  @IsOptional()
  @IsIn(ORDER_WHITELIST)
  order?: 'asc' | 'desc' = 'asc';
}
