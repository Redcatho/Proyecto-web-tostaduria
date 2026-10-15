# Arquitectura

Tostaduria Platform separa la interfaz publica de la API y de los procesos asincronos.

```text
Navegador -> Vercel (React) -> Render (Flask API) -> PostgreSQL
                                      |
                                      +-> Redis -> RQ worker
```

El frontend nunca se conecta directamente a PostgreSQL, Redis ni a proveedores externos. La API centraliza autorizacion, reglas comerciales y acceso a datos. El worker ejecuta tareas que no deben bloquear una solicitud HTTP, como notificaciones, generacion de documentos y sincronizacion de la tasa BCV.

Las tablas de negocio se agregaran mediante migraciones Alembic a partir de la Fase 2.
