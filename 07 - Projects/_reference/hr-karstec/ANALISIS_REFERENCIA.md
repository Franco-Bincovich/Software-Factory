# Análisis de referencia — repositorio RRHH (HR Karstec)

> Lectura descriptiva de un desarrollo real, tomado como **referencia de horizonte**: el tipo
> de resultado que una plataforma de desarrollo basada en agentes debería poder producir.
> No es un template, no es una norma y no es una decisión. Es una muestra de uno.
>
> **Alcance:** análisis read-only, 2026-08-01. No se modificó, creó ni borró nada en el
> repositorio. No se ejecutaron tests, builds ni instalaciones.
>
> **Saneamiento:** este informe no contiene credenciales, valores de variables de entorno,
> identificadores de proyecto de proveedores cloud, URLs de despliegue, nombres de personas
> ni datos de negocio. Donde un archivo importaba por su estructura pero tenía contenido
> sensible, se describe la estructura y se omite el contenido.

---

## 0. Verificaciones previas

### 0.1 `.git 2` — la premisa era incorrecta: git **sí** funciona

**El repositorio git es funcional.** Existe un `.git/` real y normal junto al `.git 2`.

| | |
|---|---|
| `git status` | funciona — rama `main`, working tree limpio, con upstream configurado |
| `.git/` | repositorio real, operativo |
| `.git 2/` | **directorio vacío, cero entradas**, con fecha posterior al `.git` |

`.git 2` es un artefacto de copia del Finder, pero **no reemplazó al repositorio**: es una
carpeta vacía que quedó al lado. No interfiere con nada. Git no la mira porque no se llama
`.git`, y el `.git` verdadero está intacto.

**Consecuencia:** el análisis de historial (sección 8) **sí es posible** y está incluido.
No se renombró ni se tocó nada.

### 0.2 `CLAUDE.md` — resumen

Ver la sección **6.2**, que lo trata completo. Es, con diferencia, el archivo más relevante
del repositorio para lo que estamos mirando: 692 líneas escritas específicamente para que un
agente trabaje sobre este código.

### 0.3 Nombre real del proyecto

**El nombre del producto es `HR Karstec`. `RRHH` es el nombre del repositorio y de la
carpeta.** Los dos conviven en todos lados y ninguno reemplaza al otro.

Evidencia, por orden de autoridad:

| Fuente | Qué declara |
|---|---|
| `CLAUDE.md:1` | `# CLAUDE.md — RRHH (HR Karstec)` |
| `docs/README.md:1` | `# HR Karstec — RRHH` |
| `backend/requirements.txt:1` | `# HR Karstec — Backend dependencies` |
| `backend/requirements-dev.txt:1` | `# HR Karstec — Dependencias de desarrollo y testing` |
| `docs/ARCHITECTURE.md:1` | `# Arquitectura — HR Karstec (RRHH)` |
| `frontend/package.json` | `"name": "frontend"` — genérico, no nombra el proyecto |

**Ningún manifiesto de paquete declara el nombre del proyecto.** No hay `package.json` en la
raíz, y `backend/pyproject.toml` fue eliminado a propósito (rompía el build de la plataforma
de deploy, que lo interpretaba como paquete instalable). El único `package.json` es el del
frontend y se llama literalmente `"frontend"`.

**Dónde vive el nombre real: en la documentación, no en la configuración.** Es un dato en sí
mismo sobre cómo está identificado el proyecto.

**Convención sugerida para la carpeta de referencia:** `hr-karstec`.

### 0.4 `migracionAWS/` — qué contiene y en qué estado está

**Es una mezcla de código y documentación. No es infraestructura como código.**

21 archivos, ninguno en producción:

| Tipo | Cantidad | Contenido |
|---|---|---|
| **Documentación** | 4 `.md` | Guía de migración a RDS, README de la carpeta, README del nuevo módulo de auth, y un documento de qué agregar a la configuración |
| **Código Python** | 7 módulos | Cliente PostgreSQL con `asyncpg`, middleware de auth nuevo, dos servicios (auth y tokens), tres repositorios-molde |
| **Migraciones SQL** | 3 archivos | Numeradas 075–077: hash de password, tabla de refresh tokens, recreación de triggers |
| **Bytecode** | 7 `.pyc` | Compilados de Python — ver 10.3 |

**Estado: staging aislado, no ejecutado.** La carpeta existe para escribir el código nuevo
sin tocar el `backend/` que está en producción. Los módulos llevan sufijo `_NEW` justamente
para que no se confundan con los vigentes. La ejecución de la infraestructura queda a cargo
de otra persona.

**No hay infraestructura como código en ningún lado del repositorio.** No existe Terraform,
CloudFormation, CDK, Serverless Framework, Dockerfile ni docker-compose. Lo que hay es un
plan escrito y el código de aplicación que ese plan necesita. El aprovisionamiento es manual.

**Detalle notable:** las migraciones 075–077 viven acá y no en `backend/migrations/`, que va
por la 081. O sea que la numeración de migraciones está **repartida entre dos carpetas** y
no es contigua en ninguna de las dos.

---

## 1. Qué es

Es una plataforma interna de gestión del ciclo de vida del empleado, construida para el
equipo de recursos humanos de una consultora. Cubre el recorrido completo de una persona por
la organización: incorporación, legajo, licencias y ausencias, proyectos y asignaciones,
capacitación, inventario asignado, objetivos, evaluaciones de desempeño, costos de nómina,
y desvinculación con entrevista de salida. Encima de eso hay una capa de reporting —catorce
reportes descargables en PDF y Excel, más nueve indicadores de tablero— y un registro de
auditoría de todo lo que se modifica. Es multiempresa: una sola instalación opera varias
empresas simultáneamente, con un selector que cambia qué se mira sin cambiar sobre qué se
actúa.

Técnicamente es una aplicación web de tres capas convencional —cliente, API, base de
datos— resuelta como dos despliegues independientes: un frontend Next.js y un backend
FastAPI que se comunican por HTTP con una URL absoluta configurada en tiempo de build. No es
un producto vendible ni multi-tenant en el sentido comercial: es una herramienta interna con
tres roles funcionales, operada por un equipo chico. El problema que resuelve no es
técnicamente exótico —es ABM sobre un modelo de datos grande— pero el volumen de reglas
alrededor sí lo es: permisos por sección y acción, aislamiento entre empresas, propiedad de
datos por jerarquía, y trazabilidad de cada cambio.

---

## 2. Stack

### 2.1 Backend

**Declarado en configuración** (`backend/requirements.txt`, versiones exactas y pineadas):

| Dependencia | Versión | Rol |
|---|---|---|
| `fastapi` | 0.115.0 | framework web |
| `uvicorn[standard]` | 0.30.6 | servidor ASGI |
| `pydantic` | 2.9.2 | validación y esquemas |
| `pydantic-settings` | 2.5.2 | configuración desde entorno |
| `supabase` | 2.9.1 | cliente de base de datos, auth y storage |
| `anthropic` | 0.34.2 | cliente del modelo de IA |
| `PyJWT[crypto]` | 2.10.1 | verificación de firma de JWT |
| `python-jose[cryptography]` | 3.3.0 | criptografía de tokens |
| `passlib[bcrypt]` | 1.7.4 | hashing de contraseñas |
| `slowapi` | 0.1.9 | rate limiting |
| `resend` | 2.3.0 | envío de mails |
| `openpyxl` | 3.1.5 | generación de Excel |
| `reportlab` | 4.2.5 | generación de PDF |
| `python-docx` | 1.1.2 | generación de Word |
| `python-multipart` | 0.0.12 | subida de archivos |
| `httpx` | 0.27.2 | cliente HTTP |
| `google-auth-oauthlib` / `google-auth-httplib2` | 1.2.1 / 0.2.0 | OAuth con Google |

`requirements-dev.txt` está **separado a propósito**, con un comentario que explica por qué:
mezclar dependencias de test en producción infló la imagen de deploy y amplió la superficie
de ataque. Declara `pytest>=8.3.0`, `pytest-asyncio>=0.24.0` y re-declara `httpx` para que
los tests sean autocontenidos.

