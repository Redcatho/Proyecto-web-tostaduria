# Manual del Administrador — Tostaduria Platform v0.1.0
**Ultima actualizacion:** Octubre 2026

---

## 1. Vision General

Tostaduria Platform es un sistema B2B para la gestion comercial y operativa de una tostaduria de cafe. Clientes (cafeterias y comercios) realizan pedidos de cafe en grano o presentaciones comerciales. El equipo interno gestiona produccion, inventario, pagos y despachos desde un solo lugar.

**Arquitectura:** Navegador (Vercel, React 19) > API (Render, Flask 3) > PostgreSQL / Redis > RQ Worker.
Almacenamiento de archivos en Cloudflare R2 (S3-compatible).

---

## 2. Flujo Completo

### 2.1 Registro
* Ingresar > Registrate. Nombre, correo, contrasena (6+ caracteres). Rol customer automatico.

### 2.2 Perfil Comercial
* Perfil > Completar empresa (nombre, RIF, tipo, responsable, correo, telefono) y agregar direccion.
* El estado del perfil se indica con un badge verde (completo) o rojo (incompleto).
* Sin perfil completo no se puede cotizar ni solicitar credito.

### 2.3 Solicitud de Credito (opcional)
* Perfil > Credito > plazo (7/15/30 dias), limite USD, justificacion.
* Un administrador aprueba/rechaza desde Administracion.

### 2.4 Compra
* Catalogo con stepper numerico (+ / -).
* Comerciales: paso de 1 bulto. Cafeterias: paso de 5 kg + perfil de tostado.
* Agregar al carrito muestra toast de confirmacion: Ir al carrito o Seguir comprando.
* Badge numerico en el enlace Carrito de la barra de navegacion (se actualiza al agregar/eliminar).
* Carrito muestra resumen USD, VES segun tasa BCV, y datos bancarios para transferencia.
* Calculadora USD/VES integrada en el catalogo.

### 2.5 Cotizacion
* Continuar a cotizacion > modalidad entrega, direccion, condicion de pago.
* Valida tasa BCV vigente, perfil completo y carrito con productos.
* Cotizacion valida 24 horas. Descargable en PDF.

### 2.6 Pago y Aprobacion
* Aceptar cotizacion > pending_payment.
* Cliente sube comprobante (PDF/JPG/PNG, max 10 MB) desde el detalle del pedido.
* El archivo se envía al backend y este lo sube a Cloudflare R2 (sin CORS).
* El pedido pasa a payment_under_review.
* Un administrador o ventas lo revisa en Operacion > Pedidos, filtra payment_under_review: puede ver el comprobante, aprobar o rechazar (con nota).
* Al aprobar: el pedido pasa a confirmed y Telegram notifica Pedido confirmado.

### 2.7 Produccion
* Operador/admin: Iniciar produccion (descuenta inventario, pasa a in_production).
* Si falta stock: pending_stock. Reintentar tras reponer.
* Completar produccion: pasa a ready. Telegram avisa al grupo interno.
* El administrador/ventas puede notificar manualmente al cliente con el boton Notificar al cliente.

### 2.8 Despacho y Entrega
* Dispatch/admin: Registrar guia (transportista, tracking, nota) > dispatched.
* Confirmar entrega > delivered.
* Admin: Procesar devolucion (motivo, cantidades) > returned (reponer inventario).

---

## 3. Roles y Permisos

| Rol | Acceso |
| --- | --- |
| customer | Catalogo, carrito, cotizaciones, pedidos propios, perfil |
| admin | Todo el sistema |
| operator | Catalogo, inventario, produccion |
| sales | Catalogo, pedidos, revision de pagos, notificar cliente |
| dispatch | Pedidos, despacho, entregas |

**Matriz de permisos detallada:**
- Ver catalogo: todos
- Comprar: customer, admin
- Gestionar usuarios: admin
- Aprobar credito: admin
- Ver inventario: admin, operator, sales
- Registrar movimientos: admin, operator
- Iniciar/completar produccion: admin, operator
- Fijar estimado entrega: admin, sales
- Revisar pagos (aprobar/rechazar): admin, sales
- Registrar despacho: admin, dispatch
- Confirmar entrega: admin, dispatch
- Cancelar pedidos: admin
- Procesar devoluciones: admin
- Gestionar imagenes de producto: admin
- Sincronizar/registrar tasa BCV: admin, sales
- Notificar al cliente (pedido listo): admin, sales

