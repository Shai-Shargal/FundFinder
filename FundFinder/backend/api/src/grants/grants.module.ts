import { Module } from '@nestjs/common';
import { DatabaseModule } from '../database/database.module';
import { GrantsController } from './grants.controller';
import { GrantsService } from './grants.service';

@Module({
  imports: [DatabaseModule],
  controllers: [GrantsController],
  providers: [GrantsService],
})
export class GrantsModule {}