**Runtime:** Python 3.11 (`target-version = "py311"` en `ruff.toml`).

**Herramientas de calidad — confirmado contra los archivos de configuración.** La presencia
de `.ruff_cache/` y `.pytest_cache/` se corresponde con configuración real:

- `backend/ruff.toml` — existe, con `line-length = 100`, reglas `E`/`F`/`I`/`N`/`UP` y
  `ignore = ["E501"]`.
- `backend/pytest.ini` — existe, con `asyncio_mode = auto` y `testpaths = tests`.

**Los dos archivos son consecuencia de una restricción de deploy**, no una preferencia: el
`pyproject.toml` original hacía que el builder de Python de la plataforma interpretara el
backend como paquete instalable y abortara el build. Se reemplazó por estos dos archivos
sueltos. Está documentado en `CLAUDE.md`.

**Inferido del código, no declarado:** faltan en `requirements-dev.txt` dos dependencias que
los tests sí usan —`python-docx` está en producción pero se necesita para tests de export, y
no hay `ruff` pineado en ningún requirements—. `CLAUDE.md` advierte que instalar sin
`requirements-dev.txt` produce ~33 fallos que no son del código.

### 2.2 Frontend

**Declarado en `frontend/package.json`:**

| Dependencia | Versión | Rol |
|---|---|---|
| `next` | 16.2.4 | framework, App Router |
| `react` / `react-dom` | 19.2.4 | librería de UI |
| `typescript` | ^5 | tipado |
| `tailwindcss` + `@tailwindcss/postcss` | ^4 | estilos |
| `shadcn` | ^4.6.0 | generador de componentes |
| `@base-ui/react` | ^1.4.1 | primitivas accesibles |
| `lucide-react` | ^1.14.0 | iconografía |
| `next-themes` | ^0.4.6 | tema claro/oscuro |
| `sonner` | ^2.0.7 | notificaciones |
| `class-variance-authority`, `clsx`, `tailwind-merge` | — | composición de clases CSS |
| `xlsx` | ^0.18.5 | lectura/escritura de Excel en cliente |
| `vitest` | ^2.1.9 | tests |
| `eslint` + `eslint-config-next` | ^9 / 16.2.4 | linting |

**Runtime:** Node 20+ según `docs/README.md`.

**Asimetría de estrategia de versionado, y es deliberada:** el backend pinea versiones
exactas con un comentario que dice por qué (*"para evitar CVEs silenciosos"*, con recordatorio
de correr auditoría mensual); el frontend usa rangos `^` para todo salvo `next`, `react`,
`react-dom` y `eslint-config-next`, que están exactos. Las cuatro fijas son justamente las
que definen la compatibilidad del build.

### 2.3 Base de datos

Supabase — PostgreSQL con Auth y Storage integrados, y RLS activo. Tres buckets de Storage
declarados en la documentación de instalación.

**El destino declarado es distinto del actual:** la migración planificada va a AWS con RDS y
S3, accedido por `asyncpg` en vez del cliente de Supabase, y **sin RLS** — la seguridad pasa
a ser enteramente a nivel de aplicación. Ese cambio está a medio construir en `migracionAWS/`.

### 2.4 IA

Anthropic Claude Sonnet, usado en dos lugares: generación de reportes ad-hoc en el backend y
un panel de chat en el frontend. `CLAUDE.md` documenta una regla operativa concreta: usar
siempre el alias del modelo sin fecha, porque un identificador con fecha fue retirado y
empezó a devolver 404. Las dos superficies de IA están **ocultas** hoy: el reporte ad-hoc no
figura en el catálogo y el panel de chat no tiene su clave cargada, por decisión.

---

## 3. Estructura del repositorio

### 3.1 Árbol hasta dos niveles

```
RRHH/
├── .env.example                 71 líneas — 18 variables, con comentarios
├── .gitignore
├── CLAUDE.md                    692 líneas — contexto operativo para agentes
├── .git/                        repositorio real, funcional
├── .git 2/                      directorio VACÍO — artefacto de copia
├── .pytest_cache/  .ruff_cache/ no versionados
│
├── backend/
│   ├── main.py                  entrada, registro de routers y middleware
│   ├── config/                  settings.py — única fuente de configuración
│   ├── routers/                 51 archivos — endpoints, sin lógica
│   ├── services/                106 archivos — lógica de negocio
│   │   ├── export/              8 archivos — motor de exportación (CSV/Excel/PDF/Word)
│   │   └── reportes/            11 archivos — un submódulo por familia de reporte
│   ├── repositories/            59 archivos — único acceso a base
│   ├── schemas/                 39 archivos — Pydantic in/out
│   ├── middleware/              auth · error_handler · security_headers
│   ├── integrations/            supabase_client · anthropic_client
│   ├── utils/                   permisos · errors · logger · rate_limit · empresas_cache · empresa · files
│   ├── db/                      schema.sql (reconstrucción) + README
│   ├── migrations/              82 archivos SQL, numerados hasta 081
│   ├── tests/                   72 archivos (69 test_*.py + 3 helpers)
│   ├── scripts/                 5 archivos — smoke tests y barridos
│   ├── controllers/             VACÍO (solo __init__.py) — ver 3.3
│   ├── ruff.toml  pytest.ini    configuración de calidad
│   ├── requirements.txt  requirements-dev.txt
│   ├── vercel.json  vercel_app.py
│   └── venv/                    no versionado
│
├── frontend/
│   ├── app/                     App Router — 27 rutas de dashboard + login + públicas
│   │   ├── (dashboard)/         grupo de rutas autenticadas
│   │   ├── api/ai/              única ruta de API del propio Next
│   │   ├── login/  cambiar-password/  evaluacion/[token]/
│   ├── components/
│   │   ├── features/            27 subcarpetas, una por dominio
│   │   ├── ui/                  primitivas (Shadcn) + compartidos
│   │   ├── layout/              navegación y estructura
│   │   └── auth/                guardas de ruta
│   ├── services/                42 archivos — cliente HTTP y llamadas por dominio
│   ├── hooks/                   10 archivos
│   ├── types/                   27 archivos
│   ├── lib/  utils/  styles/  public/
│   ├── AGENTS.md  CLAUDE.md     ver 6.3
│   ├── README.md                36 líneas
│   ├── proxy.ts                 middleware de Next
│   └── configs                  next · tsconfig · vitest · eslint · postcss · components.json
│
├── docs/                        23 archivos — ver sección 6
│
└── migracionAWS/                21 archivos — staging de migración, no en producción
    └── backend/                 espeja la estructura de backend/ con sufijos _NEW
```

### 3.2 Criterio de organización — es distinto en cada mitad

**No hay un criterio único, y la diferencia no parece accidental.**

- **Backend: por capa técnica.** `routers/` → `services/` → `repositories/`, con `schemas/`,
  `utils/` e `integrations/` transversales. El dominio aparece en el **nombre del archivo**
  (`vacaciones_service.py`, `empleado_repo.py`), no en la carpeta. Es plano: 106 archivos de
  servicio conviven en un solo directorio, con dos excepciones que sí se agruparon por
  dominio cuando crecieron —`services/reportes/` y `services/export/`.

- **Frontend: por feature.** `components/features/` tiene 27 subcarpetas, una por dominio, y
  `app/(dashboard)/` espeja esas mismas 27 rutas. Las capas técnicas del front
  (`services/`, `hooks/`, `types/`) sí son planas y nombradas por dominio.

- **`migracionAWS/` replica la estructura del backend** dentro de sí mismo, en vez de
  mezclarse con él. El aislamiento es la decisión estructural principal de esa carpeta.

**El punto de contacto entre las dos organizaciones es el nombre del dominio**, que se
repite idéntico a los dos lados: `vacaciones` es una carpeta en el front y un prefijo de
archivo en el back.

### 3.3 `backend/controllers/` está vacío

