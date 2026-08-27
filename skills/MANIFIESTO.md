# Manifiesto de skills externas

Este archivo es el registro único de las skills traídas desde repos de terceros a `skills/externas/`: qué se copió, de dónde, en qué commit y quién lo aprobó.
Regla: ninguna skill externa se usa si no está listada acá.

## Skills vendoreadas

| Skill | Repo de origen | Commit de origen | Fecha de copia | Archivos no documentales | Aprobado por |
|---|---|---|---|---|---|
| `skill-creator` | https://github.com/anthropics/skills | `3b3fad96af16a10759d930941b4520ba0c40edae` | 2026-08-27 | **`.py` (10):** `scripts/__init__.py`, `scripts/aggregate_benchmark.py`, `scripts/generate_report.py`, `scripts/improve_description.py`, `scripts/package_skill.py`, `scripts/quick_validate.py`, `scripts/run_eval.py`, `scripts/run_loop.py`, `scripts/utils.py`, `eval-viewer/generate_review.py` · **`.html` (2):** `assets/eval_review.html`, `eval-viewer/viewer.html` | |
| `webapp-testing` | https://github.com/anthropics/skills | `3b3fad96af16a10759d930941b4520ba0c40edae` | 2026-08-27 | **`.py` (4):** `scripts/with_server.py`, `examples/console_logging.py`, `examples/element_discovery.py`, `examples/static_html_automation.py` | |
| `mcp-builder` | https://github.com/anthropics/skills | `3b3fad96af16a10759d930941b4520ba0c40edae` | 2026-08-27 | **`.py` (2):** `scripts/connections.py`, `scripts/evaluation.py` · **`.xml` (1):** `scripts/example_evaluation.xml` | |
| `frontend-design` | https://github.com/anthropics/skills | `3b3fad96af16a10759d930941b4520ba0c40edae` | 2026-08-27 | ninguno | |
| `theme-factory` | https://github.com/anthropics/skills | `3b3fad96af16a10759d930941b4520ba0c40edae` | 2026-08-27 | **`.pdf` (1):** `theme-showcase.pdf` | |

## Reglas de vendoring

Se copia únicamente la carpeta de la skill. Ningún archivo de instrucciones que viva en la raíz del repo de origen —`CLAUDE.md`, `AGENTS.md`, `.cursorrules`, `hooks/` o cualquier equivalente— entra al repo sin una decisión explícita y firmada. Esos archivos le hablan al agente, no a la skill, y arrastran comportamiento que nadie pidió.

Actualizar una skill es un pull request revisado por un humano. Nunca automático. No hay sincronización periódica, ni script que traiga la última versión del upstream por su cuenta: cada cambio se mira, se compara contra lo que ya está y se aprueba a mano.

Ninguna skill se habilita mientras contenga archivos que no sean texto plano legible por un humano. El criterio es amplio: se declaran y se leen todos los archivos no documentales, no solo los ejecutables, porque un HTML puede traer JavaScript y un PDF es un formato con superficie de ataque propia. Estar copiada en el repo y estar habilitada son dos estados distintos: lo primero es este manifiesto, lo segundo exige que alguien haya leído todo lo que no sea markdown y que exista una frontera de ejecución aislada, un lugar donde correr esos archivos sin acceso al resto del sistema.

Las dependencias declaradas por una skill se congelan a versión exacta antes de habilitarla. Un `requirements.txt` sin versiones fijadas es motivo de rechazo: el hash del commit congela la skill, no lo que la skill descarga de internet al instalarse.
