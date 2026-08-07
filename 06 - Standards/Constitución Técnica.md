---
titulo: Constitución Técnica
tipo: norma
estado: aceptado
aprobado: 2026-08-07
version: 1.0
owner: CEO
actualizado: 2026-08-07
adr: [ADR-005, ADR-008]
aliases: [Constitución Técnica, Constitución]
---

# Constitución de Desarrollo — Agencia

> Documento único de referencia técnica. Reemplaza y unifica todos los documentos previos
> de bases, orden, seguridad y UX/UI.
>
> **Stack:** Python 3.11 · FastAPI · React · Next.js · TypeScript · PostgreSQL · Anthropic · AWS
>
> **Versión 2.0**

---

## Los cuatro criterios

Toda regla de este documento existe para sostener uno o más de estos cuatro criterios.
Ante cualquier duda que este documento no resuelva, la decisión correcta es la que mejor
los respeta, en este orden:

| # | Criterio | Qué significa en la práctica |
|---|---|---|
| 1 | **Seguro** | Un error no expone datos. Un atacante no escala privilegios. Un bug no borra información. |
| 2 | **Escalable** | Agregar la próxima feature no obliga a reescribir lo anterior. |
| 3 | **Legible por un humano** | Quien resuelve un incidente a las 2 AM se orienta solo, sin preguntarle a nadie. |
| 4 | **Ordenado** | Cada cosa está donde corresponde y se llama como corresponde. Sin excepciones informales. |

Cuando dos criterios entran en conflicto, gana el de número más bajo.
Seguridad le gana a escalabilidad. Escalabilidad le gana a legibilidad. Legibilidad le gana a orden.

---

## Índice