---

## 4. Pantallas del Sistema

### 4.1 Pagina Principal / Catalogo (/)
Publico. Muestra productos con imagen, descripcion, origen, precio. Stepper numerico, perfil de tostado (cafeterias), calculadora USD/VES, tasa BCV del dia.

### 4.2 Dashboard (/ autenticado)
Saludo personalizado, tasa BCV destacada, enlace a completar perfil.

### 4.3 Perfil (/perfil)
Contacto, empresa, direcciones, solicitud de credito, estado del perfil (completo/incompleto).

### 4.4 Administracion (/administracion)
Solo admin. Crear cuentas internas (admin, operator, sales, dispatch), gestionar usuarios (suspender/activar), aprobar solicitudes de credito.

### 4.5 Operacion - Catalogo y Stock (/operacion)
Admin, operator, sales. Tabla de productos con stock (naranja bajo, rojo cero). Formulario de movimientos (ingreso, salida, merma, ajuste). Historial de movimientos. Gestion de imagenes de producto. Tasa BCV (sincronizar o manual).

### 4.6 Operacion - Pedidos (/operacion/pedidos)
Admin, operator, dispatch, sales. Filtro por estado (payment_under_review, confirmed, in_production, pending_stock, ready, dispatched, delivered, etc.).
**Por estado se puede:**
- payment_under_review: ver comprobante, aprobar o rechazar pago (admin/sales)
- confirmed: fijar estimado de entrega (admin/sales), iniciar produccion (admin/operator)
- pending_stock: reintentar produccion (admin/operator)
- in_production: completar produccion (admin/operator)
- ready: notificar al cliente (admin/sales), registrar despacho (admin/dispatch)
- dispatched: confirmar entrega (admin/dispatch)
- delivered: procesar devolucion (admin)
- Cualquier estado disponible: cancelar pedido (admin) con reposicion de inventario si corresponde.

### 4.7 Carrito (/carrito)
Stepper para ajustar cantidades, eliminar, resumen USD/VES, datos bancarios para transferencia, boton a cotizacion.

### 4.8 Pedidos Cliente (/pedidos)
Lista de pedidos. Detalle: productos, progreso (historial de estados), comprobantes de pago, guia de despacho, estimado de entrega, descarga de PDF.

---

## 5. Productos y Precios

### Linea Comercial (bultos)
| Producto | SKU | Precio USD |
| --- | --- | --- |
| Cafe Filtrado 250g | FIL-001 | .00 |
| Cafe Espresso 500g | ESP-001 | .00 |
| Cafe Premium 250g | PRM-001 | .00 |

### Linea Cafeterias (por kg, multiplos de 5 kg)
| Producto | SKU | Precio/kg | 5 kg = |
| --- | --- | --- | --- |
| Cafe Especial en Grano | GRA-001 | .00/kg | .00 |
| Cafe Premium Mezcla Casa | PRE-001 | .00/kg | .00 |
| Cafe Organico de Finca | ORG-001 | .00/kg | .00 |

---

## 6. Estados del Pedido

issued (cotizacion) > pending_payment > payment_under_review > confirmed > in_production > ready > dispatched > delivered

Alternos: pending_stock (falta inventario), returned (devuelto), cancelled (cancelado).

---

## 7. Gestion de Inventario

El inventario es informativo (no bloquea compras). Sirve para control interno, identificar stock bajo (naranja) o cero (rojo), y descontar automaticamente al iniciar produccion.

**Tipos de movimiento:** Ingreso (+), Salida (-), Merma (-), Ajuste Sumar (+), Ajuste Restar (-).

**Movimientos automaticos:**
- Iniciar produccion: descuenta inventario (outgoing + motivo Production).
- Cancelar pedido en produccion: repone inventario.
- Devolucion: repone inventario.

---

## 8. Tasa BCV y Precios

* Sincronizacion automatica lun-vie 13:05 UTC en Render (cron job).
* Fuentes en orden: BCV oficial (bcv.org.ve) > DolarAPI (ve.dolarapi.com) > ExchangeRate.host > FALLBACK_BCV_RATE (variable de entorno).
* Registro manual desde Operacion (requiere motivo, queda auditado).
* Precios base en USD. Equivalente VES = USD x tasa del dia.
* Cotizaciones y pedidos congelan la tasa al momento de emitirse.