Contiene únicamente un `__init__.py` de cero bytes. `CLAUDE.md` dice explícitamente
*"NO hay controllers"*. La carpeta es un resto de una estructura anterior que se decidió no
usar; sobrevivió el paquete sin contenido.

---

## 4. Organización del código

### 4.1 Backend — separación de responsabilidades

**El contrato entre capas es explícito y está documentado como norma, no solo practicado:**

| Capa | Responsabilidad | Límite de líneas |
|---|---|---|
| `routers/` | endpoints, sin lógica de negocio | 80 |
| `services/` | lógica de negocio | 150 |
| `repositories/` | único acceso a base de datos | 100 |
| otros | — | 200 |

**Los límites de líneas son una convención declarada con número, no una aspiración.**
`CLAUDE.md` lleva el inventario de qué archivo está sobre el límite, cuál está exactamente en
el límite —donde el próximo cambio obliga a dividir antes de escribir— y qué corte ya está
identificado para cada uno. Es el mecanismo de control de tamaño más concreto que vi en el
repositorio.

**Patrón que se repite: el helper con guión bajo.** Cuando un archivo pasa su límite, lo que
se extrae va a un módulo hermano con prefijo `_`, en la misma carpeta:
`_vacaciones_write.py`, `_costos_write.py`, `_empleados_write.py`, `_onboarding_iniciar.py`.
El prefijo marca "esto es interno de este dominio, no una capa nueva". Hay decenas.

**Un router típico** (leído: `routers/vacaciones.py`) tiene esta forma:
docstring que explica el contrato de la ruta y por qué se monta en ese orden → imports de
esquemas, servicio y utilidades de permisos → un `SECCION` de módulo → una factoría `_svc()`
que instancia el servicio → funciones de endpoint decoradas con
`dependencies=[Depends(require_permission(SECCION, Accion.READ))]`. Sin lógica.

### 4.2 Frontend — separación de responsabilidades

- **`app/`** — solo rutas y composición de página. Las páginas grandes se descomponen en
  componentes de `features/`.
- **`components/features/<dominio>/`** — componentes con conocimiento del dominio. Se
  distingue explícitamente el **orquestador** (tiene estado y datos) del **presentacional**
  (recibe props y no fetchea). Está nombrado así en la documentación.
- **`components/ui/`** — primitivas sin dominio. Incluye componentes generados por Shadcn,
  que la documentación marca aparte para que no cuenten como deuda de tamaño propia.
- **`services/`** — una función por llamada a la API, agrupada por dominio en un archivo.
- **`hooks/`** — estado reutilizable. Límite declarado: 80 líneas. Componentes: 150.

**Patrón repetido: el hook de filtros.** Hay un molde `useFiltros<Modulo>` del que cuelgan
siete hooks concretos, todos con la misma forma: un objeto de filtros **tipado por módulo**
que viaja entero de la UI al servicio, nunca argumentos posicionales. La regla explícita es
que el **mismo tipo** lo consuman el listado y la exportación, y que los dos armen sus query
params con la **misma** función de traducción — para que sea estructuralmente imposible que
un filtro quede implementado en uno solo de los dos.

### 4.3 Configuración

**Una sola fuente, sin excepciones.** `backend/config/settings.py` es un modelo
`pydantic-settings` que se instancia en tiempo de import. La convención declarada es
*"solo vía `settings`, nunca `os.environ` directo"*.

La distinción que hace el modelo es entre **variables sin default** —que rompen el import si
faltan, o sea que el proceso no arranca mal configurado— y **variables con default**. Seis
son obligatorias: URL y dos claves de Supabase, secreto de JWT, clave de Anthropic, clave de
Resend. El resto tiene default seguro.

**Detalle:** una de las obligatorias es la clave del servicio de mail, y la documentación
aclara que el backend no arranca sin ella *aunque hoy ningún módulo envíe mails*.

### 4.4 Manejo de errores

**Un solo tipo y un solo formato de salida.** La convención es
`AppError(message, code, status_code)` en todos lados, y un `global_error_handler` en
`middleware/error_handler.py` que produce el contrato `{error, message, code}` que el
frontend espera.

Ese handler es **el mismo** que arma la respuesta 429 del rate limiter — hecho a propósito,
para que el error de límite no pueda divergir del formato del resto.

Del lado del frontend hay una clase `ApiError` con `code` y `status`, y un conversor que
parsea el body del error y cae a un genérico si no puede. El código del error viaja
end-to-end.

**Regla de diseño de errores que aparece varias veces: el rechazo único.** Cuando hay varias
razones por las que algo puede fallar y distinguirlas filtraría información, todas salen por
el mismo status, el mismo código y el mismo mensaje. Se aplica en la barrera de empresa —
"no existe" y "es de otra empresa" son el mismo 404, nunca un 403— y en la validación de
nonce de OAuth, donde los cuatro motivos posibles dan un error idéntico.

### 4.5 Acceso a datos

**Los repositorios son el único lugar que toca la base.** Ningún servicio ni router accede
directamente. Las 59 clases de repositorio envuelven el cliente de Supabase.

**Dos reglas de acceso que están escritas como permanentes:**

1. **El filtro de aislamiento va en el WHERE de la query, no en una comparación posterior.**
   La forma preferida es que el repositorio acepte el identificador de empresa y lo aplique
   en la consulta — una sola ida a la base, imposible de saltear. Comparar después, en el
   servicio, está admitido solo si el repositorio no lo soporta, y marcado como deuda.

2. **Los ejes de aislamiento se componen por intersección, nunca se reemplazan.** Hay dos
   ejes independientes —la empresa, que aplica a todo, y la propiedad por jerarquía, que
   aplica solo a dos secciones— y la regla es que un filtro nuevo se compone con el eje de
   propiedad, nunca lo esquiva con una condición propia.

**Patrón de resolución de lotes en vez de N+1.** Aparece explícito: los enriquecimientos de
listados hacen un lookup por dimensión en vez de uno por fila, y hay al menos un caso
documentado de haber convertido 201 requests en 2.

### 4.6 Convenciones de nombres

| Ámbito | Convención |
|---|---|
| Archivos backend | `snake_case`, sufijo por capa: `*_service.py`, `*_repo.py`, `*_router` |
| Helpers internos | prefijo `_`: `_scope_filtros.py`, `_audit_payloads.py` |
| Componentes React | `PascalCase.tsx` |
| Hooks | `useAlgo.ts` |
| Servicios front | `snake`/`camel` por dominio: `empleados.ts`, `dashboardEquipo.ts` |
| Tests backend | `test_<tema>.py` |
| Tests frontend | `<archivo>.test.ts(x)`, **junto al código que prueban** |
| Migraciones | `NNN_descripcion.sql`, tres dígitos |
| Código de migración | módulos nuevos con sufijo `_NEW` mientras conviven con los viejos |
| Idioma | **español para el dominio, inglés para lo técnico** — `vacaciones_service`, `empleado_repo`, pero `router`, `service`, `repository`, `schema` |

El idioma mezclado es consistente: el vocabulario del negocio nunca se traduce.

### 4.7 Comunicación entre backend y frontend

**HTTP contra una URL absoluta configurada en tiempo de build**, no un proxy de rutas. Es la
decisión que hace que los dos despliegues sean independientes: el día del cambio de
infraestructura solo cambia esa variable.

El cliente está centralizado en `frontend/services/api.ts` y hace tres cosas:

1. **Arma los headers de autenticación** — token bearer desde la sesión, más un header de
   empresa activa que siempre viaja, con un valor explícito para "todas".
2. **Intercepta el 401 y reintenta con refresh**, con una lista de rutas excluidas del
   interceptor: las de login y refresh, donde un 401 significa credencial inválida y no token
   vencido. Sin esa exclusión, un login con contraseña incorrecta dispararía un refresh y un
   redirect en vez de mostrar el error.
3. **Convierte la respuesta de error al tipo `ApiError`** preservando el código.