**Parte I — Fundamentos**
- [0. Cómo se usa este documento](#0--cómo-se-usa-este-documento)
- [1. Arquitectura](#1--arquitectura)
- [2. Límites de tamaño y modularidad](#2--límites-de-tamaño-y-modularidad)
- [3. Naming y estructura de carpetas](#3--naming-y-estructura-de-carpetas)

**Parte II — Corrección y seguridad**
- [4. Manejo de errores](#4--manejo-de-errores)
- [5. Configuración y secretos](#5--configuración-y-secretos)
- [6. Base de datos](#6--base-de-datos)
- [7. Autenticación y autorización](#7--autenticación-y-autorización)
- [8. Validación de inputs](#8--validación-de-inputs)
- [9. Seguridad en features de IA](#9--seguridad-en-features-de-ia)
- [10. Logging](#10--logging)

**Parte III — Proceso**
- [11. Testing](#11--testing)
- [12. Deploy](#12--deploy)
- [13. Git y unidad de trabajo](#13--git-y-unidad-de-trabajo)
- [14. Formato y linting](#14--formato-y-linting)
- [15. Trabajo con IA](#15--trabajo-con-ia)
- [16. Documentación por proyecto](#16--documentación-por-proyecto)

**Parte IV — Interfaz**
- [17. UX/UI](#17--uxui)

**Anexos**
- [Checklists ejecutables](#anexos--checklists-ejecutables)

---

# Parte I — Fundamentos

---

## 0 · Cómo se usa este documento

### 0.1 Qué es

La constitución técnica de la agencia. Es la fuente única de verdad sobre cómo se desarrolla.
Todo proyecto — SaaS, sistema para cliente o herramienta interna — nace desde acá.

### 0.2 Jerarquía de reglas

Cuando hay conflicto entre fuentes, este es el orden de precedencia:

```
1. Esta constitución
2. CLAUDE.md del proyecto        ← ajusta y especifica, nunca contradice
3. DECISIONES.md del proyecto    ← registra excepciones puntuales con su justificación
```

Una regla de este documento solo se rompe si la excepción queda escrita en `DECISIONES.md`
con fecha, motivo y alcance. **Una excepción no documentada es un error, no una decisión.**

### 0.3 Tipos de producto

No todas las secciones aplican a todos los productos. Cada proyecto declara su tipo
en `ARCHITECTURE.md` y eso define qué se le exige.

| Tipo | Características | Secciones que no aplican |
|---|---|---|
| **SaaS público** | Registro abierto, pagos, multi-tenant | — (aplica todo) |
| **Sistema para cliente** | Usuarios provisionados, sin pago in-app | Registro público |
| **Herramienta interna** | Sin multi-tenancy externo, usuarios acotados | Registro público, aislamiento por tenant |

### 0.4 Qué hacer cuando una regla no encaja

No se ignora. Se elige una de tres:

1. **Se cumple** — la opción por defecto.
2. **Se documenta la excepción** en `DECISIONES.md` y se cumple el resto.
3. **Se anota en `DEUDA-TECNICA.md`** si el incumplimiento es temporal y hay intención de corregirlo.

Lo que nunca pasa: descubrir seis meses después que un módulo no sigue las reglas y nadie sabe por qué.

---

## 1 · Arquitectura

### 1.1 Principio

Cada capa tiene una responsabilidad única y no invade la de las demás.
Esta separación es lo que permite cambiar una parte sin romper las otras — es la base
de la escalabilidad y de que el código sea navegable.

### 1.2 Flujo canónico del backend

```
router → service → repository → DB
              ↘ integration → servicio externo
```

**No hay capa de controllers por defecto.** El router recibe y delega; el service tiene toda
la lógica; el repository es el único que toca la base. Una capa intermedia adicional
en un flujo simple agrega indirección sin agregar claridad.

#### Cuándo se agrega un controller

Solo cuando un endpoint necesita **orquestar dos o más services** que no deben conocerse entre sí.
En ese caso el controller coordina la secuencia y no hace nada más.

```
# ✅ Flujo simple — el 90% de los casos
router → service → repository

# ✅ Flujo que justifica un controller
router → controller → ┬→ contact_service   → contact_repo
                      ├→ billing_service   → billing_repo
                      └→ notification_service → integration
```

Si un controller termina teniendo lógica de negocio propia, es un service mal ubicado.

### 1.3 Responsabilidades por capa — backend

| Capa | Hace | No hace |
|---|---|---|
| **Router** | Recibe el request, valida con schema, delega al service | Lógica de negocio, queries, transformaciones |
| **Controller** *(opcional)* | Orquesta varios services | Lógica de negocio propia, acceso a DB |
| **Service** | Toda la lógica de negocio y las reglas del dominio | Conocer HTTP, conocer SQL, conocer el ORM |
| **Repository** | Único punto de acceso a la base de datos | Lógica de negocio, decisiones |
| **Integration** | Wrapper de un servicio externo | Lógica de negocio, decisiones de dominio |
| **Schema** | Validación de entrada y salida | Lógica de negocio |
| **Middleware** | Auth, rate limiting, errores, logging | Lógica de negocio |

#### Lo que nunca debe pasar

```
❌ Un router ejecutando una query
❌ Un service importando FastAPI o devolviendo un status code
❌ Un service armando SQL
❌ Un repository decidiendo si el usuario tiene permiso
❌ Una integration decidiendo qué hacer con la respuesta del servicio externo
```

### 1.4 Responsabilidades por capa — frontend

| Capa | Hace | No hace |
|---|---|---|
| **Pages / App** | Composición de layouts y componentes | Lógica de negocio, llamadas directas a la API |
| **Components** | UI pura y presentación | Fetch, lógica de negocio |
| **Hooks** | Estado, efectos y orquestación de datos | Renderizado |
| **Services** | Llamadas HTTP al backend | Estado, presentación |
| **Store** | Estado global compartido | Lógica de negocio compleja |
| **Types** | Contratos compartidos | — |

### 1.5 Aislamiento entre tenants

En todo producto donde más de una organización o usuario comparte la base de datos,
el identificador de tenant (`empresa_id`, `organizacion_id`, `user_id` según el modelo)
se valida **en el service, en cada operación**.

```python
# ✅ El service verifica que el recurso pertenece al tenant del usuario
async def get_contact(contact_id: UUID, empresa_id: UUID) -> Contact:
    contact = await contact_repo.find_by_id(contact_id)
    if not contact or contact.empresa_id != empresa_id:
        raise AppError("No encontrado", "NOT_FOUND", 404)
    return contact

# ❌ Confiar en que el ID que llegó ya es del tenant correcto
async def get_contact(contact_id: UUID) -> Contact:
    return await contact_repo.find_by_id(contact_id)
```

**El tenant nunca se toma de un parámetro del request.** Se toma siempre del token verificado.
Un `empresa_id` que viaja como query param es un agujero de autorización.

---

## 2 · Límites de tamaño y modularidad

### 2.1 Tabla de límites

Estos números no son sugerencias. Son el umbral donde un archivo deja de ser revisable
por un humano y deja de ser navegable por una IA sin perder contexto.

| Tipo de archivo | Límite |
|---|---|
| Router / Page | **80 líneas** |
| Controller | **100 líneas** |
| Service | **150 líneas** |
| Repository | **100 líneas** |
| Componente React | **150 líneas** |
| Custom Hook | **80 líneas** |
| Schema / Types | **200 líneas** |
| Cualquier otro archivo | **200 líneas** |

### 2.2 Qué hacer cuando un archivo supera su límite

1. **Se propone la división antes de escribir**, no después.
2. La división es por responsabilidad, no por cantidad de líneas — cortar un archivo
   de 300 líneas en dos de 150 sin criterio produce dos archivos peores.
3. Si algo parece imposible de dividir, es señal de que tiene demasiadas responsabilidades juntas.

### 2.3 Regla de una función, un propósito

Cada función hace exactamente una cosa. Si su descripción necesita un "y", se divide.

```python
# ✅ Responsabilidades separadas
async def validate_contact_email(email: str) -> bool:
    """Verifica que el email tenga formato válido y no esté duplicado."""

async def save_contact(data: CreateContactRequest, tenant_id: UUID) -> Contact:
    """Persiste un contacto nuevo."""

async def create_contact(data: CreateContactRequest, tenant_id: UUID) -> Contact:
    """Orquesta la validación y el guardado de un contacto nuevo."""
    if not await validate_contact_email(data.email):
        raise AppError("Email inválido o duplicado", "INVALID_EMAIL", 400)
    return await save_contact(data, tenant_id)

# ❌ Una función que valida, guarda, enriquece, notifica y audita
```

---

## 3 · Naming y estructura de carpetas

### 3.1 Estructura backend — Python / FastAPI

```
backend/
├── main.py                  ← punto de entrada, solo configuración de la app
├── config/
│   └── settings.py          ← única fuente de configuración y variables de entorno
├── routers/                 ← endpoints, sin lógica de negocio
├── controllers/             ← solo si existe orquestación multi-service (ver 1.2)
├── services/                ← toda la lógica de negocio
├── repositories/            ← único punto de acceso a la base de datos
├── integrations/            ← wrappers de servicios externos
├── schemas/                 ← modelos Pydantic de entrada y salida
├── middleware/              ← auth, rate limiting, errores, logging
├── utils/                   ← helpers reutilizables
├── migrations/              ← SQL versionado y numerado
└── tests/                   ← espeja la estructura del proyecto
```

### 3.2 Estructura frontend — React / Next.js

```
frontend/
├── app/                     ← rutas (App Router)
│   ├── (auth)/
│   ├── dashboard/
│   └── layout.tsx
├── components/
│   ├── ui/                  ← genéricos reutilizables (Button, Input, Modal)
│   └── features/            ← específicos de una feature
│       └── contacts/
├── hooks/                   ← custom hooks
├── services/                ← llamadas a la API
│   └── api.ts               ← cliente base con interceptors
├── store/                   ← estado global
├── styles/
│   └── design-system.ts     ← tokens de diseño del producto
├── types/                   ← tipos compartidos
└── utils/                   ← helpers del frontend
```

### 3.3 Convenciones de nombres

#### Python

```python
# Funciones y variables — snake_case, nombre completo, sin abreviar
async def find_contact_by_email(email: str) -> Contact: ...
contact_list = await contact_repo.find_all_by_tenant(tenant_id)

# Constantes — UPPER_SNAKE_CASE
MAX_REQUESTS_PER_DAY = 100

# Clases — PascalCase
class ContactRepository: ...
class CreateContactRequest(BaseModel): ...

# ❌ Abreviaciones que necesitan contexto para entenderse
async def find_ct(em: str): ...
```

#### TypeScript

```typescript
// Componentes — PascalCase
const ContactCard = ({ contact }: ContactCardProps) => { ... }

// Hooks — camelCase con prefijo "use"
const useContactList = (tenantId: string) => { ... }

// Funciones y variables — camelCase, descriptivas
const isEmailValid = (email: string): boolean => { ... }

// Constantes — UPPER_SNAKE_CASE
const MAX_CONTACTS_PER_PAGE = 20

// Tipos e interfaces — PascalCase
type ContactStatus = "active" | "inactive" | "pending"
```

#### Archivos

```
# Python — snake_case
contact_service.py
auth_repository.py

# React / Next.js — PascalCase para componentes, camelCase para el resto
ContactCard.tsx
useContacts.ts
contactService.ts
```

### 3.4 Documentación en el código

**Docstring obligatorio** en toda función de `services/` e `integrations/`.

```python
async def generate_summary(source_text: str, tone: str, variants: int = 2) -> list[str]:
    """
    Genera variantes de resumen a partir de un texto fuente.

    Args:
        source_text: Texto a resumir. Máximo 10.000 caracteres.
        tone: Tono del resumen. Valores: 'formal' | 'directo' | 'amigable'.
        variants: Cantidad de variantes a generar. Default: 2.

    Returns:
        Lista con las variantes generadas, en orden de confianza descendente.

    Raises:
        AppError: code 'AI_UNAVAILABLE' si el proveedor no responde.
        AppError: code 'GENERATION_FAILED' si no se pudo generar contenido válido.
    """
```

**JSDoc obligatorio** en hooks y services del frontend.

```typescript
/**
 * Gestiona la lista de contactos del usuario autenticado.
 *
 * @param tenantId - Identificador del tenant cuyos contactos se cargan.
 * @returns contacts, isLoading, error, createContact, deleteContact.
 */
export const useContacts = (tenantId: string) => { ... }
```

**Comentarios inline** solo cuando explican el *por qué*, nunca el *qué*.

```python
# ✅ Agrega información que el código no puede expresar
# El proveedor devuelve 200 aunque no encuentre filas, por eso chequeamos el array
if not response.data:
    raise AppError("No encontrado", "NOT_FOUND", 404)

# ❌ Repite lo que el código ya dice
# Incrementar el contador
count += 1
```

---

# Parte II — Corrección y seguridad

---

## 4 · Manejo de errores

### 4.1 Formato único de respuesta

Todos los endpoints de todos los productos devuelven errores con la misma forma.
Un cliente que sabe parsear un error sabe parsear todos.

```json
{
  "error": true,
  "message": "Descripción legible para el usuario",
  "code": "SNAKE_CASE_ERROR_CODE"
}
```

### 4.2 Clase base

```python
# utils/errors.py
class AppError(Exception):
    """Error tipado de la aplicación. Lleva mensaje al usuario, código interno y HTTP status."""

    def __init__(self, message: str, code: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
```

### 4.3 Handler global — único punto de captura

```python
# middleware/error_handler.py
async def global_error_handler(request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, AppError):
        logger.warning(exc.message, extra={"code": exc.code, "path": request.url.path})
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": True, "message": exc.message, "code": exc.code},
        )

    # Error inesperado — se loguea completo, se devuelve genérico
    logger.error("Error inesperado", extra={"error": str(exc), "path": request.url.path})
    return JSONResponse(
        status_code=500,
        content={"error": True, "message": "Error interno del servidor", "code": "INTERNAL_ERROR"},
    )
```

### 4.4 Códigos de error — convención

- `UPPER_SNAKE_CASE`, en inglés, estables en el tiempo
- El código es contrato con el frontend: **no se renombra** sin actualizar el consumidor
- El catálogo de códigos del proyecto vive en `ARCHITECTURE.md`

```python
raise AppError("Contacto no encontrado", "CONTACT_NOT_FOUND", 404)
raise AppError("Email duplicado", "DUPLICATE_EMAIL", 409)
raise AppError("Límite diario alcanzado", "USAGE_LIMIT_EXCEEDED", 429)
```

### 4.5 El mensaje no revela estructura interna

```python
# ✅ Le sirve al usuario, no le sirve a un atacante
raise AppError("No autorizado", "UNAUTHORIZED", 401)

# ❌ Le regala información a quien está sondeando el sistema
raise AppError("El token expiró hace 5 minutos", "TOKEN_EXPIRED", 401)
raise AppError("El usuario no existe en la tabla users", "USER_NOT_FOUND", 401)
```

---

## 5 · Configuración y secretos

### 5.1 Regla absoluta

**Cero secretos en el código fuente.** Ni en comentarios, ni en strings temporales,
ni en archivos de test, ni en fixtures.

### 5.2 Un único módulo lee el entorno

```python
# config/settings.py — el único archivo del proyecto que toca el entorno
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_env: str = "development"
    secret_key: str

    database_url: str

    jwt_secret: str
    jwt_expiration_minutes: int = 60
    refresh_token_expiration_days: int = 30

    ai_api_key: str

    allowed_origins: str

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

```python
# ✅ En cualquier otro módulo
from config.settings import settings
key = settings.ai_api_key

# ❌ Nunca fuera de settings.py
import os
key = os.environ["AI_API_KEY"]
```

### 5.3 Reglas de repositorio

- `.env` en `.gitignore` desde el primer commit del proyecto
- `.env.example` siempre actualizado, con todas las variables y valores falsos del formato correcto
- Si un secreto se commitea por accidente, **se rota inmediatamente**. Borrar el commit no alcanza:
  el valor ya salió del entorno controlado
- En producción los secretos viven en el gestor de variables del hosting o en el parameter store
  del proveedor cloud. **Nunca en archivos en el servidor**

---

## 6 · Base de datos

### 6.1 Migraciones versionadas

El schema nunca se toca a mano en producción.

- Cada cambio es un archivo SQL numerado en `/migrations`, commiteado al repositorio
- El estado de la base es reproducible desde cero corriendo las migraciones en orden
- Los comentarios de la migración explican **el por qué**, no el qué

```sql
-- migrations/001_create_users.sql
-- Tabla base de usuarios.
-- activo=false representa baja lógica: el registro se conserva por integridad referencial
-- y trazabilidad de auditoría.

CREATE TABLE users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       TEXT UNIQUE NOT NULL,
    activo      BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 6.2 La producción deriva — verificar antes de asumir

Con el tiempo el estado real de la base se separa de lo que dicen los archivos de migración:
hotfixes aplicados a mano, cambios desde la consola del proveedor, triggers que nunca se versionaron.

**Antes de escribir cualquier código o prompt que toque el schema, se verifica contra el catálogo vivo.**

```sql
-- Columnas reales de una tabla
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'contacts';

-- Constraints reales (PK, FK, UNIQUE, CHECK) y su comportamiento ON DELETE
SELECT conname, contype, confdeltype, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = 'contacts'::regclass;

-- Triggers activos
SELECT tgname, tgenabled, pg_get_triggerdef(oid)
FROM pg_trigger
WHERE tgrelid = 'contacts'::regclass AND NOT tgisinternal;
```

**Regla:** una implementación escrita sobre lo que dicen las migraciones, sin verificar el catálogo,
es una implementación escrita sobre una suposición.

### 6.3 schema.sql como fuente de reconstrucción

Cada proyecto mantiene un `schema.sql` **generado desde el catálogo vivo**, no concatenando migraciones.
Es el artefacto que se usa para levantar un entorno nuevo o reconstruir la base ante un desastre.

Orden obligatorio de reconstrucción:

```
1. CREATE TABLE          ← todas las tablas, sin constraints entre ellas
2. PRIMARY KEY / UNIQUE  ← constraints internas de cada tabla
3. CHECK                 ← reglas de dominio
4. FOREIGN KEY           ← último, cuando todas las tablas destino existen
5. TRIGGERS / FUNCTIONS  ← incluyendo los de updated_at
```

Los triggers son parte del schema. Un `schema.sql` sin triggers produce una base que parece
correcta y se comporta distinto.

### 6.4 Ejecución de migraciones

- Las migraciones corren **después del deploy del código**, en el orden numérico, sin saltear
- Las corre una persona responsable, verificando el resultado de cada una — no un script silencioso
- Una migración que falla a la mitad se resuelve antes de correr la siguiente
- Toda migración destructiva (DROP, ALTER que pierde datos) exige backup verificado previo

### 6.5 Aislamiento de datos — dos capas

La autorización en la aplicación puede tener bugs. La base de datos es la red de contención.
Según la infraestructura, la segunda capa se implementa distinto:

#### Variante A — Postgres gestionado con auth integrado

Row Level Security activo en toda tabla con datos de usuario.

```sql
ALTER TABLE contacts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "tenant_isolation" ON contacts
  FOR ALL
  USING (tenant_id = current_tenant_id());
```

⚠️ Una tabla sin RLS en este modelo es una tabla que cualquier usuario autenticado puede leer entera.

#### Variante B — Postgres propio / instancia administrada sin auth del proveedor

RLS con `auth.uid()` no existe. La contención se construye así:

1. **Validación de tenant obligatoria en el service**, tomada del token verificado (ver 1.5)
2. **Usuario de base de datos con privilegios mínimos** — la app no se conecta como superusuario
3. **Tests específicos de aislamiento**: por cada recurso, un test que verifique que el tenant A
   no puede leer, modificar ni borrar un recurso del tenant B
4. Opcionalmente, RLS con variable de sesión (`SET LOCAL app.tenant_id`) seteada por el pool
   de conexiones en cada transacción

La variante elegida se declara en `ARCHITECTURE.md`. **No hay opción "ninguna de las dos".**

### 6.6 Queries — nunca concatenar

```python
# ✅ Parámetros
await conn.fetch("SELECT * FROM contacts WHERE email = $1", email)

# ✅ ORM o query builder que parametriza internamente
db.table("contacts").select("*").eq("email", email).execute()

# ❌ SQL Injection garantizado
query = f"SELECT * FROM contacts WHERE email = '{email}'"
```

### 6.7 Borrado lógico como regla

En cualquier tabla referenciada por otras o sujeta a auditoría, **el borrado es lógico**:
un flag `activo=false` más las marcas de baja que el dominio requiera.

Motivos:
- Un `DELETE` sobre una tabla con FK restrictivas falla en producción
- Un `DELETE` con `ON DELETE CASCADE` borra silenciosamente el rastro de auditoría
- La información borrada rara vez es recuperable y casi siempre termina haciendo falta

El borrado físico se reserva para datos efímeros sin valor histórico (sesiones, caches, colas).

### 6.8 ON DELETE CASCADE es lógica de negocio

Un `ON DELETE CASCADE` decide qué se destruye cuando se borra un registro padre.
Eso es una regla de negocio viviendo en el schema.

- Toda cláusula `ON DELETE` distinta de `NO ACTION` se documenta en `ARCHITECTURE.md`
  con la razón por la que existe
- Antes de agregar una, se responde: ¿qué datos desaparecen y quién los va a extrañar?

---

## 7 · Autenticación y autorización

### 7.1 Rutas públicas — lista explícita y corta

Todo lo que no está en la lista requiere autenticación verificada.
La lista es una constante del proyecto, no una condición dispersa en el código.

```python
PUBLIC_ROUTES = [
    "/health",
    "/api/auth/login",
    "/api/auth/refresh",
]
```

### 7.2 JWT — implementación

```python
ALGORITHM = "HS256"

def create_access_token(user_id: str, tenant_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expiration_minutes)
    payload = {
        "sub": user_id,
        "tenant": tenant_id,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def verify_token(token: str) -> dict:
    """Decodifica y VERIFICA LA FIRMA del token. Nunca decodificar sin verificar."""
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except JWTError:
        raise AppError("No autorizado", "UNAUTHORIZED", 401)
```

**Reglas no negociables:**

- La firma **siempre** se verifica. Un decode sin verificación acepta cualquier token fabricado
- El algoritmo se pasa explícito. Nunca se acepta el que declara el propio token
- El tipo de token se valida: un refresh no se usa como access
- El `tenant` viaja en el token y de ahí lo toma el service. Nunca del request

### 7.3 Hashing de contraseñas

- Contraseñas con **bcrypt**, nunca en texto plano ni con hashes rápidos (MD5, SHA sin KDF)
- Se usa la librería de bcrypt directamente. Las capas de abstracción sobre bcrypt tienen
  historial de romperse silenciosamente entre versiones y dejar el hashing sin funcionar
- Al arrancar el proyecto se verifica con un test que el hash y la verificación funcionan de verdad

### 7.4 Refresh tokens

- Se almacenan **hasheados**, nunca en texto plano
- **Rotación obligatoria**: al refrescar, el token anterior se invalida
- Al cerrar sesión, el refresh token se borra del servidor. Que el cliente lo descarte no alcanza

### 7.5 Autorización — ownership siempre

Estar autenticado no es estar autorizado.

```python
# ✅ Verifica pertenencia y no confirma existencia de recursos ajenos
contact = await contact_repo.find_by_id(contact_id)
if not contact or contact.tenant_id != current_user["tenant"]:
    raise AppError("No encontrado", "NOT_FOUND", 404)   # 404, no 403
```

Devolver 403 sobre un recurso ajeno le confirma al atacante que ese ID existe.

### 7.6 Sesiones

- Expiración por inactividad configurable, cerrada por defecto (valor conservador)
- La expiración se aplica **en el servidor**. Un timer en el frontend no es seguridad
- Cierre de sesión invalida del lado servidor

### 7.7 Desactivación de usuarios

Un usuario que se va **se desactiva, no se borra**: `activo=false` más revocación de sesiones y tokens.
Sus registros históricos y su rastro de auditoría se conservan.

### 7.8 Mensajes genéricos

Todo rechazo de autenticación devuelve el mismo mensaje y el mismo código.
No se distingue entre usuario inexistente, contraseña incorrecta y cuenta desactivada.

---

## 8 · Validación de inputs

### 8.1 Validación en la frontera

Todo input externo se valida **antes** de llegar a la lógica de negocio.
El sistema interno trabaja asumiendo dato limpio.

```python
class CreateContactRequest(BaseModel):
    nombre: str = Field(min_length=2, max_length=100)
    email: EmailStr
    empresa: str | None = Field(default=None, max_length=200)

    @field_validator("nombre", "empresa")
    @classmethod
    def sanitize_text(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return re.sub(r'[<>"\']', "", v).strip()
```

### 8.2 IDs siempre tipados como UUID

```python
# ✅ FastAPI valida y devuelve 422 si no es UUID válido
@router.get("/contacts/{contact_id}")
async def get_contact(contact_id: UUID): ...

# ❌ String sin validar
async def get_contact(contact_id: str): ...
```

### 8.3 TypeScript estricto en el frontend

- `strict: true` en `tsconfig.json`
- `any` prohibido por regla de ESLint
- Los tipos de la API viven en `types/` y son el contrato con el backend

### 8.4 Límite de tamaño de payload

```python
MAX_PAYLOAD_SIZE = 1 * 1024 * 1024  # 1 MB

@app.middleware("http")
async def limit_payload_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_PAYLOAD_SIZE:
        return JSONResponse(status_code=413, content={
            "error": True, "message": "Payload demasiado grande", "code": "PAYLOAD_TOO_LARGE"
        })
    return await call_next(request)
```

### 8.5 Seguridad de la API

#### Headers

```python
response.headers["X-Content-Type-Options"] = "nosniff"
response.headers["X-Frame-Options"] = "DENY"
response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
response.headers.pop("server", None)
```

#### CORS

Lista blanca explícita desde configuración. **Nunca `allow_origins=["*"]` en producción.**

#### Rate limiting diferenciado

```python
@limiter.limit("5/minute")    # login — restrictivo, previene fuerza bruta
@limiter.limit("30/minute")   # búsquedas y escrituras
@limiter.limit("60/minute")   # lecturas
```

#### HTTPS obligatorio

HTTP se rechaza o se redirige con 301. Certificado con renovación automática.

---

## 9 · Seguridad en features de IA

### 9.1 System prompt separado del input

El input del usuario nunca se concatena dentro del system prompt.

```python
response = client.messages.create(
    model=settings.ai_model,
    max_tokens=settings.ai_max_tokens,
    system=SYSTEM_PROMPT,                              # instrucciones del sistema
    messages=[{"role": "user", "content": clean_input}],  # dato del usuario
)
```

### 9.2 Sanitización del input

```python
def sanitize_user_input(user_input: str) -> str:
    """Acota y limpia el input del usuario antes de incluirlo en un prompt."""
    user_input = user_input[:MAX_INPUT_CHARS]

    injection_patterns = [
        r"ignore (all |previous |above )?instructions",
        r"forget (everything|all|previous)",
        r"you are now",
        r"system prompt",
    ]
    for pattern in injection_patterns:
        user_input = re.sub(pattern, "[removido]", user_input, flags=re.IGNORECASE)

    return user_input
```

La sanitización por patrones es una capa, no la defensa completa. La defensa real es que
el modelo no tenga acceso a nada que no debería exponer.

### 9.3 Contenido externo es input no confiable

Todo texto que el modelo procesa y no escribió el usuario directamente —documentos subidos,
emails, páginas, respuestas de APIs— se trata como input hostil.
Ese contenido puede contener instrucciones dirigidas al modelo.

Se marca explícitamente como dato en el prompt y **nunca se le da al modelo capacidad
de ejecutar acciones basándose solo en lo que ese contenido dice.**

### 9.4 Control de costos como vector de ataque

Un usuario que abusa de una feature de IA genera costo real e ilimitado.

```python
MAX_TOKENS_PER_REQUEST = 2000
MAX_REQUESTS_PER_USER_PER_DAY = 100

async def check_usage_limit(user_id: str) -> None:
    if await usage_repo.get_daily_count(user_id) >= MAX_REQUESTS_PER_USER_PER_DAY:
        raise AppError("Límite diario de uso alcanzado", "USAGE_LIMIT_EXCEEDED", 429)
```

Todo endpoint que llama a un modelo tiene límite de tokens, límite de uso por usuario
y rate limiting. Los tres.

### 9.5 El output se valida antes de exponerse

- Se verifica que no filtre el system prompt
- Si se espera estructura (JSON, clasificación), se parsea y valida contra un schema
- Un output que no cumple el formato esperado es un error, no algo que se muestra igual

### 9.6 La IA filtra, no decide

En toda feature donde un modelo procesa información sobre personas o produce una clasificación
con consecuencias, el rol del modelo es **acotar, ordenar o sugerir**. La decisión la toma
una persona.

Esto se refleja en el diseño, no solo en el discurso:

- La interfaz muestra la salida del modelo como sugerencia revisable, no como veredicto
- El material original queda siempre accesible para revisión humana
- Existe un estado explícito para los casos que el modelo no pudo procesar,
  y esos casos van a revisión manual — nunca se descartan por default
- El criterio con el que el modelo clasificó queda registrado y es auditable

---

## 10 · Logging

### 10.1 Qué se loguea

Los logs existen para diagnosticar. Un log que nadie lee es ruido; un log que falta cuando
algo se rompe es un incidente sin resolver.

```python
# ✅ Eventos de negocio y anomalías
logger.info("Usuario registrado", extra={"user_id": user_id})
logger.warning("Intento de login fallido", extra={"ip": ip, "email": email})
logger.warning("Rate limit excedido", extra={"ip": ip, "endpoint": endpoint})
logger.error("Error en webhook", extra={"error": str(e), "reference": ref})

# ❌ Ruido
logger.info("Entrando a la función get_contacts")
logger.info("Query ejecutada correctamente")
```

### 10.2 Niveles

| Nivel | Cuándo |
|---|---|
| `INFO` | Eventos de negocio relevantes |
| `WARNING` | Anomalías que no rompen el sistema: login fallido, rate limit, validación rechazada |
| `ERROR` | Algo falló y necesita atención humana |
| `DEBUG` | Solo desarrollo local. Nunca en producción |

### 10.3 Formato estructurado

JSON con `timestamp`, `level`, `message`, `module` y los campos de contexto en `extra`.
El log tiene que ser consultable, no solo legible.

### 10.4 Lo que nunca se loguea

- Contraseñas, en cualquier forma
- Tokens completos — como máximo primeros y últimos 4 caracteres
- API keys
- Datos personales sensibles en texto plano

### 10.5 Regla de oro

> Si un log no ayuda a responder **qué pasó, cuándo y con quién**, no tiene razón de existir.

---

# Parte III — Proceso

---

## 11 · Testing

### 11.1 Qué se exige

No se pide cobertura total. Se pide que **nada que sostenga el negocio se rompa en silencio**.

Tres niveles, todos obligatorios:

| Nivel | Qué cubre |
|---|---|
| **Flujos críticos** | Autenticación, autorización, el flujo core del producto |
| **Regla de negocio nueva** | Toda lógica con ramificación estrenada en el proyecto |
| **Aislamiento** | Que un tenant no acceda a datos de otro |

### 11.2 Flujos críticos — siempre testeados

```python
# Autenticación
async def test_login_success(): ...
async def test_login_wrong_password(): ...
async def test_protected_endpoint_without_token(): ...
async def test_expired_token_is_rejected(): ...
async def test_tampered_token_signature_is_rejected(): ...

# Autorización
async def test_user_cannot_access_other_tenant_resource(): ...
async def test_deactivated_user_cannot_authenticate(): ...

# Core del producto — varía por proyecto
async def test_[flujo_principal]_success(): ...
async def test_[flujo_principal]_with_invalid_input(): ...
```

### 11.3 Piso por módulo nuevo

Todo service nuevo entra con al menos:

1. Un test del camino feliz
2. Un test por cada rama de error que el service puede levantar
3. Un test de aislamiento si el service toca datos de tenant

Un service sin tests no se mergea. No es una recomendación: es la condición de entrada.

### 11.4 Principio del fake

> **Un test solo prueba lo que su fake puede desmentir.**

Un fake que siempre devuelve lo mismo no valida nada — solo confirma que el código corre.
Todo fake tiene que poder:

- **Devolver estados distintos** — encontrado, vacío, parcial
- **Contar llamadas** — para verificar que se llamó, cuántas veces y con qué argumentos
- **Lanzar excepciones** — para probar el camino de error

```python
class FakeContactRepo:
    def __init__(self, result=None, raises=None):
        self.result = result
        self.raises = raises
        self.calls = []

    async def find_by_id(self, contact_id):
        self.calls.append(contact_id)
        if self.raises:
            raise self.raises
        return self.result
```

Si el test pasa igual cambiando el fake por otro que devuelve cualquier cosa, el test no sirve.

### 11.5 Validación del contrato con la base

Los errores de sintaxis en queries, nombres de columna y sintaxis de embeds no los detecta
el linter ni el tipado: aparecen en runtime, en producción.

Cada proyecto incluye un **test validador de schema** que recorre las queries definidas
y verifica que las tablas, columnas y relaciones que nombran existan en el catálogo.
Es barato de escribir y ataja una clase entera de bugs.

### 11.6 Regla de deploy

Los tests pasan antes de cada deploy. **Si un test falla, el deploy no sale.**
Un test que "falla siempre pero sabemos por qué" se arregla o se borra — no se ignora.

---

## 12 · Deploy

### 12.1 Principio

El deploy es documentado, repetible y no depende de pasos manuales que solo alguien conoce.

### 12.2 Infraestructura mínima por producto

```
├── Cómputo         ← servicio de la aplicación (contenedor o instancia)
├── Base de datos   ← instancia gestionada, con backups automáticos
├── Almacenamiento  ← archivos estáticos y backups
├── Logs y alertas  ← centralizados, con alerta configurada sobre errores 5xx
└── DNS             ← dominio y certificado
```

### 12.3 Variables de entorno en producción

Se configuran en el gestor de variables del servicio o en el parameter store del proveedor.
**Nunca en archivos `.env` en el servidor.**

### 12.4 Auditoría de dependencias

```bash
pip-audit --fail-on-vuln     # backend
npm audit                    # frontend
```

- Versiones **exactas** en `requirements.txt` — un rango abierto instala un CVE sin que nadie lo note
- Revisión mensual: auditar, actualizar lo que tenga CVE, eliminar lo que ya no se usa,
  correr la suite completa después

### 12.5 Limitaciones de la plataforma

Antes de elegir dónde corre cada parte, se verifica que la plataforma soporte lo que el
producto necesita. En particular: tareas en background, procesos largos, timeouts de request
y persistencia de archivos entre invocaciones.

Una limitación de plataforma conocida se documenta en `ARCHITECTURE.md` junto con la
estrategia para cuando el volumen la vuelva bloqueante.

### 12.6 Checklist de deploy

```
[ ] Tests críticos pasando
[ ] Variables de entorno configuradas en el entorno destino
[ ] pip-audit sin vulnerabilidades high ni critical
[ ] npm audit sin vulnerabilidades high ni critical
[ ] Backup de la base verificado (no solo "activado")
[ ] Código deployado
[ ] Migraciones ejecutadas en orden, verificando cada una
[ ] HTTPS con certificado válido
[ ] Logs llegando al destino centralizado
[ ] Alerta de errores 5xx activa
[ ] Smoke test manual del flujo principal
```

---

## 13 · Git y unidad de trabajo

### 13.1 El commit es la unidad de trabajo

Cada commit es un cambio completo y coherente. Si incluye tres cosas distintas,
tenían que haber sido tres commits.

### 13.2 Refactor y fix nunca en el mismo commit

Esta regla es la más violada y la que más caro sale.

Cuando un commit mezcla un arreglo funcional con una reorganización de código,
el diff se vuelve ilegible: no se puede distinguir qué cambió el comportamiento
de qué solo cambió de lugar. Si algo se rompe después, no hay forma de revertir
una parte sin la otra.

```bash
# ✅ Dos commits
fix: corregir cálculo de vencimiento cuando el mes tiene 31 días
refactor: extraer lógica de fechas a util propio

# ❌ Un commit imposible de revisar y de revertir
fix: arreglar vencimientos y reorganizar el service
```

Lo mismo aplica a: renombrar mientras se arregla, reformatear mientras se agrega,
y "aprovechar que estoy acá".

### 13.3 Formato de commits

```
tipo: descripción corta en presente e imperativo

feat:     nueva funcionalidad
fix:      corrección de bug
refactor: cambio de código que no agrega ni corrige comportamiento
chore:    mantenimiento (deps, config)
docs:     solo documentación
test:     agregar o modificar tests
style:    formato sin cambio de lógica
```

```bash
# ✅
feat: agregar búsqueda de contactos por industria
fix: corregir refresh de token cuando expira en medio de una sesión

# ❌
fix: arreglar bug
update: cambios
wip
```

### 13.4 Revisar el diff antes de commitear

```bash
git diff --staged
```

Se verifica:

```
[ ] No hay secretos ni credenciales
[ ] No hay print() ni console.log() de debug
[ ] No hay archivos tocados fuera del scope de la tarea
[ ] .env no está en el staging
[ ] El diff se entiende sin explicación adicional
```

### 13.5 No romper lo que funciona

Si un módulo funciona y no es parte de la tarea actual, **no se toca**.
"Mejorar de paso" es la causa más común de regresiones inesperadas.

Lo que se detecta y está fuera de scope va a `DEUDA-TECNICA.md` con fecha y descripción.
No se arregla en el momento.

### 13.6 Flujo de ramas

El flujo depende de cuánta gente escribe en el repo. Los dos son válidos; el proyecto declara
cuál usa en su `README.md`.

#### Modo individual — un solo desarrollador

```
main    ← única rama, siempre deployable
```

- Se commitea directo a `main`, con commits atómicos y bien descritos
- La disciplina la sostienen los commits, no las ramas: cada commit tiene que poder
  revertirse solo
- Se abre una rama solo para cambios experimentales o de riesgo alto que pueden abandonarse
- El push a remoto es frecuente — el repositorio remoto es el backup

#### Modo equipo — dos o más desarrolladores

```
main          ← producción, siempre estable
└── develop   ← integración
    ├── feat/nombre-descriptivo
    └── fix/nombre-descriptivo
```

- Nadie pushea directo a `main` ni a `develop`
- El nombre de la rama describe exactamente qué hace
- Pull Request obligatorio hacia `develop`, con al menos un review

**El pasaje de modo individual a modo equipo se hace antes de que entre la segunda persona**,
no después del primer conflicto de merge.

---

## 14 · Formato y linting

### 14.1 Los formateadores automáticos no se corren sobre código existente

**`ruff format` y `prettier` están prohibidos sobre repositorios ya escritos.**

Un formateador reescribe archivos enteros: comillas, saltos de línea, orden de argumentos,
indentación de expresiones. El resultado es un diff de cientos de líneas donde el cambio real
son tres. Eso:

- Hace imposible revisar el commit
- Destruye la utilidad de `git blame`
- Mezcla cambio de formato con cambio de comportamiento, violando la regla 13.2

Si un proyecto arranca de cero y se decide usar formateador, se corre en el commit inicial,
se documenta en `DECISIONES.md` y a partir de ahí forma parte del pipeline desde siempre.
Es una decisión de fundación, no algo que se agrega en la mitad.

### 14.2 Qué sí se usa

#### Backend — Ruff en modo detección

```bash
ruff check .        # detecta, no reescribe
```

```toml
# pyproject.toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = [
    "E",   # errores de estilo
    "F",   # errores de lógica: variables e imports sin usar
    "I",   # orden de imports
    "N",   # naming conventions
    "UP",  # sintaxis moderna de Python
]
ignore = ["E501"]
```

`ruff check --fix` se usa solo de forma acotada, sobre archivos específicos que se están
tocando en la tarea actual, y el resultado se revisa en el diff.

#### Frontend — TypeScript y ESLint

```bash
node_modules/.bin/tsc --noEmit      # verificación de tipos, no compila
npx eslint .                        # detecta, no reformatea
```

```json
// .eslintrc.json — sin el plugin de Prettier
{
  "extends": ["next/core-web-vitals", "plugin:@typescript-eslint/recommended"],
  "rules": {
    "no-unused-vars": "error",
    "no-console": "error",
    "prefer-const": "error",
    "eqeqeq": "error",
    "@typescript-eslint/no-explicit-any": "error",
    "@typescript-eslint/explicit-function-return-type": "warn"
  }
}
```

### 14.3 Pre-commit hooks

Los hooks **verifican, nunca reescriben**.

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.0
    hooks:
      - id: ruff          # sin --fix
```

Verificaciones adicionales del hook:

```
[ ] ruff check pasa
[ ] tsc --noEmit pasa
[ ] eslint pasa
[ ] no hay archivos .env en el staging
```

### 14.4 El estilo se sostiene al escribir

Sin formateador automático, la consistencia depende de que el código se escriba bien
desde el principio. Por eso las convenciones de la sección 3 son obligatorias y por eso
el código generado por IA se revisa contra ellas antes de aceptarlo.

---

## 16 · Documentación por proyecto

### 16.1 Documentos obligatorios

Sin estos cinco, el proyecto no está terminado.

| Archivo | Qué contiene | Cuándo se actualiza |
|---|---|---|
| `README.md` | Requisitos, instalación, cómo correr. Máximo una página | Cuando cambia el setup |
| `ARCHITECTURE.md` | Decisiones de arquitectura y su justificación | Cuando se toma una decisión estructural |
| `CLAUDE.md` | Contexto operativo para la IA | Cuando cambia algo relevante del proyecto |
| `DECISIONES.md` | Decisiones cerradas y excepciones a esta constitución | Al cerrar una decisión |
| `DEUDA-TECNICA.md` | Lo que se detectó y se decidió no arreglar ahora | Cada vez que se detecta algo fuera de scope |

### 16.2 README.md

Tres secciones, nada más. Si hay que leer más para levantar el proyecto, el README está roto.

```markdown
# Nombre del Proyecto

Qué hace, en una oración.

## Requisitos
- Python 3.11+
- Node.js 20+

## Instalación
git clone [repo] && cd [proyecto]
cp .env.example .env    # completar variables
[comandos de setup]

## Cómo correr
Backend:  uvicorn main:app --reload
Frontend: npm run dev
Tests:    pytest / npm test

## Flujo de ramas
[individual | equipo]
```

### 16.3 ARCHITECTURE.md

```markdown
# Arquitectura — [Proyecto]

## Tipo de producto
[SaaS público | Sistema para cliente | Herramienta interna]

## Stack elegido y por qué
[Decisiones de stack con su justificación]

## Modelo de aislamiento de datos
[Variante A o B de la sección 6.5, y por qué]

## Catálogo de códigos de error
[Lista de codes del proyecto y su significado]

## Reglas de negocio que viven en el schema
[Cláusulas ON DELETE, triggers, constraints con significado de dominio]

## Limitaciones de plataforma conocidas
[Y la estrategia para cuando dejen de ser tolerables]
```

### 16.4 DECISIONES.md

Toda decisión estructural cerrada se escribe acá. **La decisión que no está escrita
se va a rediscutir**, y se va a rediscutir en el peor momento posible.

```markdown
## [YYYY-MM-DD] Paginación por offset y no por cursor
**Contexto:** volumen esperado bajo, sin scroll infinito en el diseño.
**Decisión:** offset con límite fijo de 20.
**Revisar si:** el volumen supera las 10.000 filas por tenant.
```

### 16.5 DEUDA-TECNICA.md

```markdown
## [YYYY-MM-DD] Emails transaccionales con SMTP directo
**Qué:** el envío usa SMTP sin reintentos ni tracking.
**Por qué no se arregló:** fuera del scope de la tarea actual.
**Impacto si no se arregla:** un fallo de envío pasa desapercibido.
**Prioridad:** media.
```

### 16.6 Documentos de planificación — opcionales

Proyectos con muchas sesiones de trabajo pueden sumar documentos de coordinación:
un plan de trabajo por bloques, un registro de sesiones, una bitácora de cambios.

Son útiles y recomendables en proyectos largos, pero **no son obligatorios**.
Lo que sí es obligatorio: si existen, se mantienen actualizados.
Un plan de trabajo desactualizado es peor que ninguno, porque la gente lo lee y toma
decisiones sobre información falsa.

---

# Parte IV — Interfaz

---

## 17 · UX/UI

### 17.1 Principios

**Claridad sobre creatividad.** Una interfaz que sorprende pero confunde es un mal diseño.

**El usuario nunca debería preguntarse qué hacer.** Si alguien tiene que pensar más de dos
segundos cuál es su próximo paso, la interfaz falló.

**Consistencia genera confianza.** Un botón primario siempre se ve igual.
Un error siempre aparece en el mismo lugar.

**Responsive no es opcional.** No "funciona en mobile" — se ve y se usa impecable en mobile.

### 17.2 Perfil de usuario

Los productos se diseñan para personas con bajo conocimiento técnico que tienen que poder
usarlos sin ayuda externa. Toda decisión de interfaz se evalúa contra ese estándar.

### 17.3 Stack

**Tailwind CSS** para estilos, espaciado y responsive.
**Shadcn/ui** para componentes: no es dependencia instalada, los componentes se copian al
proyecto y se modifican libremente. Control total del código y sin actualizaciones que rompan
el diseño.

```bash
npx create-next-app@latest [proyecto] --typescript --tailwind
npx shadcn-ui@latest init
npx shadcn-ui@latest add button input dialog table
```

### 17.4 Design system por producto

Un único archivo de tokens por producto. Es el contexto obligatorio de todo prompt de diseño.

```typescript
// styles/design-system.ts
export const designSystem = {
  colors: {
    primary: "#[hex]",
    primaryHover: "#[hex]",
    secondary: "#[hex]",
    background: "#[hex]",
    surface: "#[hex]",
    border: "#[hex]",
    text: {
      primary: "#[hex]",
      secondary: "#[hex]",
      disabled: "#[hex]",
    },
    status: {
      success: "#22c55e",
      warning: "#f59e0b",
      error: "#ef4444",
      info: "#3b82f6",
    },
  },
  typography: {
    fontFamily: "[fuente]",
    sizes: {
      xs: "0.75rem", sm: "0.875rem", base: "1rem", lg: "1.125rem",
      xl: "1.25rem", "2xl": "1.5rem", "3xl": "1.875rem",
    },
  },
  spacing: {
    xs: "4px", sm: "8px", md: "16px", lg: "24px",
    xl: "32px", "2xl": "48px", "3xl": "64px",
  },
  borderRadius: { sm: "4px", md: "8px", lg: "12px", full: "9999px" },
}
```

Los tokens se extienden en `tailwind.config.ts` para que estén disponibles como utilidades.

### 17.5 Los cuatro estados — siempre implementados

Todo componente que carga datos implementa los cuatro. No hay excepción.

```tsx
if (isLoading) return <ContactListSkeleton />

if (error) return (
  <ErrorState
    title="No pudimos cargar tus contactos"
    description="Hubo un problema al conectar con el servidor."
    action={<Button variant="secondary" onClick={refetch}>Reintentar</Button>}
  />
)

if (contacts.length === 0) return (
  <EmptyState
    icon={<UsersIcon />}
    title="Todavía no tenés contactos"
    description="Agregá tu primer contacto para empezar."
    action={<Button onClick={openCreateModal}>Agregar contacto</Button>}
  />
)

return <ContactList contacts={contacts} />
```

Una pantalla sin estado de error deja al usuario mirando un vacío sin saber si el sistema
está roto o si no tiene datos.

### 17.6 Lenguaje de la interfaz

```
# ✅ Claro
"Guardando tus cambios..."
"¡Listo! Tu cuenta está activada."
"Algo salió mal. Intentá de nuevo en unos minutos."

# ❌ Técnico
"Procesando request..."
"200 OK — Operación completada"
"Error 500: Internal Server Error"
"No se encontraron registros en la base de datos"
```

Ningún mensaje de error crudo del backend llega a la pantalla del usuario.

### 17.7 Feedback inmediato

| Acción | Feedback |
|---|---|
| Click en "Guardar" | Botón con spinner + "Guardando..." |
| Guardado exitoso | Toast: "Cambios guardados" |
| Guardado fallido | Toast: "No se pudo guardar. Intentá de nuevo." |
| Borrar algo | Modal de confirmación previo |
| Subir archivo | Barra de progreso visible |

### 17.8 Formularios

Es el punto de mayor fricción para usuarios no técnicos.

```tsx
// 1. Labels siempre visibles — nunca solo placeholder
<Input label="Nombre de la empresa" placeholder="Ej: Acme S.A." />

// 2. Validación mientras escribe, no recién al enviar
<Input label="Email" onChange={validateEmail} error={emailError} />

// 3. Errores específicos y accionables
error="El email debe tener el formato nombre@empresa.com"   // ✅
error="Email inválido"                                       // ❌

// 4. Campos obligatorios marcados, con nota al pie
<label>Nombre <span className="text-red-500">*</span></label>

// 5. El botón describe la acción
<Button>Crear cuenta</Button>   // ✅
<Button>Enviar</Button>         // ❌
```

### 17.9 Acciones destructivas

Siempre confirmación previa que explica exactamente qué va a pasar.

```tsx
<ConfirmDialog
  title="Eliminar contacto"
  description="Vas a eliminar a Juan Pérez de tus contactos. Esta acción no se puede deshacer."
  confirmLabel="Sí, eliminar"
  confirmVariant="destructive"
  cancelLabel="Cancelar"
/>
```

El texto nombra el objeto concreto, no dice "este elemento".

### 17.10 Responsive

**Mobile-first.** Los estilos base son para mobile y se expanden con prefijos.

```tsx
// ✅
<div className="flex flex-col gap-4 md:flex-row md:gap-6 lg:gap-8">

// ❌ Desktop-first — propenso a bugs en mobile
<div className="flex flex-row gap-8 sm:flex-col sm:gap-4">
```

| Breakpoint | Ancho mínimo | Dispositivo |
|---|---|---|
| base | 0px | Mobile portrait |
| sm | 640px | Mobile landscape |
| md | 768px | Tablet |
| lg | 1024px | Desktop chico |
| xl | 1280px | Desktop |
| 2xl | 1536px | Desktop grande |

**Touch targets mínimo 44×44px.** Es el error más común en mobile.

```tsx
<button className="min-h-[44px] min-w-[44px] px-4 py-3">Guardar</button>
```

En mobile: navegación colapsada, tablas con scroll horizontal o vista de cards,
grillas de una columna.

### 17.11 Estructura de página estándar

```tsx
<PageLayout>
  <PageHeader
    title="Contactos"
    description="Gestioná todos tus contactos desde acá"
    action={<Button onClick={openCreateModal}>+ Agregar contacto</Button>}
  />
  <FiltersBar>
    <SearchInput placeholder="Buscar por nombre o empresa..." />
    <FilterSelect label="Industria" options={industryOptions} />
  </FiltersBar>
  <DataTable data={contacts} columns={contactColumns} isLoading={isLoading} />
</PageLayout>
```

Reglas para tablas: columnas con ancho definido para evitar saltos al cargar,
acciones por fila solo las más usadas, paginación visible a partir de 20 registros.

### 17.12 Flujos de varios pasos

```
1. Máximo 5 pasos
2. Cada paso tiene un título que explica qué se está configurando
3. El progreso siempre visible: dónde está y cuánto falta
4. Guardado automático entre pasos — si cierra y vuelve, retoma donde estaba
5. El último paso es un resumen antes de confirmar
6. Los pasos opcionales se marcan como opcionales
```

### 17.13 Ayuda contextual

| Elemento | Cuándo | Cuándo no |
|---|---|---|
| **Tooltip** | Explicar un ícono o término técnico | Información crítica |
| **Helper text** | Formato esperado de un campo | Repetir el label |
| **Inline info** | Contexto antes de una acción | Texto largo |
| **Modal de ayuda** | Explicaciones extensas | Confirmaciones simples |
| **Empty state** | Primera vez en una sección | Rellenar espacio |

### 17.14 Navegación

```
1. El item activo siempre visualmente destacado
2. Breadcrumb cuando hay más de 2 niveles de profundidad
3. En mobile: menú colapsado o navegación inferior
4. Máximo 7 items en la navegación principal — si hay más, se agrupan
5. Acciones destructivas (cerrar sesión, eliminar cuenta) al final y separadas
```

### 17.15 Accesibilidad mínima

No es solo para usuarios con discapacidad: mejora la experiencia de todos y es lo que
separa un producto profesional de un prototipo.

```tsx
// Imágenes con alt descriptivo, vacío si son decorativas
<img src={logo} alt="Logo de Acme S.A." />
<img src={decorative} alt="" />

// Botones con texto o aria-label
<Button aria-label="Eliminar contacto Juan Pérez"><TrashIcon /></Button>

// Labels asociados a sus inputs
<label htmlFor="email">Email</label>
<input id="email" type="email" />

// Foco visible — nunca outline:none sin reemplazo
<button className="focus-visible:ring-2 focus-visible:ring-primary">
```

Contraste mínimo 4.5:1 para texto normal. No se modifican colores de texto sin verificarlo.

### 17.16 Prompt para IA de diseño

```
Contexto del producto:
- Nombre: [nombre]
- Usuarios: [perfil, nivel técnico]
- Stack: React + Next.js + Tailwind + Shadcn/ui

Design system:
- Primario: [hex]  · Secundario: [hex]  · Fondo: [hex]  · Superficie: [hex]
- Tipografía: [fuente]  · Border radius: [valor]

Qué necesito:
[Componente o pantalla, específico]

Estados a contemplar:
- Cargando: [comportamiento]
- Vacío: [mensaje y acción]
- Error: [mensaje y acción]
- Con datos: [comportamiento]

Responsive:
- Mobile: [comportamiento]
- Desktop: [comportamiento]
```

El output se revisa contra esta sección antes de integrarlo al proyecto.

---

# Anexos — Checklists ejecutables

---

## A · Al arrancar un proyecto nuevo

```
[ ] Estructura de carpetas según sección 3
[ ] config/settings.py como único lector del entorno
[ ] .env en .gitignore, .env.example creado
[ ] utils/errors.py con AppError
[ ] middleware/error_handler.py registrado en main.py
[ ] Middleware de auth con PUBLIC_ROUTES definido
[ ] Headers de seguridad y CORS con lista blanca
[ ] Rate limiting configurado
[ ] Logger estructurado en JSON
[ ] migrations/ con la migración inicial
[ ] Modelo de aislamiento de datos elegido y documentado
[ ] tests/ con los tests de autenticación y autorización
[ ] Test validador de schema
[ ] tsconfig.json con strict:true, ESLint sin plugin de Prettier
[ ] styles/design-system.ts con los tokens del producto
[ ] README.md, ARCHITECTURE.md, CLAUDE.md, DECISIONES.md, DEUDA-TECNICA.md
[ ] Flujo de ramas declarado en el README
```

## B · Antes de cada commit

```
[ ] git diff --staged revisado línea por línea
[ ] El commit hace UNA sola cosa
[ ] No mezcla refactor con fix
[ ] Sin secretos ni credenciales
[ ] Sin print() ni console.log()
[ ] Sin archivos fuera del scope de la tarea
[ ] .env no está en el staging
[ ] Mensaje en formato convencional y descriptivo
```

## C · Al revisar código generado por IA

```
[ ] Respeta la arquitectura por capas
[ ] Sin lógica de negocio en el router
[ ] Sin queries fuera del repository
[ ] Ningún archivo supera su límite de líneas
[ ] Nombres según las convenciones de la sección 3
[ ] Errores con AppError, code y status_code correctos
[ ] Docstrings completos en services e integrations
[ ] Sin print() ni console.log()
[ ] No se tocaron archivos fuera del scope
[ ] No duplica lógica existente
[ ] Los fakes de los tests pueden desmentir
[ ] No se corrió ningún formateador automático
```

## D · Antes de mergear o cerrar una tarea

```
[ ] Ningún archivo supera su límite
[ ] Cada función tiene un solo propósito
[ ] Los nombres se entienden sin contexto extra
[ ] Docstrings completos donde corresponde
[ ] Sin comentarios que repiten el código
[ ] ruff check pasa
[ ] tsc --noEmit pasa
[ ] eslint pasa
[ ] Tests nuevos escritos y pasando
[ ] .env.example actualizado si hay variables nuevas
[ ] DECISIONES.md actualizado si se cerró alguna decisión
[ ] DEUDA-TECNICA.md actualizado si quedó algo pendiente
```

## E · Seguridad antes de deploy

```
[ ] Ningún secreto hardcodeado
[ ] .env no commiteado
[ ] .env.example completo
[ ] pip-audit y npm audit sin high ni critical
[ ] Aislamiento de datos activo según el modelo declarado
[ ] Todos los endpoints nuevos requieren auth o están en PUBLIC_ROUTES
[ ] Los recursos verifican ownership, no solo autenticación
[ ] El tenant se toma del token, nunca del request
[ ] La firma de los JWT se verifica siempre
[ ] Inputs nuevos con schema Pydantic estricto
[ ] Prompts de IA con system prompt separado del input
[ ] Endpoints de IA con límite de tokens y de uso por usuario
[ ] Rate limiting en los endpoints nuevos
[ ] CORS sin allow_origins=["*"]
[ ] Los errores no revelan información interna
[ ] Los logs no incluyen passwords, tokens ni API keys
```

## F · UX/UI antes de deploy

```
[ ] Los cuatro estados implementados en todo componente que carga datos
[ ] Verificado en 375px, 768px y 1280px
[ ] Sin jerga técnica ni errores crudos del backend en pantalla
[ ] Formularios con labels visibles, validación en vivo y errores accionables
[ ] Acciones destructivas con confirmación que nombra el objeto
[ ] Los botones describen la acción
[ ] Touch targets de 44×44px mínimo
[ ] Íconos sin texto con aria-label o tooltip
[ ] Contraste mínimo 4.5:1
[ ] Item activo de navegación destacado
[ ] Flujos de varios pasos guardan progreso
[ ] Toast de feedback después de cada acción importante
```

## G · Deploy

```
[ ] Tests críticos pasando
[ ] Variables de entorno configuradas en destino
[ ] Auditorías de dependencias limpias
[ ] Backup de la base verificado
[ ] Código deployado
[ ] Migraciones ejecutadas en orden, verificando cada una
[ ] HTTPS con certificado válido
[ ] Logs llegando al destino centralizado
[ ] Alerta de errores 5xx activa
[ ] Smoke test manual del flujo principal
```

---

*Agencia · Constitución de Desarrollo · Versión 2.0*
*Stack: Python · FastAPI · React · Next.js · TypeScript · PostgreSQL · Anthropic · AWS*
