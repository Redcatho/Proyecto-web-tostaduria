# Despliegue

## Render

1. Conecte este repositorio en Render y seleccione el Blueprint `render.yaml`.
2. Cree o vincule una instancia Redis compatible y asigne su URL a `REDIS_URL` en API y worker.
3. Defina `CORS_ORIGINS` con el dominio de Vercel, sin barra final.
4. Defina `APP_BASE_URL` con el dominio publico del frontend.
5. Ejecute `alembic upgrade head` mediante un Shell de Render antes de publicar una version que incluya migraciones.
6. Configure los secretos compartidos que futuras tareas necesiten con el mismo valor en API y worker.
7. Mantenga `JWT_COOKIE_SAMESITE=None` en producción para permitir sesiones entre el dominio de Vercel y la API de Render. La API ya exige cookies seguras y token CSRF en solicitudes autenticadas que modifican datos.
8. El Cron `tostaduria-bcv-rate-sync` ejecuta la consulta de tasa BCV a las 13:05 UTC de lunes a viernes. Ajuste el horario en `render.yaml` si la hora de publicación oficial cambia.

## Vercel

1. Importe el repositorio.
2. Configure `frontend` como Root Directory.
3. Agregue `VITE_API_URL` con la URL publica de la API de Render.
4. Configure `VITE_APP_ENV=production`.
5. Publique y copie el dominio final en `CORS_ORIGINS` de Render.

## Secretos

No guarde secretos en Git. Configure `SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`, proveedores de correo, Telegram y almacenamiento de archivos exclusivamente en los paneles de los proveedores.

## Comprobantes de pago

Configure un bucket privado compatible con S3 (por ejemplo, Cloudflare R2) y defina en Render `OBJECT_STORAGE_ENDPOINT`, `OBJECT_STORAGE_BUCKET`, `OBJECT_STORAGE_ACCESS_KEY_ID`, `OBJECT_STORAGE_SECRET_ACCESS_KEY` y, si corresponde, `OBJECT_STORAGE_REGION`. El bucket debe aceptar `PUT` desde el dominio de Vercel con `Content-Type` y mantener el acceso público deshabilitado. La API emite enlaces prefirmados temporales para carga y lectura; no exponga las credenciales en Vercel.

## Comunicación e imágenes

Configure `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD` y `MAIL_DEFAULT_SENDER` para el correo transaccional. Para avisos internos, defina `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID`. Las imágenes de producto usan `PRODUCT_IMAGE_ENDPOINT` y `PRODUCT_IMAGE_BUCKET`; ese bucket o prefijo debe permitir lectura pública, mientras que sus credenciales siguen solo en Render. Configure CORS para permitir cargas `PUT` desde el dominio de Vercel.
