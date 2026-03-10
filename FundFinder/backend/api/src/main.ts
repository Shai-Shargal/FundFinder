import 'dotenv/config';
import { NestFactory } from '@nestjs/core';
import { ValidationPipe } from '@nestjs/common';
import { DocumentBuilder, SwaggerModule } from '@nestjs/swagger';
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

  const config = new DocumentBuilder()
    .setTitle('FundFinder API')
    .setDescription('FundFinder MVP REST API for grants and scholarships discovery')
    .setVersion('0.1.0')
    .addTag('Grants')
    .build();
  const document = SwaggerModule.createDocument(app, config);
  SwaggerModule.setup('docs', app, document);

  const port = process.env.PORT != null ? Number(process.env.PORT) : 3000;
  await app.listen(port);
  console.log(`FundFinder API listening on http://localhost:${port}/api`);
  console.log(`Swagger UI available at http://localhost:${port}/docs`);
}
bootstrap().catch((err) => {
  console.error(err);
  process.exit(1);
});