**El header de empresa es solo para lectura.** La regla documentada —y nombrada como
principio— es *"mirar: manda el selector · hacer: manda el formulario"*. Las acciones reciben
la empresa como parámetro explícito del body, nunca del header. Hay un caso marcado donde el
principio está violado, en la sección 10.

`frontend/proxy.ts` es un middleware de Next mínimo: deja pasar todo y delega la
autenticación a un guard del lado del cliente.

---

## 5. Testing

### 5.1 Qué existe

| | Backend | Frontend |
|---|---|---|
| Runner | `pytest` | `vitest` |
| Archivos de test | 69 `test_*.py` | 11 `*.test.ts(x)` |
| Helpers de test | 3 (`_postgrest_schema.py`, `_selects_descubiertos.py`, `__init__.py`) | — |
| Cantidad de tests | ~975 según documentación | ~143 según documentación |
| Ubicación | `backend/tests/`, carpeta aparte | junto al archivo que prueban |
| Entorno | — | `node`, **sin jsdom** |

*(Los conteos de tests salen de `CLAUDE.md`; no se ejecutó la suite, por la regla de solo
lectura. Los conteos de archivos sí son verificados.)*

### 5.2 De qué tipo son

**Casi todos son unitarios con dobles de prueba.** No hay tests de integración contra una
base real ni end-to-end automatizados. La documentación lo dice de frente en un caso: los
tests de adjuntos son 11 unitarios con repositorio falso y storage parcheado, y el end-to-end
real **nunca se ejecutó** porque el nombre del bucket está fijo apuntando a producción.

**Lo distintivo: cuatro barridos estructurales.** No prueban una funcionalidad — prueban una
**invariante sobre todo el repositorio**, y por eso cubren automáticamente lo que se agregue
después sin tocar el test:

1. **Paridad listado ↔ exportación.** Recorre las rutas por introspección del framework —no
   una lista escrita a mano— y verifica en las dos direcciones que la exportación acepte todo
   lo que el listado filtra y que no tenga filtros propios inalcanzables desde la interfaz.
2. **Límite de exportación.** Recorre los servicios con exportación y verifica que cada uno
   no solo importe el verificador de límite sino que **lo invoque en el cuerpo de la función**
   — se comprueba inspeccionando el código fuente, porque importar no alcanza.
3. **Navegación ↔ permisos**, en el frontend. Compara la configuración del menú entera contra
   el mapeo de rutas a secciones. Un ítem nuevo sin su mapeo rompe el test.
4. **Validación de nombres de columnas contra el esquema.** Ver abajo.

**Los cuatro llevan "guarda de mínimo"** — una aserción de que el barrido encontró al menos N
elementos. Es una defensa contra el falso verde: si la derivación se rompe, el barrido
devuelve cero elementos y todo pasa sin haber comparado nada.

**Un validador de esquema que ataca una clase entera de bug.** `tests/_postgrest_schema.py`
lee el archivo de esquema SQL y valida una especificación de consulta como lo haría la capa
de acceso a datos, detectando dos fallas que los dobles de prueba no pueden ver: columna
inexistente, y relación ambigua cuando hay más de una clave foránea entre dos tablas. Existe
porque seis reportes se entregaron como completos y nunca funcionaron en producción, con la
suite entera en verde: el doble de prueba aceptaba cualquier especificación de columnas
porque ignoraba el argumento.

### 5.3 Qué cubre y qué no

**Cubre:** lógica de servicios y repositorios, permisos, aislamiento por empresa —hay ~15
archivos de test cuyo nombre contiene `scope` o `ownership`—, auditoría, filtros, límites de
exportación, importación de datos, métricas, y las invariantes estructurales de arriba.

**No cubre:**
- **La mayor parte del frontend.** 11 archivos de test sobre 326 de código. La documentación
  dice explícitamente que el chequeo de tipos sigue siendo la red principal.
- **Interacción de usuario.** Los tests de componente renderizan a markup estático y
  verifican el HTML, no el comportamiento. **No ejecutan efectos**, lo que produjo al menos
  un test que pasaba con el guard de permisos borrado.
- **Integración real con base de datos, storage o servicios externos.**
- **Consultas anidadas fuera de los generadores de reportes** — punto ciego declarado.
- **La coherencia entre el mapa de permisos del frontend y el del backend**, que es espejo
  manual sin test.

### 5.4 Cómo se ejecuta

```
Backend:   cd backend && pytest -q          (requiere venv con AMBOS requirements)
Frontend:  cd frontend && npm test          (= vitest run)
Lint:      cd frontend && npm run lint      (eslint)
Tipos:     node_modules/.bin/tsc --noEmit   (tiene que dar 0)
```

Además hay `backend/scripts/` con cinco archivos de smoke test que se corren a mano.

### 5.5 Configuración de calidad declarada

**`backend/ruff.toml`:**

```toml
line-length = 100
target-version = "py311"

[lint]
select = ["E", "F", "I", "N", "UP"]
ignore = ["E501"]

[format]
quote-style = "double"
indent-style = "space"
```

Impone: errores de estilo, variables e imports sin usar, **orden de imports**, convenciones
de nombres, y actualización a sintaxis moderna de Python. Ignora el largo de línea a nivel
lint porque el formateador lo maneja.

**Hallazgo que importa: la configuración está declarada pero no aplicada.** `CLAUDE.md`
advierte que **el repositorio no está formateado con ruff pese a tener su configuración**, y
que correr el formateador reflowearía archivos enteros — con un caso medido donde un archivo
pasaría de 149 a 253 líneas. Como los límites de tamaño se midieron sobre el estilo actual,
formatear rompería la métrica que gobierna las divisiones. La instrucción es explícita: no
correr el formateador dentro de una sesión de trabajo; adoptarlo es una tarea propia con
re-medición.

**No hay hooks de pre-commit.** No existe `.pre-commit-config.yaml`. `CLAUDE.md` marca
"confirmar si está instalado" como pendiente.

**No hay integración continua.** No existe `.github/`, ni configuración de ningún otro
sistema de CI. Nada de lo anterior corre automáticamente: todo es manual.

---

## 6. Documentación

### 6.1 Qué hay en `docs/`

23 archivos, ~530 KB. Todos Markdown salvo uno. Agrupados por función:

**Estado y trazabilidad — vivos, actualizados en los últimos días:**

| Archivo | Tamaño | Qué responde |
|---|---|---|
| `BITACORA-CAMBIOS.md` | 74 KB | qué cambió por sesión y qué tiene que hacer infraestructura al respecto |
| `ESTADO-VS-COMPROMISO.md` | 44 KB | contraste ítem por ítem entre lo comprometido y lo que el código realmente hace, con evidencia `archivo:línea` |
| `MATRIZ-FILTROS.md` | 40 KB | inventario de qué filtro existe en cada módulo y en cuál de las cuatro capas |
| `Plan de trabajo` | 21 KB | **sin extensión** — el plan vigente, 7 bloques con decisiones cerradas |
| `SMOKE-TEST.md` + `SMOKE-TEST-RESULTADOS.md` | 55 KB | procedimiento y resultados de verificación manual |
| `Resultado_import.md`, `Resultado_nomina_batch.md` | 73 KB | salidas de corridas concretas |

**Normas de trabajo — estables:**
`BASES-DE-DESARROLLO.md` (23 KB) · `ORDEN-Y-LEGIBILIDAD.md` (16 KB) · `SEGURIDAD-PENTEST.md`
(20 KB) · `UX-UI.md` (22 KB). `CLAUDE.md` las llama *"convenciones obligatorias"*.

**Auditorías y análisis:**
`AUDITORIA_TECNICA_HRKARSTEC.md` (53 KB) · `AUDITORIA_HR_KARSTEC.md` (16 KB) ·
`EXTRACCION_NEXIO_PARA_PORTAR.md` (58 KB) · `INVESTIGACION_ROLES.md` (15 KB).

**Documentos declarados obsoletos, conservados a propósito:**
`PLAN_DESARROLLO_AHORA.md` · `PLAN_DESARROLLO_DESPUES.md` · `MODELO_DATOS.md`.

