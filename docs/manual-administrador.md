# Manual del Administrador — Tostaduria Platform

**Versión:** 0.1.0 · **Última actualización:** Octubre 2026

---

## Índice

1. [Visión General](#1-visión-general)
2. [Arquitectura](#2-arquitectura)
3. [Roles y Permisos](#3-roles-y-permisos)
4. [Flujo Completo del Sistema](#4-flujo-completo-del-sistema)
5. [Pantallas y Funcionalidades](#5-pantallas-y-funcionalidades)
6. [Gestión de Inventario](#6-gestión-de-inventario)
7. [Gestión de Pedidos](#7-gestión-de-pedidos)
8. [Tasa BCV y Precios](#8-tasa-bcv-y-precios)
9. [Notificaciones](#9-notificaciones)
10. [Seguridad y Buenas Prácticas](#10-seguridad-y-buenas-prácticas)
11. [Solución de Problemas](#11-solución-de-problemas)

---

## 1. Visión General

Tostaduria Platform es un sistema B2B (Business-to-Business) para la gestión comercial y operativa de una tostaduría de café. Permite a clientes comerciales y cafeterías realizar pedidos de café en grano o presentaciones comerciales, y al equipo interno gestionar la producción, el inventario y los despachos.

### Propósito

- Centralizar las ventas B2B en un solo lugar.
- Automatizar cotizaciones, registro de pagos y seguimiento de pedidos.
- Proveer al equipo operativo herramientas para gestionar inventario y producción.
- Mantener un registro auditable de todas las transacciones.

---

## 2. Arquitectura

Navegador → Vercel (React) → Render (Flask API) → PostgreSQL
                              |
                              +→ Redis → RQ Worker

- **Frontend:** React + TypeScript + Vite, desplegado en Vercel.
- **Backend:** API Flask + SQLAlchemy + Alembic, desplegado en Render.
- **Base de datos:** PostgreSQL administrada en Render.
- **Cache/Tareas:** Redis y RQ para tareas asíncronas (notificaciones, sincronización BCV).
- **Almacenamiento:** Cloudflare R2 (S3-compatible) para comprobantes de pago e imágenes de producto.

---

## 3. Roles y Permisos

| Rol | Acceso | Quién lo usa |
|---|---|---|
| customer | Catálogo, carrito, cotizaciones, pedidos propios, perfil | Clientes B2B |
| admin | Todo el sistema | Administradores |
| operator | Catálogo, inventario, producción | Personal de planta |
| sales | Catálogo, pedidos, revisión de pagos | Equipo de ventas |
| dispatch | Pedidos, despacho, entregas | Personal de despacho |

### Permisos detallados por rol

| Acción | admin | operator | sales | dispatch | customer |
|---|---|---|---|---|---|
| Ver catálogo | ✅ | ✅ | ✅ | ✅ | ✅ |
| Comprar | ✅ | — | — | — | ✅ |
| Gestionar usuarios | ✅ | — | — | — | — |
| Aprobar crédito | ✅ | — | — | — | — |
| Ver inventario | ✅ | ✅ | ✅ | — | — |
| Registrar movimientos | ✅ | ✅ | — | — | — |
| Iniciar producción | ✅ | ✅ | — | — | — |
| Registrar despacho | ✅ | — | — | ✅ | — |
| Confirmar entrega | ✅ | — | — | ✅ | — |
| Revisar pagos | ✅ | — | ✅ | — | — |
| Cancelar pedidos | ✅ | — | — | — | — |
| Procesar devoluciones | ✅ | — | — | — | — |
| Gestionar imágenes | ✅ | — | — | — | — |
| Sincronizar tasa BCV | ✅ | — | ✅ | — | — |

---

## 4. Flujo Completo del Sistema

### 4.1 Registro de Cliente

1. El cliente entra a la página principal y hace clic en **Ingresar** → **Regístrate**.
2. Completa: nombre, correo, contraseña (mínimo 6 caracteres) y teléfono.
3. Recibe confirmación y puede iniciar sesión inmediatamente.

### 4.2 Perfil Comercial

1. Una vez autenticado, el cliente accede a **Mi perfil**.
2. Debe completar:
   - **Datos personales:** nombre, teléfono.
   - **Empresa:** nombre comercial, RIF, tipo de negocio (cafetería, supermercado, mayorista), responsable, correo y teléfono de contacto.
   - **Dirección:** al menos una dirección de entrega.
3. Una vez completa la empresa y tiene al menos una dirección, su perfil está listo.

### 4.3 Solicitud de Crédito (opcional)

1. Desde el perfil, el cliente puede solicitar crédito comercial.
2. Selecciona: plazo (7, 15 o 30 días), límite en USD y justificación.
3. Un administrador revisa y aprueba/rechaza desde **Administración**.
4. Si se aprueba, el cliente puede usar **Crédito aprobado** como condición de pago.

### 4.4 Compra

1. El cliente navega el **Catálogo**, filtra por Todo, Comercial o Cafeterías.
2. Usa el **stepper numérico** para seleccionar cantidad y perfil de tostado (cafeterías).
3. Hace clic en **Agregar al carrito** — aparece un mensaje de confirmación con opciones:
   - **Ir al carrito** → lo lleva al carrito.
   - **Seguir comprando** → el mensaje desaparece.
4. En el carrito puede ajustar cantidades con el stepper, eliminar productos y ver el resumen.

### 4.5 Cotización

1. Desde el carrito, hace clic en **Continuar a cotización**.
2. Selecciona:
   - **Modalidad de entrega:** retiro en planta, entrega propia en Caracas, paquetería nacional.
   - **Dirección de entrega** (si aplica).
   - **Condición de pago:** anticipo 50%, pago completo o crédito aprobado.
3. El sistema genera una cotización válida por 24 horas.
4. El cliente puede descargar la cotización en PDF.

### 4.6 Aceptación y Pago

1. El cliente revisa la cotización y hace clic en **Aceptar y crear pedido**.
2. Si eligió **crédito aprobado**, el pedido se confirma automáticamente si hay cupo disponible.
3. Si eligió **anticipo o pago completo**, el pedido queda como `pending_payment`.
4. El cliente sube un **comprobante de pago** (PDF, JPG, PNG):
   - Selecciona método, moneda (USD/VES), monto, referencia y archivo.
   - El archivo se almacena de forma privada en el bucket S3.

### 4.7 Revisión de Pago

1. Un administrador o ventas ve el pedido con el comprobante desde **Operación → Pedidos**.
2. Revisa el comprobante (puede ver la imagen via enlace temporal) y:
   - **Aprueba:** el pago se registra como verificado.
   - **Rechaza:** debe indicar un motivo, el cliente lo verá en el detalle del pedido.
3. Si los pagos verificados cubren el monto requerido, el pedido pasa a `confirmed`.

### 4.8 Producción

1. Un operador o administrador selecciona un pedido `confirmed`.
2. Hace clic en **Iniciar producción**:
   - El sistema descuenta el inventario automáticamente.
   - El pedido pasa a `in_production`.
3. Al terminar la producción, hace clic en **Completar producción**:
   - El pedido pasa a `ready`.

### 4.9 Despacho y Entrega

1. El personal de despacho ve los pedidos `ready`.
2. Registra la **guía de despacho**: transportista, número de tracking y nota.
   - El pedido pasa a `dispatched`.
3. Al confirmar la entrega, el pedido pasa a `delivered`.

### 4.10 Devolución

1. Solo un administrador puede procesar devoluciones sobre pedidos `delivered`.
2. Indica el motivo y la cantidad a devolver.
3. El sistema repone el inventario automáticamente y el pedido pasa a `returned`.

---

## 5. Pantallas y Funcionalidades

### 5.1 Página Principal (Catálogo Público)

- **Acceso:** Público (sin autenticación)
- **Funcionalidades:**
  - Visualización de productos con imágenes.
  - Filtro por línea (Todo, Comercial, Cafeterías).
  - Stepper numérico para seleccionar cantidad.
  - Selector de perfil de tostado (solo cafeterías).
  - Botón **Agregar al carrito** (requiere autenticación).
  - **Calculadora USD → VES** con la tasa BCV vigente.
  - Tasa BCV del día mostrada en la cabecera.

### 5.2 Dashboard (Usuario autenticado)

- Muestra la tasa BCV del día.
- Enlace rápido a completar el perfil.

### 5.3 Perfil

- **URL:** /perfil
- **Secciones:**
  - **Contacto:** nombre y teléfono.
  - **Empresa:** datos fiscales y de contacto.
  - **Direcciones:** agregar y listar direcciones.
  - **Crédito:** solicitar crédito, ver estado de solicitudes y términos activos.

### 5.4 Administración

- **URL:** /administracion — Solo admin
- **Funcionalidades:**
  - **Crear cuentas internas:** registrar operadores, ventas, despacho y administradores.
  - **Gestionar usuarios:** ver lista, suspender/activar cuentas.
  - **Solicitudes de crédito:** aprobar o rechazar con plazos y límites.

### 5.5 Operación — Catálogo, Stock y Tasa

- **URL:** /operacion — admin, operator, sales
- **Secciones:**
  - **Productos y existencias:** tabla con stock actual, umbral bajo (naranja) y stock cero (rojo).
  - **Registrar movimiento:** formulario para ingresar, sacar, ajustar o mermar inventario.
  - **Historial:** últimos 15 movimientos registrados.
  - **Imagen de empaque:** subir, reemplazar o eliminar imágenes de producto.
  - **Tasa BCV:** sincronizar desde el BCV o registrar tasa manual.

### 5.6 Operación — Pedidos

- **URL:** /operacion/pedidos — admin, operator, dispatch, sales
- **Funcionalidades:**
  - Filtro por estado (confirmed, in_production, ready, dispatched, delivered, etc.).
  - Gestión de pedido seleccionado:
    - Ver productos y cantidades.
    - **Fijar estimado de entrega** (admin/sales).
    - **Iniciar producción** (admin/operator).
    - **Completar producción** (admin/operator).
    - **Registrar despacho** (admin/dispatch).
    - **Confirmar entrega** (admin/dispatch).
    - **Procesar devolución** (admin).
    - **Cancelar pedido** (admin).

### 5.7 Carrito

- **URL:** /carrito
- Stepper numérico para ajustar cantidades.
- Botón eliminar por producto.
- Resumen con subtotal, descuento, total USD y VES.
- Botón **Continuar a cotización**.

### 5.8 Pedidos (Cliente)

- **URL:** /pedidos
- Lista de pedidos con estado, total y saldo pendiente.
- Detalle del pedido: productos, progreso, comprobantes, guía de despacho.
- Subir comprobante de pago.
- Descargar pedido PDF.
- Ver estimado de entrega.

---

## 6. Gestión de Inventario

### 6.1 Propósito

El inventario es **informativo para el personal interno**. No bloquea las compras de los clientes. Sirve para llevar control de existencias, registrar movimientos e identificar productos con stock bajo.

### 6.2 Tipos de Movimiento

| Tipo | Cuándo usarlo | Efecto |
|---|---|---|
| Ingreso | Llega mercancía nueva | + stock |
| Salida | Se retira mercancía | − stock |
| Merma | Producto dañado o pérdida | − stock |
| Ajuste Sumar | Corregir inventario al alza | + stock |
| Ajuste Restar | Corregir inventario a la baja | − stock |

### 6.3 Movimientos Automáticos

- Al **iniciar producción** se descuenta inventario automáticamente.
- Al **cancelar** un pedido en producción se repone el inventario.
- Al procesar una **devolución** se repone el inventario.

---

## 7. Gestión de Pedidos

Estados: `issued → pending_payment → payment_under_review → confirmed → in_production → ready → dispatched → delivered`

Estados alternos: `pending_stock`, `returned`, `cancelled`.

---

## 8. Tasa BCV y Precios

- Sincronización automática de lunes a viernes (13:05 UTC) en Render.
- Fuentes en orden: BCV oficial → DolarAPI → ExchangeRate.host → FALLBACK_BCV_RATE.
- Se puede registrar tasa manual desde el panel de operación.
- Los precios base están en USD. El equivalente en VES usa la tasa del día.
- Cotizaciones y pedidos congelan la tasa al momento de emitirse.

---

## 9. Notificaciones

| Canal | Destinatario | Eventos |
|---|---|---|
| **Correo** | Cliente | Pedido creado, pago en revisión, confirmado, en producción, despachado, entregado |
| **Telegram** | Equipo interno | Nuevo pedido, pago recibido, pedido listo, devolución procesada |

Para configurar: definir en Render las variables `MAIL_*` y `TELEGRAM_*`.

---

## 10. Seguridad y Buenas Prácticas

- Contraseñas con **Argon2** (mínimo 6 caracteres).
- **JWT en cookies** con CSRF protection.
- **Content-Security-Policy** activa.
- **HSTS** en producción.
- Archivos de comprobantes en bucket **privado** con URLs prefirmadas.
- Credenciales solo en **Render**, nunca en Vercel ni en Git.

---

## 11. Solución de Problemas

| Problema | Causa | Solución |
|---|---|---|
| "Failed to fetch" | Backend caído o CORS | Verificar backend y CORS_ORIGINS |
| "BCV exchange rate required" | Sin tasa registrada | Sincronizar desde Operación |
| Sin enlaces de Admin | Usuario sin rol admin | Ejecutar `create-initial-admins` |
| "Insufficient stock" | Movimiento dejaría negativo | Registrar Ingreso primero |
| PDF no se descarga | WeasyPrint no disponible | En Render funciona con formato completo |

---

© 2026 Tostaduria Platform · Versión 0.1.0