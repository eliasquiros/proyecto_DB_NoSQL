# Plan MVP: Proyecto Cupones

**TI4601 – Bases de datos avanzadas · II semestre 2026**
**Entrega:** lunes 30 de noviembre de 2026, 23:00, vía TECDigital (meta interna: subir antes de las 20:00)

Alcance: **solo lo que pide el enunciado**. Nada de login, roles, edición de promociones ni extras.

| Persona | Integrante | Funcionalidades | Puntos |
|---|---|---|---|
| A | _(nombre)_ | F1 Carga, F5 Consulta, Interfaz | 10 + 15 + 5 |
| B | _(nombre)_ | F2 Activar, F3 Promociones activas | 15 + 15 |
| C | _(nombre)_ | F4 Obtener cupón, infraestructura | 20 |

---

## Acuerdo inicial (Sprint 0, 1 hora entre los tres)

Con esto cada quien trabaja solo, sin esperar a los demás.

### MongoDB (base `cupones_db`)

- `promociones`: el JSON tal cual. **No asumir departamentos ni atributos fijos** (en la revisión usarán otros archivos).
- `cupones`: `codigo`, `cliente`, `promocion_id`, `promocion_nombre`, `departamento`, `fecha_obtencion`.

### Redis

- Clave `promo:activa:{id}`: un **Hash** con `nombre`, `departamento`, `cupones_disponibles`.
- Su **TTL** es la duración en segundos (minutos × 60). Redis maneja el vencimiento.

### Datos de prueba (para no depender de los demás)

- Catálogo: todos cargan el JSON con `mongoimport --jsonArray` (no esperan la pantalla de A).
- Redis: `HSET` + `EXPIRE` desde `redis-cli`.
- Cupones falsos: insertarlos a mano en MongoDB Compass.

### Regla cuando se agota una promoción

La clave queda con 0 cupones hasta que venza el TTL. La lista de activas oculta las que tienen 0. Así se distingue "vencida" de "sin cupones".

---

## Persona A: Carga y consulta (Mongo)

### Desarrollar

1. **F1 Carga inicial (10 pts)**
   - Página con selector de archivo `.json` y botón "Cargar".
   - Lee el archivo y hace `insert_many` en `promociones`.
   - Muestra "N promociones cargadas".
   - Rechaza archivo vacío o inválido con mensaje claro.
2. **F5 Consulta por departamento (15 pts)**
   - Tabla en pantalla: departamento, total de cupones, clientes distintos.
   - `aggregate` con `$group` por departamento: `$sum: 1` para el total y `$addToSet` de `cliente` (luego `$size`) para clientes distintos.
   - Un cliente con varias promociones del mismo departamento cuenta una sola vez.
3. **Interfaz (5 pts)**
   - `base.html` con barra de navegación, mensajes `flash` y Bootstrap.
   - Archivo compartido: se entrega en la Sprint 0.

### Documentación

- Portada completa, tabla de contenidos con números de página y "Aspectos generales" (software con versiones).
- Pruebas F1 y F5.
- Ensamblaje final y exportación del PDF.

---

## Persona B: Activar y listar promociones (Redis)

### Desarrollar

1. **F2 Activar promoción (15 pts)**
   - Pantalla con un select del catálogo (leído de Mongo), cantidad de cupones y duración en minutos.
   - Al enviar, guarda el Hash en Redis y le pone TTL.
   - Rechaza si la promoción ya está activa (la clave existe con cupones > 0).
   - Rechaza cupones o duración vacíos, 0 o negativos.
2. **F3 Promociones activas (15 pts)**
   - Tabla con nombre, departamento, cupones disponibles y tiempo restante, **todo leído de Redis** (`SCAN promo:activa:*`, `HGETALL`, `TTL`).
   - Oculta las promociones con 0 cupones.
   - Mensaje "No hay promociones activas" si no hay ninguna.
   - Botón "Actualizar".

### Documentación

- Pruebas F2 y F3.

---

## Persona C: Obtener cupón (Mongo + Redis)

### Desarrollar