### 6.2 `CLAUDE.md` — el archivo más relevante del repositorio

692 líneas, 88 KB, en la raíz. Está escrito para que un agente trabaje sobre este código, y
es el artefacto de este repositorio que más directamente habla del problema que estamos
mirando. Su forma:

**a. Jerarquía de fuentes de verdad, declarada y ordenada.** No dice "la documentación es la
verdad": establece un orden con el catálogo vivo de la base de datos primero, el archivo de
esquema segundo, y el documento de modelo de datos tercero **y marcado como desactualizado**,
con la regla de que ante contradicción gana el catálogo. Hace lo mismo con el plan de trabajo,
declarando cuál supersede a cuál.

**b. Marca lo obsoleto en vez de borrarlo, y dice para qué sirve igual.** Los dos planes
viejos están señalados como no vigentes pero conservados como *"registro de la intención
original de producto"*, con la instrucción de leerlos como contexto histórico y nunca como
instrucción.

**c. Una regla transversal presentada como el patrón que más caro salió.** *"Un test solo
prueba lo que el fake puede desmentir"*, con una **tabla de las cinco veces que pasó**, cada
una con qué hacía mal el doble de prueba, qué quedó sin probar, y en qué archivo está. De ahí
derivan seis reglas obligatorias sobre cómo construir dobles.

**d. Reglas permanentes distinguidas de estado coyuntural.** Secciones marcadas como
"REGLA PERMANENTE" —el patrón de barrera de empresa, las invariantes de filtros y
exportaciones— separadas de las de "foco actual" y "deuda técnica".

**e. Advertencias contra "correcciones" plausibles.** Varias decisiones contraintuitivas
están documentadas con un *"es a propósito, no lo corrijas"* y el desarrollo de por qué:
headers de rate limit deshabilitados porque habilitarlos rompe el camino de éxito de la
librería; un caché de validación que falla en modo permisivo porque el modo restrictivo
**ensancharía** el acceso en vez de reducirlo; flags de módulo que no pueden ser constantes
literales porque el compilador de tipos colapsaría el tipo y rompería el build.

**f. Inventario de deuda con números medidos y fecha de medición.** Lista de archivos sobre
el límite con su conteo, de archivos exactamente en el límite —donde el próximo cambio obliga
a dividir antes de escribir— y de cortes ya identificados para no re-diagnosticar.

**g. Quince reglas operativas numeradas** sobre cómo trabajar: no modificar fuera del scope,
proponer la división antes de escribir si un archivo excede su límite, diagnóstico read-only
antes de implementar, una tarea atómica por sesión, verificar contra los archivos fuente y no
contra el auto-reporte, y la obligación de escribir la entrada de bitácora en la **misma**
sesión que el cambio — *"si la sesión termina sin su entrada, la sesión no terminó"*.

**h. Los commits los hace una persona, nunca el agente.** Está declarado dos veces.

### 6.3 Documentación de agentes en el frontend

Hay una segunda capa, mínima:

- **`frontend/CLAUDE.md`** — una sola línea: `@AGENTS.md`. Es una referencia, no contenido.
- **`frontend/AGENTS.md`** — 5 líneas, entre marcadores `BEGIN`/`END` que indican que es
  **contenido generado por una herramienta**, no escrito a mano. Advierte que la versión de
  Next.js en uso tiene cambios que rompen respecto de lo que un modelo tendría memorizado, y
  ordena leer la guía dentro de `node_modules` antes de escribir código.

Es un patrón distinto del `CLAUDE.md` de la raíz: allá conocimiento acumulado del proyecto,
acá una advertencia inyectada por el framework sobre su propia versión.

### 6.4 Qué tan actualizada está respecto del código

**Está partida en dos: una capa muy actualizada y una capa muy desactualizada, y el propio
repositorio sabe cuál es cuál — parcialmente.**

**Actualizada y consciente de sí misma.** `CLAUDE.md`, la bitácora, la matriz de filtros y el
contraste estado-vs-compromiso se tocaron en los últimos días, marcan sus propias
desactualizaciones y citan evidencia con archivo y línea.

**Desactualizada y marcada como tal.** `MODELO_DATOS.md` y los dos planes viejos están
señalados explícitamente en `CLAUDE.md` con qué tienen de falso y por qué se conservan.

**Desactualizada y NO marcada — es el hallazgo relevante de esta sección.** Dos archivos
contradicen el código sin que nada lo advierta:

- **`docs/ARCHITECTURE.md`** contradice la realidad en casi todos sus puntos:
  - dice **Next.js 15**; el `package.json` declara 16.2.4.
  - dice *"Multi-tenancy: **no aplica** — la plataforma es para una única empresa"*, cuando
    el sistema entero es multiempresa y el aislamiento entre empresas es la regla de
    seguridad más trabajada del repositorio.
  - declara tres roles que **no existen** en el código (`management`, `empleado`) y una tabla
    de permisos configurables que tampoco.
  - describe una arquitectura de "cuatro agentes especializados de IA" que no se corresponde
    con lo que hay (dos usos puntuales del modelo, los dos ocultos).
  - su tabla de deuda técnica está **vacía**, con un marcador de "se completa a medida que
    avanza el desarrollo".
  - Es el documento al que el README apunta como *"decisiones de arquitectura"*.

- **`docs/CHANGELOG.md`** son 8 líneas: dice *"En desarrollo: S1 — Setup y arquitectura base"*
  y un historial de versiones vacío con *"se completa a partir del primer deploy"*. El
  sistema está en producción y el historial tiene 176 commits.

**`docs/README.md` está parcialmente desactualizado:**
- dice que pytest y ruff se configuran en `backend/pyproject.toml`, archivo que fue eliminado
  y reemplazado por `ruff.toml` + `pytest.ini`.
- dice que las migraciones van de 001 a 074; hay 82 archivos hasta la 081, más tres en la
  carpeta de migración.
- advierte sobre un entorno virtual *"commiteado por error"* que **no está versionado** —
  verificado: cero archivos de esa ruta trackeados.
- su árbol de estructura incluye un `vercel.json` en la raíz que **ya no existe**.

**Deriva menor entre `CLAUDE.md` y el conteo real de archivos** (`CLAUDE.md` / real):
servicios 113/106 · repositorios 54/59 · tests 61/69 · migraciones 79/82. Se mueven en las
dos direcciones, o sea que son mediciones de momentos distintos, no un error sistemático.

---

## 7. Build, entrega y entorno

### 7.1 Cómo se construye y se corre localmente

```
Backend:   cd backend && uvicorn main:app --reload      → puerto 8000
Frontend:  cd frontend && npm run dev                   → puerto 3000
Build:     cd frontend && npm run build                 (next build)
Health:    GET /health, sin autenticación
```

El frontend no necesita configuración de entorno para desarrollo local: la única variable que
consume tiene default a localhost.

**Fricción documentada de entorno**, que es en sí un artefacto interesante — `CLAUDE.md`
dedica una sección a los problemas concretos de operar en dos sistemas operativos: qué
intérprete de Python rompe el import, cuál de dos entornos virtuales es el usable en cada
máquina, por qué invocar el compilador de TypeScript por el atajo habitual baja el paquete
equivocado, cómo hay que citar rutas con corchetes en la shell de Windows para que no se
interpreten como patrón, y por qué hay que borrar el bytecode compilado antes de creer un
fallo de test.

### 7.2 Cómo se despliega

**Plataforma de hosting serverless, con dos proyectos separados** apuntando al mismo
repositorio con distinto directorio raíz. El despliegue se dispara solo al hacer push a la
rama principal.

`backend/vercel.json` declara un único build de Python con `maxDuration: 300` y dos rutas:
`/health` y `/api/(.*)`. No hay `vercel.json` en la raíz — existía y se eliminó porque era
configuración mono-proyecto heredada que rompía el serving.

