import {
  Controller,
  Get,
  Param,
  ParseIntPipe,
  Query,
  HttpException,
  HttpStatus,
} from '@nestjs/common';
import { GrantsService } from './grants.service';
import { GetGrantsQueryDto } from './dto/get-grants-query.dto';

@Controller('grants')
export class GrantsController {
  constructor(private readonly grantsService: GrantsService) {}

  @Get()
  async list(@Query() query: GetGrantsQueryDto) {
    return this.grantsService.list(query);
  }

  @Get('filters')
  async getFilters() {
    return this.grantsService.getFilters();
  }

  @Get(':id')
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
