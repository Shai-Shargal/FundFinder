import { NestFactory } from '@nestjs/core';
import { ValidationPipe } from '@nestjs/common';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  app.setGlobalPrefix('api');
  app.useGlobalPipes(
    new ValidationPipe({
      whitelist: true,
      transform: true,
      transformOptions: { enableImplicitConversion: true },
      forbidNonWhitelisted: false,
    }),
  );
  const port = process.env.PORT != null ? Number(process.env.PORT) : 3000;
  await app.listen(port);
  console.log(`FundFinder API listening on http://localhost:${port}/api`);
}
bootstrap().catch((err) => {
  console.error(err);
  process.exit(1);
});