**Verificación post-despliegue: manual y con orden obligatorio.** Como son dos proyectos que
deployan en paralelo, `CLAUDE.md` documenta una secuencia de cuatro pasos —confirmar que el
backend deployó el commit nuevo, comprobar su health check, confirmar que el frontend
deployó, y recién ahí probar la funcionalidad— con la observación de que si una funcionalidad
nueva devuelve 404, es que el frontend salió antes que el backend y hay que esperar, no tocar
código.

Hay además una lista de "minas ya desactivadas" de despliegue: la integración de git
desconectada que congeló los deploys durante semanas, un archivo de lock duplicado en la raíz
que confundía la inferencia del bundler, y la más traicionera — que con reversión instantánea
activa o auto-asignación de dominios deshabilitada, cada push crea un deployment nuevo que el
dominio no toma, y el síntoma es que arreglás algo, pusheás, y el bug persiste.

### 7.3 Variables de entorno

`.env.example` — 71 líneas con comentarios, **18 variables**. Solo los nombres:

| Grupo | Variables |
|---|---|
| Base de datos y auth | `SUPABASE_URL` · `SUPABASE_ANON_KEY` · `SUPABASE_SERVICE_KEY` |
| Tokens | `JWT_SECRET` · `JWT_EXPIRATION_MINUTES` · `REFRESH_TOKEN_EXPIRATION_DAYS` |
| IA | `ANTHROPIC_API_KEY` |
| Mail | `RESEND_API_KEY` · `RESEND_FROM_EMAIL` |
| OAuth Google | `GOOGLE_CLIENT_ID` · `GOOGLE_CLIENT_SECRET` · `GOOGLE_REDIRECT_URI` |
| Red y entorno | `ALLOWED_ORIGINS` · `APP_ENV` · `FRONTEND_URL` |
| Frontend | `NEXT_PUBLIC_API_URL` · `NEXT_PUBLIC_SUPABASE_URL` · `NEXT_PUBLIC_SUPABASE_ANON_KEY` |

**El archivo está desactualizado respecto de la configuración real.** No declara cuatro
variables que el código y la documentación sí usan: las tres del bloque de endurecimiento
—flag de módulo desactivado, cantidad de saltos de proxy confiables, URI del almacén de
contadores de rate limit— ni la cadena de conexión que agrega la migración. Las tres primeras
tienen default seguro, pero la de saltos de proxy es la que `CLAUDE.md` marca en rojo: un
valor de más colapsa todo el tráfico en un solo contador y deja al equipo entero fuera.

**Un `.env` real nunca se abrió.** El `.gitignore` los excluye correctamente, y los valores
reales viven en el panel de la plataforma de hosting.

### 7.4 Qué está automatizado y qué es manual

| | Estado |
|---|---|
| Despliegue al hacer push | **automatizado** |
| Verificación post-despliegue | manual, con secuencia documentada de 4 pasos |
| Tests | manual |
| Linting y formateo | manual — y el formateador está desaconsejado en sesiones normales |
| Chequeo de tipos | manual, con regla de que tiene que dar cero |
| Migraciones de base | manual |
| Commits | manual, por decisión explícita — nunca los hace el agente |
| Push | manual y desacoplado del commit |
| Integración continua | **no existe** |
| Hooks de pre-commit | **no existen** |
| Aprovisionamiento de infraestructura | manual, sin infraestructura como código |

**Lo único automatizado es el despliegue.** Todo lo que sería una compuerta de calidad
—tests, lint, tipos— depende de que alguien lo corra. La compensación es documental: los
barridos estructurales y el inventario de deuda cumplen parte de esa función, pero solo si
alguien ejecuta la suite.

### 7.5 Qué muestra `migracionAWS/` sobre el destino de infraestructura

**Destino declarado:** de una plataforma gestionada a infraestructura propia — base
PostgreSQL administrada accedida por driver asíncrono nativo en vez del cliente del
proveedor, storage de objetos, y despliegue en contenedores.

**Las decisiones ya cerradas** que la carpeta documenta:
- Se recrean los treinta y seis triggers de marca de tiempo que el archivo de esquema no
  trae.
- **No hay seguridad a nivel de fila en el destino.** Toda la seguridad pasa a ser de
  aplicación. Es el cambio conceptual más grande: hoy hay dos capas, va a quedar una.
- No se carga data de demostración.
- La autenticación se reconstruye entera: hash de contraseñas propio y tabla de refresh
  tokens, en vez del servicio de auth del proveedor.

**Una lista de obstáculos ya identificados para quien ejecute la infraestructura**: tipos de
dato que el driver nuevo devuelve distinto y hay que castear, una clave foránea contra el
esquema de auth del proveedor que bloquea las inserciones y hay que eliminar, una librería de
hashing rota por un cambio de versión de su dependencia, y las variables de entorno nuevas
que tienen que existir del otro lado.

**Lo que la carpeta muestra sobre el estado de la migración: está a nivel de aplicación, no
de infraestructura.** El código para hablar con la base nueva existe y está escrito. La
infraestructura que lo va a correr no está descrita en ningún archivo del repositorio. La
carpeta también contiene un contraste con el changelog de otro proyecto del mismo grupo con
el stack de destino, del que se toman prestadas lecciones —gestión de secretos por servicio
dedicado en vez de valores fijos, opciones de TLS y timeouts del cliente— con una nota de que
la carpeta está limpia de secretos y placeholders, cosa que verifiqué.

---

## 8. Historial

Git funciona, así que esta sección es posible.

| | |
|---|---|
| Commits | **176** |
| Período | 2026-05-02 → 2026-07-30 (~3 meses) |
| Rama | `main` únicamente, con upstream. Sin ramas sueltas |
| Autores | 2 identidades |
| Archivos versionados | 852 |
| Working tree | limpio |

**Distribución por tipo de commit** — formato convencional respetado en los 176:

| Tipo | Cantidad | % |
|---|---|---|
| `feat` | 89 | 51% |
| `fix` | 44 | 25% |
| `docs` | 18 | 10% |
| `refactor` | 14 | 8% |
| `chore` | 8 | 5% |
| `test` | 3 | 2% |

**Distribución temporal:**

| Mes | Commits |
|---|---|
| 2026-05 | 23 |
| 2026-06 | 35 |
| 2026-07 | **118** |

**Qué muestra el patrón sobre cómo se trabajó:**

- **La aceleración es fuerte y tardía.** El último mes concentra el 67% de los commits, más
  que los dos anteriores juntos. Coincide con el período en que `CLAUDE.md` describe cierres
  de bloques completos y ~15 divisiones de archivos en una semana.
- **Uno de cada cuatro commits es un `fix`.** Alta proporción de corrección respecto de
  construcción, consistente con la historia que la documentación cuenta de funcionalidades
  entregadas como completas que no funcionaban en producción.
- **Solo 3 commits de tipo `test`** contra 89 de `feat`, aunque hay 69 archivos de test. Los
  tests entran mayormente **dentro** de los commits de funcionalidad, no como commits
  propios. Es coherente con la regla declarada de "un commit por sub-sesión, no por tarea".
- **Sin ramas.** Trabajo lineal sobre la rama principal, sin pull requests, sin revisión
  entre pares como paso de proceso. La revisión, donde existe, es la que el propio operador
  hace antes de commitear.
- **Los commits los hace una persona a mano, nunca el agente.** Está declarado dos veces en
  `CLAUDE.md`. El historial es entonces un registro de decisiones humanas de agrupamiento,
  no un log automático.
- **Commit y push desacoplados** por decisión: no hay push hasta que se decide.

---

## 9. Artefactos de un proyecto terminado

**Inventario de lo que este repositorio contiene y que tendría que existir en cualquier
proyecto equivalente producido por una plataforma de desarrollo.** Es la respuesta a "qué
entrega un proyecto", derivada de una muestra real.

### 9.1 Código de aplicación

