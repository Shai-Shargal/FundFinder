import { Module } from '@nestjs/common';
import { DatabaseModule } from './database/database.module';
import { GrantsModule } from './grants/grants.module';

@Module({
  imports: [DatabaseModule, GrantsModule],
})
export class AppModule {}
