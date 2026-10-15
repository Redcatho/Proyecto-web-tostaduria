# Manual del Administrador — Tostaduria Platform

**Versión:** 0.1.0 · **Última actualización:** Octubre 2026

---

## Índice

1. Visión General
2. Arquitectura
3. Roles y Permisos
4. Flujo Completo del Sistema
5. Pantallas y Funcionalidades
6. Gestión de Inventario
7. Gestión de Pedidos
8. Tasa BCV y Precios
9. Notificaciones
10. Seguridad y Buenas Prácticas
11. Solución de Problemas

---

## 1. Visión General

Tostaduria Platform es un sistema B2B para la gestión comercial y operativa de una tostaduría de café. Permite a clientes (cafeterías y comercios) realizar pedidos de café en grano o presentaciones comerciales, y al equipo interno gestionar producción, inventario, pagos y despachos desde un solo lugar.

### Propósito

- Centralizar las ventas B2B eliminando WhatsApp, correos sueltos y hojas de cálculo.
- Automatizar cotizaciones, registro de pagos y seguimiento de pedidos.
- Proveer al equipo operativo herramientas para gestionar inventario y producción.
- Mantener un registro auditable de todas las transacciones.

---

## 2. Arquitectura

Navegador → Vercel (React 19 + TypeScript + Vite) → Render (Flask 3 + SQLAlchemy + Alembic) → PostgreSQL
                                                                      |
                                                                      +→ Redis → RQ Worker

- Frontend: React 19 + TypeScript + Vite, desplegado en Vercel.
- Backend: API Flask + SQLAlchemy + Alembic, desplegado en Render.
- Base de datos: PostgreSQL administrada en Render (plan básico 256 MB).
- Cache/Tareas: Redis y RQ para tareas asíncronas (notificaciones, sincronización BCV).
- Almacenamiento: Cloudflare R2 (S3-compatible, opcional) para comprobantes de pago e imágenes de producto.

> Nota: Sin Cloudflare R2 no funcionan la subida de comprobantes ni las imágenes de producto; el resto de la plataforma opera con normalidad.

---

## 3. Roles y Permisos

| Rol | Acceso | Quién lo usa |
|---|---|---|
| customer | Catálogo, carrito, cotizaciones, pedidos propios, perfil | Clientes B2B |
| admin | Todo el sistema | Administradores |
| operator | Catálogo, inventario, producción | Personal de planta |
| sales | Catálogo, pedidos, revisión de pagos | Equipo de ventas |
| dispatch | Pedidos, despacho, entregas | Personal de despacho |

### Matriz de permisos

Acción | admin | operator | sales | dispatch | customer
Ver catálogo público | ✅ | ✅ | ✅ | ✅ | ✅
Comprar | ✅ | — | — | — | ✅
Gestionar usuarios internos | ✅ | — | — | — | —
Aprobar/rechazar crédito | ✅ | — | — | — | —
Ver inventario y stock | ✅ | ✅ | ✅ | — | —
Registrar movimientos | ✅ | ✅ | — | — | —
Iniciar/completar producción | ✅ | ✅ | — | — | —
Fijar estimado de entrega | ✅ | — | ✅ | — | —
Registrar guía de despacho | ✅ | — | — | ✅ | —
Confirmar entrega | ✅ | — | — | ✅ | —
Revisar y aprobar pagos | ✅ | — | ✅ | — | —
Cancelar pedidos | ✅ | — | — | — | —
Procesar devoluciones | ✅ | — | — | — | —
Gestionar imágenes de producto | ✅ | — | — | — | —
Sincronizar/registrar tasa BCV | ✅ | — | ✅ | — | —

---

## 4. Flujo Completo del Sistema

### 4.1 Registro de Cliente

1. El cliente entra a la página principal y hace clic en Ingresar / Regístrate.
2. Completa nombre, correo, contraseña (mínimo 6 caracteres) y teléfono.
3. La cuenta se crea con rol customer y el cliente puede iniciar sesión inmediatamente.

### 4.2 Perfil Comercial

1. El cliente accede a Mi perfil.
2. Debe completar: contacto (nombre, teléfono), empresa (nombre, RIF, tipo, contacto) y dirección.
3. Sin perfil completo no puede solicitar crédito ni emitir cotizaciones.

### 4.3 Solicitud de Crédito

1. Desde el perfil, el cliente solicita crédito (plazo 7/15/30 días, límite USD, justificación).
2. Admin revisa desde Administración y aprueba o rechaza.

### 4.4 Compra