1. **F4 Obtener cupón (20 pts)**
   - Pantalla donde el cliente escribe su nombre y elige una promoción de la lista de activas (nombre y departamento). C hace su propia lectura de Redis para esa lista, sin depender de B.
   - Validaciones, en este orden:
     1. La clave no existe en Redis → "La promoción ya venció".
     2. El cliente ya tiene cupón de esa promoción en Mongo (`find_one` por `cliente` y `promocion_id`) → "Cliente ya tiene un cupón de esta promoción".
     3. Se descuenta con `HINCRBY ... -1`. Si el resultado es menor que 0, se devuelve con `HINCRBY ... +1` y se muestra "No hay cupones disponibles".
   - Si todo pasa: genera el código (`{id}-{n:04d}`, con `n` = cupones ya emitidos de esa promoción + 1) e inserta el cupón en Mongo con fecha y hora.
   - Muestra el código al cliente.
2. **Infraestructura (Sprint 0)**
   - `docker-compose.yml` (Mongo + Redis).
   - `db.py` con las conexiones.

### Documentación

- Pruebas F4.
- Sección de tareas asignadas y % de cumplimiento (recopila lo que escriba cada integrante).

---

## Documentación (PDF obligatorio)

**Sin documentación la nota es cero. Toda funcionalidad no documentada en "Pruebas de funcionalidad" queda excluida de la revisión.**

### Secciones del PDF y responsables

| Sección | Responsable |
|---|---|
| Portada completa, tabla de contenidos, números de página | A |
| Aspectos generales: software utilizado (con versiones) | A |
| Aspectos generales: tareas asignadas y % de cumplimiento | C (cada quien aporta su texto) |
| Pruebas F1 y F5 | A |
| Pruebas F2 y F3 | B |
| Pruebas F4 | C |
| Ensamblaje y exportación del PDF | A |

### Capturas mínimas por funcionalidad

Todo se muestra en la web (nunca JSON). Cada captura con título, nítida y legible.

| Func. | Capturas mínimas |
|---|---|
| F1 | Colección vacía → pantalla con archivo → mensaje de éxito → colección cargada. Rechazo: archivo inválido. |
| F2 | Redis sin la clave → formulario → éxito → clave con hash y `TTL`. Rechazos: ya activa, datos inválidos. |
| F3 | Lista con varias promociones y su comparación con Redis. Lista tras un vencimiento y sin promociones activas. |
| F4 | Redis antes y después (N a N−1), documento del cupón en Mongo, código mostrado en pantalla. Rechazos: vencida, cliente repetido, sin cupones. |
| F5 | Tabla en la web, incluyendo un caso de cliente con dos promociones del mismo departamento. |

### Entrega

- Nombre del archivo: `NombreApellido-NombreApellido-NombreApellido.pdf` (si no, −5 puntos).
- Solo por TECDigital. No se aceptan otros medios.

---

## Framework (resumido)

**Flask + Jinja2 + Bootstrap 5.** El HTML lo genera el servidor: sin SPA, sin npm, sin CORS.

- **Librerías:** `flask`, `pymongo`, `redis`.
- **Bootstrap:** guardarlo local en `static/` por si en la revisión no hay internet.
- **Bases de datos:** `docker compose up -d` levanta Mongo y Redis.
- **Capturas de BD:** MongoDB Compass y RedisInsight (o `redis-cli`).

```
proyecto/
├── docker-compose.yml
├── requirements.txt
├── run.py
└── app/
    ├── __init__.py      # crea la app y registra las rutas
    ├── db.py            # conexiones a Mongo y Redis
    ├── templates/       # base.html + una carpeta por función
    ├── static/          # Bootstrap local
    ├── carga.py         # A: F1
    ├── reportes.py      # A: F5
    ├── activar.py       # B: F2
    ├── activas.py       # B: F3
    └── cupones.py       # C: F4
```

Cada persona edita solo sus archivos y trabaja en su propia rama de Git, para evitar conflictos.

---

## No olvidar

- Cada integrante debe saber explicar **toda** la app y ambas bases en la revisión presencial (se descuentan 7 o 15 puntos por pregunta fallada).
- Todos deben asistir y llevar equipo y software propios.
- En la revisión se activarán promociones de 1 o 2 minutos y se usarán otros JSON: no hardcodear nada.
- Todo resultado se muestra en la interfaz. Mostrar JSON o CSV pierde el 50 % del puntaje de esa funcionalidad.
