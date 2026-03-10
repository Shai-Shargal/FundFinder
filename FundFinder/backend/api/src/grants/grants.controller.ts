import {
  Controller,
  Get,
  Param,
  ParseIntPipe,
  Query,
  HttpException,
  HttpStatus,
} from '@nestjs/common';
import { ApiTags, ApiOperation, ApiParam, ApiResponse } from '@nestjs/swagger';
import { GrantsService } from './grants.service';
import { GetGrantsQueryDto } from './dto/get-grants-query.dto';

@ApiTags('Grants')
@Controller('grants')
export class GrantsController {
  constructor(private readonly grantsService: GrantsService) {}

  @Get()
  @ApiOperation({ summary: 'List grants with optional filters and pagination' })
  @ApiResponse({ status: 200, description: 'Paginated list of grants' })
  async list(@Query() query: GetGrantsQueryDto) {
    return this.grantsService.list(query);
  }

  @Get('filters')
  @ApiOperation({ summary: 'Get filter options (source names and currencies)' })
  @ApiResponse({ status: 200, description: 'Filter options for source names and currencies' })
  async getFilters() {
    return this.grantsService.getFilters();
  }

  @Get(':id')
  @ApiOperation({ summary: 'Get a single grant by ID' })
  @ApiParam({ name: 'id', description: 'Grant ID', example: 1 })
  @ApiResponse({ status: 200, description: 'Grant detail' })
  @ApiResponse({ status: 404, description: 'Grant not found' })
  async getById(@Param('id', ParseIntPipe) id: number) {
    const grant = await this.grantsService.getById(id);
    if (!grant) {
      throw new HttpException(
        {
          error: {
            code: 'NOT_FOUND',
            message: `Grant with id ${id} not found.`,
          },
        },
        HttpStatus.NOT_FOUND,
      );
    }
    return grant;
  }
}