| Artefacto | Presente | Forma en esta muestra |
|---|---|---|
| Punto de entrada del servicio | ✅ | `main.py` con registro explícito de rutas y middleware |
| Capa de exposición (endpoints) | ✅ | 51 archivos, sin lógica de negocio |
| Capa de lógica de negocio | ✅ | 106 archivos |
| Capa de acceso a datos | ✅ | 59 archivos, único punto que toca la base |
| Contratos de entrada/salida | ✅ | 39 esquemas tipados |
| Middleware transversal | ✅ | autenticación, manejo de errores, cabeceras de seguridad |
| Envoltorios de servicios externos | ✅ | aislados en su propia capa |
| Utilidades transversales | ✅ | permisos, errores, logging, rate limit, cachés |
| Interfaz de usuario | ✅ | 27 dominios, rutas espejadas con componentes |
| Cliente HTTP del frontend | ✅ | centralizado, con interceptor de refresh de sesión |
| Tipos compartidos del frontend | ✅ | 27 archivos |

### 9.2 Modelo y evolución de datos

| Artefacto | Presente | Forma en esta muestra |
|---|---|---|
| Esquema completo reconstruible | ✅ | un `schema.sql` que se corre contra base vacía |
| Migraciones versionadas | ✅ | 82 archivos numerados de tres dígitos |
| Documento de qué es fuente de verdad del esquema | ✅ | jerarquía ordenada, con el catálogo vivo primero |
| Procedimiento de reconstrucción documentado | ✅ | con sus límites explícitos |
| Marca de migraciones deprecadas | ✅ | con guard que aborta la ejecución |

**Distinción que esta muestra hace explícita:** el archivo de esquema es para **reconstruir**;
las migraciones son **historial**, y correrlas en orden no reproduce producción de forma
confiable. Son dos artefactos con propósitos distintos, no uno derivado del otro.

### 9.3 Configuración

| Artefacto | Presente | Forma en esta muestra |
|---|---|---|
| Fuente única de configuración | ✅ | un módulo tipado, sin acceso directo al entorno |
| Plantilla de variables de entorno | ⚠️ | existe, **incompleta** — le faltan 4 |
| Distinción obligatorias / con default | ✅ | las obligatorias rompen el arranque si faltan |
| Exclusión de secretos del control de versiones | ✅ | `.gitignore` correcto, verificado |
| Configuración de despliegue | ✅ | declarativa, por servicio |
| Configuración de linting | ✅ | `ruff.toml` |
| Configuración de tests | ✅ | `pytest.ini`, `vitest.config.ts` |
| Configuración de tipos | ✅ | `tsconfig.json` |
| Configuración de build/estilos | ✅ | `next.config.ts`, `postcss.config.mjs`, `components.json` |

### 9.4 Tests

| Artefacto | Presente | Forma en esta muestra |
|---|---|---|
| Suite de tests del backend | ✅ | 69 archivos |
| Suite de tests del frontend | ✅ | 11 archivos, junto al código |
| **Tests estructurales de invariantes** | ✅ | 4, con guarda contra el falso verde |
| Validador de esquema contra consultas | ✅ | lee el SQL y valida especificaciones |
| Helpers de test reutilizables | ✅ | 3 |
| Scripts de smoke test | ✅ | 5, ejecución manual |
| Tests de integración reales | ❌ | ausentes |
| Tests end-to-end | ❌ | ausentes |
| Reporte de cobertura | ❌ | no configurado |

**El artefacto más transferible de esta categoría es el test estructural**: prueba una
invariante sobre todo el repositorio en vez de una funcionalidad, se alimenta por
introspección en vez de una lista escrita a mano, y lleva una guarda de mínimo para que no
pueda pasar en el vacío.

### 9.5 Documentación

| Artefacto | Presente | Forma en esta muestra |
|---|---|---|
| README de instalación y ejecución | ✅ | con requisitos, comandos y estructura |
| Documento de contexto para agentes | ✅ | `CLAUDE.md`, 692 líneas |
| Jerarquía declarada de fuentes de verdad | ✅ | ordenada, con qué gana ante contradicción |
| Bitácora de cambios por sesión | ✅ | con obligación de escribirla en la misma sesión |
| Contraste comprometido vs. real | ✅ | ítem por ítem, con evidencia `archivo:línea` |
| Inventario de deuda técnica | ✅ | con números medidos y fecha de medición |
| Normas de desarrollo vinculantes | ✅ | 4 documentos separados del estado |
| Plan de trabajo vigente | ✅ | con declaración de qué supersede |
| Matriz de cobertura funcional | ✅ | qué existe en cada capa de cada módulo |
| Registro de decisiones de arquitectura | ⚠️ | existe pero **contradice el código** |
| Changelog | ⚠️ | existe pero **vacío** |
| Documento de modelo de datos | ⚠️ | existe, **marcado como desactualizado** |
| Procedimiento de verificación manual | ✅ | con sus resultados registrados |
| Documentación de migración pendiente | ✅ | con decisiones cerradas y obstáculos identificados |

**Lo distintivo de esta muestra:** la documentación **declara su propio grado de confianza**.
Cada documento desactualizado que está marcado como tal sigue siendo útil; los dos que no
están marcados son los únicos que engañan. La diferencia entre esos dos grupos es el hallazgo
más transferible de esta sección.

### 9.6 Operación y entorno

| Artefacto | Presente | Forma en esta muestra |
|---|---|---|
| Endpoint de salud | ✅ | sin autenticación, devuelve estado y entorno |
| Definición de dependencias con versión | ✅ | producción y desarrollo **separadas** |
| Separación prod/dev de dependencias | ✅ | con el motivo escrito en el archivo |
| Procedimiento de verificación post-despliegue | ✅ | manual, con orden obligatorio |
| Registro de fallas de despliegue conocidas | ✅ | "minas ya desactivadas" |
| Scripts de operación | ✅ | 5, en `backend/scripts/` |
| Logging centralizado | ✅ | con prohibición explícita de salida directa a consola |
| Rate limiting | ✅ | por franjas de riesgo, con baseline global |
| Auditoría de cambios | ✅ | a nivel de aplicación, tabla inmutable |
| Infraestructura como código | ❌ | ausente |
| Integración continua | ❌ | ausente |
| Contenerización | ❌ | ausente |
| Observabilidad / métricas | ❌ | ausente |
| Versionado semántico o tags | ❌ | ausente |

### 9.7 Gobierno del trabajo

| Artefacto | Presente | Forma en esta muestra |
|---|---|---|
| Convención de commits | ✅ | formato convencional, respetado en los 176 |
| Reglas operativas para el agente | ✅ | 15 numeradas |
| Límites de tamaño por tipo de archivo | ✅ | con número, y con inventario de quién los viola |
| Decisión de quién commitea | ✅ | explícita: una persona, nunca el agente |
| Registro de decisiones de producto cerradas | ✅ | marcadas "no reabrir" |
| Lista de lo deliberadamente no hecho | ✅ | "al margen por decisión (no tocar)" |
| Advertencias contra correcciones plausibles | ✅ | "es a propósito, no lo corrijas", con el porqué |
| Revisión entre pares | ❌ | sin ramas, sin pull requests |
| Definición de terminado | ⚠️ | implícita en el contraste comprometido-vs-real |

**Las tres últimas filas del bloque anterior son el aporte menos obvio de esta muestra.** Un
repositorio con agentes trabajando encima necesita registrar no solo qué se hizo, sino **qué
se decidió no hacer y por qué**, y **qué parece un error pero no lo es** — porque sin eso,
cada agente nuevo "arregla" lo mismo una y otra vez.

---

## 10. Qué está incompleto o pendiente

Sin juicio de valor: es información sobre cómo se ve un proyecto real en curso.

### 10.1 Marcadores en el código: prácticamente ninguno

**Cero `TODO`, `FIXME`, `HACK` o `XXX` reales** en las 371 fuentes Python y 326 TypeScript.
Los 11 resultados de la búsqueda son todos falsos positivos: la palabra española "TODO"
—como en *"valida TODO lo que se pueda"*, o la constante `ROL_VE_TODO`— coincide con el
patrón en mayúsculas.

