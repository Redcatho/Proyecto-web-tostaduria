# Tostaduria Platform

Plataforma B2B para la gestion comercial y operativa de Tostaduria.

## Estado actual

- Fase 1: infraestructura React, Flask, PostgreSQL, Redis y despliegues preparada.
- Fase 2: registro de clientes, roles internos, empresas, direcciones, credito y auditoria implementados.
- Fase 3: catálogo B2B, inventario auditable, precios USD/VES y tasa BCV implementados.
- Fase 4: carrito B2B, cotizaciones de 24 horas y pedidos pendientes de pago implementados.
- Fase 5: historial de pedidos, comprobantes privados de pago, revisión comercial y uso de crédito implementados.
- Fase 6: producción, descuento/reposición de inventario, despacho y entrega de pedidos implementados.
- Fase 7: notificaciones de operación, documentos PDF e imágenes de producto preparada.

## Arquitectura

- `frontend/`: React, TypeScript y Vite. Se despliega en Vercel.
- `backend/`: API Flask, SQLAlchemy y Alembic. Se despliega en Render.
- PostgreSQL: datos de negocio administrados en Render.
- Redis y RQ: tareas asincronas, notificaciones y procesos programados.

## Inicio rapido local

1. Copie `.env.example` a `.env`.
2. Inicie PostgreSQL y Redis:

   ```powershell
   docker compose -f infrastructure/docker-compose.yml up -d
   ```

3. Instale y ejecute la API:

   ```powershell
   cd backend
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   alembic upgrade head
   flask --app wsgi run --debug
   ```

4. En otra terminal, instale y ejecute el frontend:

   ```powershell
   cd frontend
   npm install
   npm run dev
   ```

5. Opcionalmente, inicie el worker RQ en una tercera terminal:

   ```powershell
   cd backend
   .\.venv\Scripts\Activate.ps1
   rq worker tostaduria
   ```

Consulte `docs/development.md` y `docs/deployment.md` antes de desplegar.
