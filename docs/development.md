# Desarrollo Local

## Requisitos

- Python 3.13 o superior.
- Node.js 22 o superior.
- Docker Desktop.

## Servicios locales

Desde la raiz del proyecto:

```powershell
docker compose -f infrastructure/docker-compose.yml up -d
```

Para detenerlos:

```powershell
docker compose -f infrastructure/docker-compose.yml down
```

Para eliminar tambien los datos locales:

```powershell
docker compose -f infrastructure/docker-compose.yml down -v
```

## Backend

```powershell
Copy-Item .env.example .env
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
flask --app wsgi run --debug
```

La API queda disponible en `http://localhost:5000/api/health`.

## Frontend

```powershell
cd frontend
npm install
npm run dev
```

El frontend queda disponible en `http://localhost:5173`.

## Worker de prueba

Con Redis activo, inicie el worker y encole una tarea tecnica en terminales separadas:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
rq worker --url $env:REDIS_URL tostaduria
```

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m app.tasks.enqueue_probe
```

## Migraciones

Genere una migracion despues de cambiar los modelos:

```powershell
cd backend
alembic revision --autogenerate -m "descripcion del cambio"
alembic upgrade head
```

No modifique migraciones que ya se hayan aplicado en un entorno compartido.

## Administradores iniciales

Tras aplicar las migraciones, configure dos correos y contrasenas seguras exclusivamente en variables de entorno. No las agregue al repositorio.

```powershell
$env:ADMIN_1_EMAIL="admin1@ejemplo.com"
$env:ADMIN_1_PASSWORD="una-contrasena-de-al-menos-12-caracteres"
$env:ADMIN_2_EMAIL="admin2@ejemplo.com"
$env:ADMIN_2_PASSWORD="otra-contrasena-de-al-menos-12-caracteres"
flask --app wsgi create-initial-admins
```

El comando puede ejecutarse otra vez: no duplica usuarios y otorga el rol administrador a una cuenta existente cuando sea necesario.

## Tasa BCV e inventario

La tasa diaria usa `BCV_RATE_URL`, que por defecto apunta al sitio oficial del Banco Central de Venezuela. Para ejecutar la sincronización manualmente:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
flask --app wsgi sync-bcv-rate
```

Si la fuente oficial cambia su estructura o no está disponible, administración puede registrar una tasa manual en el panel, indicando el motivo. Las tasas manuales son auditables y no reemplazan el historial anterior.

El inventario se actualiza únicamente mediante movimientos. Registre ingresos, salidas, mermas o ajustes con un motivo; la API bloquea cualquier operación que produzca stock negativo.