**Esto no significa que no haya trabajo pendiente**, sino que el pendiente **no vive en el
código**: vive en `CLAUDE.md`, en el plan de trabajo y en la bitácora. Es una decisión de
dónde poner la información, y bastante deliberada.

### 10.2 Deuda declarada en la documentación

`CLAUDE.md` mantiene una sección de deuda con tres estados: activa, resuelta y "al margen
por decisión". La activa, resumida:

- **Un flujo de importación no registra evento de auditoría**, contra la regla propia de "un
  evento por lote". El flujo hermano sí lo hace.
- **Un punto etiqueta un evento de auditoría con el identificador de empresa del header en
  vez del de la entidad afectada**, violando el principio "mirar/hacer" del propio proyecto.
  La nota aclara que hoy no etiquetó nada mal porque no hay eventos de ese tipo en
  producción, y que se va a volver visible cuando exista una segunda empresa.
- **Una clave foránea apunta a la tabla equivocada**, lo que bloquea dos funcionalidades.
  Marcado con la observación de que migrarla es trivial hoy y cara después.
- **Un mapa de permisos del frontend es espejo manual del backend, sin test que los compare.**
  La divergencia hermana —menú contra guard de ruta— sí tiene test; esta no.
- **El validador de esquema cubre los generadores de reportes, no todo el repositorio.**
  Punto ciego declarado, con instrucción de verificar en producción tras cada despliegue.

### 10.3 Código muerto identificado, no borrado

- **Dos repositorios legacy con cero llamadores**, verificados: aparecen solo en su propio
  archivo, en el esquema y en un comentario de test que dice que son el código muerto.
- **Un componente de frontend huérfano**, cero llamadores.
- **Seis tablas huérfanas** en la base, marcadas para limpiar después del cambio de
  infraestructura.
- **`backend/controllers/`** — paquete vacío de una estructura que se descartó.
- **Un conjunto de tablas de un modelo de evaluaciones anterior**, vacías en producción,
  reemplazadas por un modelo nuevo y conservadas hasta el cambio de infraestructura.

Todo está inventariado y agrupado bajo un bloque de limpieza marcado "no urgente".

### 10.4 Módulos completos apagados a propósito

**Dos módulos con el código entero, a los que se les sacó el punto de entrada.** Ninguno está
borrado.

- Uno está apagado en **backend y frontend** a la vez, por flag de configuración. El router
  no se monta y el regex de rutas públicas está gateado por el mismo flag — las dos cosas, a
  propósito, para que se comporten como una ruta inexistente cualquiera y no delaten que el
  módulo existe. Se reactiva con una variable de entorno, sin tocar código.
- El otro está apagado solo en el **frontend**, con dos flags, uno por archivo. Hacen falta
  los dos: uno devuelve el ítem al menú y el otro deja de redirigir.

**Las rutas siguen navegables y protegidas** a propósito: como no se borraron del router, el
guard de ruta tiene que seguir cubriéndolas.

### 10.5 Funcionalidades a medio hacer

- **La descarga de archivos originales de una importación**: hoy el importador parsea y
  descarta los bytes. Requiere tres cosas —guardar en storage, una migración con la columna
  de ruta, y un endpoint de descarga firmada— y está marcada como "solo hacia adelante": lo
  ya importado no se recupera. Con una nota de que hay que decidir **antes** dónde va a vivir
  el storage, o se hace dos veces.
- **Un bloque entero bloqueado por falta de datos**: las estadísticas comparativas entre
  lotes no son verificables con un solo lote cargado.
- **Un filtro pendiente hasta que existan datos que filtrar**: las columnas están, el
  catálogo está servido por endpoint, pero no hay contenido.
- **Una funcionalidad bloqueada esperando una reunión de definición**, con el mockup ya
  aprobado.

### 10.6 Deuda de tamaño de archivo

Inventariada con números medidos: **38 archivos de frontend sobre el límite de 150 líneas**
—dos de ellos primitivos generados que se excluyen explícitamente— y **6 de backend** sobre
el suyo. Además hay una lista de archivos **exactamente en el límite**, donde el próximo
cambio obliga a dividir antes de escribir, y una lista de cortes ya identificados para no
re-diagnosticar.

### 10.7 Inconsistencias de higiene del repositorio

- **7 archivos de bytecode compilado (`.pyc`) versionados** dentro de `migracionAWS/`. El
  `.gitignore` excluye correctamente los de `backend/`, pero su patrón está anclado a esa
  ruta y no alcanza a la copia de la estructura dentro de la carpeta de migración.
- **`.git 2/`** — el directorio vacío del artefacto de copia.
- **La numeración de migraciones está repartida** entre dos carpetas y no es contigua en
  ninguna.
- **`.env.example` incompleto** respecto de la configuración real: le faltan cuatro
  variables.
- **`AUDITORIA_FUNCIONAL.md`** está en el `.gitignore`, o sea que hay un documento
  deliberadamente fuera del control de versiones.
- **Documentación desactualizada sin marcar** — sección 6.4.

### 10.8 El bloqueante que no es técnico

`CLAUDE.md` abre su sección de foco con una observación que no es sobre el código: la mayor
parte de los módulos está **sin datos cargados** en producción, así que los reportes y
tableros funcionan correctamente pero salen vacíos. Está clasificado explícitamente como
*"no es deuda técnica — es un bloqueante de adopción"*, con una lista de qué avisarle al
equipo usuario antes de entregarles el sistema para que no confundan vacío con roto.

*(Los números concretos de ese diagnóstico son datos de negocio y quedan fuera de este
informe.)*

---

## 11. Qué no pude determinar

**Ejecución.** No corrí tests, builds ni instalaciones, por la regla de solo lectura. Todos
los conteos de **tests que pasan** (~975 backend, ~143 frontend) salen de `CLAUDE.md`, no de
una corrida. Los conteos de **archivos** sí están verificados por mí.

**Cobertura real de tests.** No hay reporte de cobertura configurado y no lo generé. Las
afirmaciones sobre qué cubre y qué no salen de leer los nombres de archivo, la documentación
y una muestra del código — no de una medición.

**Estado de producción.** No accedí a ningún entorno desplegado ni a ninguna base. Todo lo
que digo sobre producción es lo que la documentación afirma sobre ella, y esa documentación
declara en varios puntos que producción **driftea** respecto de lo versionado.

**Contenido de los documentos grandes de `docs/`.** Leí completo el `CLAUDE.md` de la raíz,
el README, el de arquitectura y el changelog. De los demás —bitácora de 74 KB, contraste de
44 KB, matriz de 40 KB, auditorías de 53 y 16 KB, y el documento de extracción de 58 KB—
verifiqué existencia, tamaño, fecha y propósito declarado, pero **no los leí completos**. Es
posible que contengan información que cambie alguna conclusión de las secciones 6 y 10.

**El archivo `Plan de trabajo`** no tiene extensión y es el que gobierna qué se hace ahora.
No lo leí completo.

**Si existen hooks de pre-commit instalados localmente.** No hay archivo de configuración
versionado, pero `CLAUDE.md` marca "confirmar si está instalado" como pendiente abierto, así
que el propio proyecto tampoco lo sabe. No inspeccioné `.git/hooks`.

**Qué contiene `AUDITORIA_FUNCIONAL.md`.** Está en `.gitignore`. No verifiqué si existe en
disco ni lo abrí.

**El motivo del segundo autor en el historial.** Hay dos identidades en los 176 commits. No
investigué la distribución entre ellas para no manipular datos de personas.

**Si la deriva entre `CLAUDE.md` y el conteo real de archivos** (servicios, repositorios,
tests, migraciones) corresponde a trabajo posterior a la última actualización del documento o
a un criterio de conteo distinto — por ejemplo si excluye archivos `__init__.py`. Las
diferencias van en las dos direcciones, lo que sugiere lo segundo, pero no lo confirmé.

**Cuál de los dos entornos virtuales del backend está vigente.** La documentación menciona
uno como resto de otra máquina; en disco hay uno solo y ninguno está versionado. No lo
inspeccioné.