1. Catálogo con stepper numérico (+/-). Cafeterías requieren perfil de tostado.
2. Agregar al carrito muestra confirmación con Ir al carrito o Seguir comprando.
3. Carrito muestra resumen USD/VES y badge con cantidad en la barra.

### 4.5 Cotización

1. Continuar a cotización: validación de carrito, tasa BCV y perfil.
2. Seleccionar entrega, dirección y condición de pago.
3. Cotización válida 24 horas. Descargable en PDF.

### 4.6 Aceptación y Pago

1. Aceptar y crear pedido. Crédito se confirma automático si hay cupo.
2. Anticipo/pago completo queda como pending_payment.
3. Cliente sube comprobante (PDF/JPG/PNG, máx 10 MB).

### 4.7 Revisión de Pago

1. Admin/ventas revisa desde Operacion / Pedidos.
2. Aprueba (pedido pasa a confirmed) o rechaza (con motivo visible al cliente).

### 4.8 Producción

1. Iniciar producción: descuenta inventario, pasa a in_production.
2. Si falta stock: pending_stock. Reintentar tras reponer.
3. Completar producción: pasa a ready.

### 4.9 Despacho y Entrega

1. Registrar guía (transportista, tracking) → dispatched.
2. Confirmar entrega → delivered.

### 4.10 Devolución

1. Admin sobre pedidos delivered. Motivo + cantidades.
2. Sistema repone inventario → returned.

---

## 5. Pantallas y Funcionalidades

- / (raíz): Catálogo público con stepper, calculadora USD/VES, tasa BCV.
- / (autenticado): Dashboard con tasa BCV y acceso rápido.
- /perfil: Contacto, empresa, direcciones, crédito.
- /administracion: Solo admin. Usuarios, roles, crédito.
- /operacion: Admin/operator/sales. Stock, movimientos, historial, imágenes, tasa BCV.
- /operacion/pedidos: Admin/operator/dispatch/sales. Filtro, producción, despacho, devoluciones.
- /carrito: Stepper, eliminar, resumen USD/VES.
- /pedidos: Cliente. Lista, detalle, progreso, comprobantes, guía, PDF.

---

## 6. Gestión de Inventario

Inventario informativo (no bloquea compras). Control interno con alertas visuales.

Movimientos: Ingreso (+), Salida (-), Merma (-), Ajuste Sumar (+), Ajuste Restar (-).

Automáticos: al iniciar producción (descuenta), al cancelar/reponer (reponer), al devolver (reponer).

Stock bajo: naranja. Stock cero: rojo.

---

## 7. Gestión de Pedidos

issued → pending_payment → payment_under_review → confirmed → in_production → ready → dispatched → delivered

Alternos: pending_stock, returned, cancelled.

Cada transición queda registrada en el historial del pedido.

---

## 8. Tasa BCV y Precios

- Sincronización automática lun-vie 13:05 UTC.
- Fuentes: BCV oficial / DolarAPI / ExchangeRate.host / FALLBACK_BCV_RATE.
- Registro manual desde Operación.
- Precios base en USD. Equivalente VES = USD x tasa.
- Cotizaciones y pedidos congelan la tasa.

---

## 9. Notificaciones

- Correo: al cliente. Eventos: pedido creado, pago en revisión, confirmado, producción, despacho, entrega.
- Telegram: al grupo interno. Eventos: nuevo pedido, pago a revisar, pedido listo, devolución.

Telegram configurado. Correo requiere SMTP (SendGrid).

---

## 10. Seguridad

- Contraseñas con Argon2 (mínimo 6 caracteres).
- JWT en cookies con CSRF. Tokens: 15 min acceso, 30 días refresh.
- CSP, HSTS (producción), rate limiting (200/hora).
- Archivos en bucket privado con URLs prefirmadas.
- Credenciales solo en Render.

---

## 11. Solución de Problemas

| Problema | Causa | Solución |
|---|---|---|
| Failed to fetch | Backend caído o CORS | Verificar backend y CORS_ORIGINS |
| BCV exchange rate required | Sin tasa registrada | Sincronizar desde Operación |
| Sin enlaces de Admin | Usuario sin rol admin | Ejecutar create-initial-admins |
| Insufficient stock | Movimiento dejaría negativo | Registrar Ingreso primero |
| PDF no se descarga | WeasyPrint no disponible | En Render funciona correctamente |
| No llegan notificaciones | Bot no está en el grupo | Verificar chat ID y membresía del bot |

---

© 2026 Tostaduria Platform · Versión 0.1.0