---

## 9. Notificaciones

| Evento | Telegram (grupo interno) | Correo (cliente) |
| --- | --- | --- |
| Pedido creado | Nuevo pedido: numero, cliente, total, condicion | Pedido recibido |
| Pago recibido | Pago por revisar: numero, cliente, total | Pago en revision |
| Pago verificado | Pago verificado - Pedido confirmado | Pedido confirmado |
| Pago rechazado | -- | Comprobante rechazado |
| Produccion iniciada | Produccion iniciada: numero | Pedido en produccion |
| Pedido listo | Listo para despachar | *Manual* (admin pulsa Notificar) |
| Despachado | Pedido despachado: numero, transportista | Pedido despachado |
| Entregado | -- | Pedido entregado |
| Devolucion | Devolucion procesada | Devolucion procesada |

*El correo de pedido listo se envia SOLO cuando el admin pulsa Notificar al cliente en Operacion.*

---

## 10. Seguridad

* Contrasenas con Argon2 (minimo 6 caracteres).
* JWT en cookies (HttpOnly) + Bearer token en localStorage para auth cross-domain.
* CSRF protection activo (X-CSRF-TOKEN header).
* Content-Security-Policy con connect-src https: para API externa.
* HSTS en produccion (max-age=31536000).
* Rate limiting: 200 peticiones/hora por IP.
* Archivos de comprobantes en bucket privado con URLs prefirmadas temporales (15 min).
* Imagenes de producto en bucket publico con dominio r2.dev.
* Subida de archivos via proxy (cliente > API > R2, sin CORS del navegador).
* Secretos solo en variables de entorno de Render (nunca en Git ni en Vercel).
* Auditoria de todas las acciones en tabla audit_logs.

---

## 11. Almacenamiento (Cloudflare R2)

| Bucket | Proposito | Acceso |
| --- | --- | --- |
| proyecto-tostaduria-proofs | Comprobantes de pago | Privado (solo API con boto3) |
| proyecto-tostaduria-web | Imagenes de producto | Publico (r2.dev) |

Requiere OBJECT_STORAGE_* y PRODUCT_IMAGE_* configurados en Render.

---

## 12. Solucion de Problemas

| Problema | Causa | Solucion |
| --- | --- | --- |
| Failed to fetch | Backend caido, CORS o VITE_API_URL incorrecto | Verificar Render, CORS_ORIGINS y VITE_API_URL en Vercel |
| BCV exchange rate required | Sin tasa registrada | Sincronizar desde Operacion o agregar FALLBACK_BCV_RATE |
| Sin enlaces de Admin | Usuario sin rol admin | flask --app wsgi create-initial-admins |
| No aparecen productos | Base de datos sin seed | flask --app wsgi seed-initial-data (si vacia) o fix-prices (si datos existentes) |
| No se ven imagenes | image_url sin asignar en BD de produccion | flask --app wsgi set-product-images (requiere PRODUCT_IMAGE_PUBLIC_URL) |
| Insufficient stock | Movimiento de inventario dejaria negativo | Registrar Ingreso primero |
| PDF no se descarga | WeasyPrint no disponible localmente | En Render (Linux) funciona con formato completo |
| No llegan notificaciones | Bot de Telegram no en grupo o chat ID erroneo | Verificar TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID |
| Cannot read property reset | React recicla event.currentTarget tras await | Ya corregido con formEl?.reset() |
| Invalid header value Credential | Salto de linea en credenciales R2 de Render | .strip() en config.py corrige espacios/saltos |

---

## 13. Comandos de Consola (Render Shell)

| Comando | Accion |
| --- | --- |
| flask --app wsgi create-initial-admins | Crear 2 administradores desde variables ADMIN_1 y ADMIN_2 |
| flask --app wsgi seed-initial-data | Sembrar 6 productos, variantes e inventario inicial |
| flask --app wsgi fix-prices | Corregir precios y eliminar variantes 15 kg en BD existente |
| flask --app wsgi set-product-images | Asignar URLs publicas de R2 a productos (requiere PRODUCT_IMAGE_PUBLIC_URL) |
| flask --app wsgi sync-bcv-rate | Sincronizar tasa BCV desde fuentes oficiales |

---

© 2026 Tostaduria Platform
