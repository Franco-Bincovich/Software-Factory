"""CLI del armazón de ejecución — T14.

    python correr.py --pedido pedido.json --definicion "ruta/Requirement Agent.md" --vault "ruta/al/Vault"
    python correr.py --reanudar <run_id>

Una corrida nueva arranca, avanza hasta el primer Gate, imprime el `run_id` y
**termina el proceso**. La corrida queda esperando. El Gate se resuelve con la
CLI de T11 y recién entonces se reanuda.

Ese ciclo —corre, frena, resolvés, reanudás— es deliberado. Un proceso que se
queda vivo esperando una decisión humana durante horas invita a agregarle un
timeout, y ADR-004 lo prohíbe.

Por defecto el plan lo produce el modelo, contra la API de Anthropic y con cargo
a la cuenta. `--stub` lo reemplaza por un productor de relleno que no invoca a
nadie: sirve para ejercitar el armazón sin gastar.

El modo con el que arranca una corrida queda registrado como hecho suyo en el
Operational State. `--reanudar` lo lee de ahí en vez de deducirlo de los flags,
así que una corrida iniciada con `--stub` se retoma con el stub aunque quien la
reanude no lo repita. Pedir en la reanudación un modo distinto del registrado no
elige entre los dos: falla.
"""

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ / "src"))

import grafo  # noqa: E402
import productor  # noqa: E402
from agent_loader import CargaFallida  # noqa: E402
from intake import PedidoRechazado  # noqa: E402
from operational_state import OperationalState  # noqa: E402

# Costo nominal por iteración del stub. El productor real devuelve el costo
# medido y este valor no se usa.
COSTO_STUB = 0.1


def producir_stub(pedido, plan_anterior, incumplimientos, contexto_vault):
    """Productor de relleno. Arma un Plan de Trabajo mínimo que pasa T7.

    No invoca a ningún modelo: eso es T15. Existe para que el armazón se pueda
    correr de punta a punta y para que la forma del contrato quede fijada.

    Si recibe incumplimientos corrige el plan anterior en vez de regenerarlo, que
    es lo que exige el campo 9 de la Agent Definition. La corrección que sabe
    hacer es una sola: reponer lo que falta sobre la estructura que ya había.
    """
    sucede_a = plan_anterior["plan_id"] if plan_anterior else None

    return {
        "plan_id": "PLAN-STUB-1" if plan_anterior is None else "PLAN-STUB-2",
        "run_id": "asignado-por-la-corrida",
        "pedido_id": "asignado-por-el-intake",
        "sucede_a": sucede_a,
        "restricciones": {
            "techo_costo": pedido["techo_costo_usd"],
            "techo_tiempo_min": pedido["techo_tiempo_min"],
            "techo_iteraciones": pedido["techo_iteraciones"],
            "alcance_excluido": list(pedido["alcance_excluido"]),
        },
        "unidades": [
            {
                "id": "U1",
                "enunciado": "Construir el entregable que el pedido describe.",
                "criterios": [
                    {
                        "condicion_observable": "Corriendo el entregable sobre su entrada de "
                        "prueba, qué devuelve.",
                        "resultado_esperado": "Devuelve el resultado que el pedido describe, "
                        "sin error.",
                        "procedimiento": "Ejecutar el entregable sobre la entrada de prueba y "
                        "comparar la salida con lo esperado.",
                    }
                ],
                "dependencias": [],
                "rastreo": pedido["que_se_quiere"],
                "artefacto_esperado": "Entregable ejecutable con su prueba asociada.",
            }
        ],
        "supuestos": [
            "Plan producido por el stub de T14: no hubo modelo involucrado.",
        ],
        "fuera_de_alcance": [
            "Todo lo que el pedido declara excluido.",
        ],
    }


def _store(ruta):
    return OperationalState() if ruta is None else OperationalState(ruta)


def _checkpointer(ruta):
    if ruta is None:
        return grafo.abrir_checkpointer()
    return grafo.abrir_checkpointer(ruta)


def elegir_productor(modo, ruta_vault):
    """Devuelve `(producir_fn, costo_por_defecto, nombre_del_modelo)`.

    El productor real mide su propio costo y devuelve `(plan, costo)`, así que
    el costo por defecto queda en cero: si alguna vez se usara, sería una
    invención, y un techo alimentado con números inventados no es un techo.

    El nombre del modelo se devuelve para registrarlo como evidencia de la
    corrida. En modo stub no hay ninguno, y el hecho lo dice callándolo.
    """
    if modo == grafo.MODO_STUB:
        return producir_stub, COSTO_STUB, None

    load_dotenv(RAIZ / ".env")
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise SinCredencial(
            "ANTHROPIC_API_KEY no configurada. Agregala en .env "
            "(hay una plantilla en .env.example). Para correr sin modelo, "
            "usá --stub."
        )
    modelo = os.environ.get("ANTHROPIC_MODEL", "").strip() or productor.MODELO_POR_DEFECTO
    return productor.crear_productor(api_key, modelo, ruta_vault), 0.0, modelo


class SinCredencial(RuntimeError):
    """No hay `ANTHROPIC_API_KEY` y no se pidió el stub."""


class ModoContradictorio(RuntimeError):
    """La reanudación pide un modo y la corrida se abrió con el otro."""


class ModoNoRegistrado(RuntimeError):
    """La corrida es anterior a que el modo se registrara como hecho suyo."""


def modo_declarado(args):
    """El modo que piden los flags, o `None` si no piden ninguno.

    No pedir ninguno no es pedir el modelo: en una corrida nueva el default es
    el modelo, pero en una reanudación la ausencia de flag no dice nada y el
    hecho registrado es el que manda.
    """
    if args.stub:
        return grafo.MODO_STUB
    if args.modelo:
        return grafo.MODO_MODELO
    return None


def modo_para_reanudar(store, run_id, declarado):
    """El modo con el que se retoma la corrida: el que ella registró.

    Los flags no eligen acá; a lo sumo contradicen. Y una contradicción no se
    resuelve quedándose con uno de los dos: uno de los dos lados cree algo
    falso, y seguir adelante gastaría —o dejaría de producir— sin que nadie lo
    haya decidido.
    """
    registrado = grafo.modo_de(store, run_id)

    if registrado is None:
        if not store.leer_run(run_id):
            raise grafo.CorridaInexistente(
                "no hay corrida con id %s en el Operational State." % run_id
            )
        raise ModoNoRegistrado(
            "la corrida %s no registró su modo de producción: es anterior a que "
            "el modo se anotara como hecho de la corrida. No se reanuda, porque "
            "elegirle un modo ahora sería decidir por ella si gasta dinero. "
            "Abrí una corrida nueva declarando el modo." % run_id
        )

    if declarado is not None and declarado != registrado:
        raise ModoContradictorio(
            "la corrida %s se inició en modo '%s' y se la está reanudando con "
            "--%s. El modo es un hecho de la corrida y no se cambia al "
            "reanudarla. Reanudala sin ese flag y se retoma en modo '%s'."
            % (run_id, registrado, declarado, registrado)
        )

    return registrado


def main(argv=None):
    parser = argparse.ArgumentParser(description="Armazón de ejecución (T14).")
    parser.add_argument("--pedido", help="Ruta al pedido en JSON.")
    parser.add_argument("--definicion", help="Ruta a la Agent Definition en el Vault.")
    parser.add_argument("--reanudar", metavar="RUN_ID", help="Corrida a retomar.")
    parser.add_argument("--vault", help="Raíz del Vault, para el contexto de lectura.")
    parser.add_argument("--db", help="Ruta del Operational State.")
    parser.add_argument("--checkpointer", help="Ruta del checkpointer.")
    parser.add_argument(
        "--stub",
        action="store_true",
        help="Produce con el stub en vez del modelo. No consume ni exige credencial.",
    )
    parser.add_argument(
        "--modelo",
        action="store_true",
        help="Produce con el modelo real. Es el default; declararlo sirve para "
        "que una reanudación diga en voz alta con qué cree que corre.",
    )
    args = parser.parse_args(argv)

    if args.stub and args.modelo:
        print("--stub y --modelo son dos modos distintos; no se piden juntos.", file=sys.stderr)
        return 2
    if args.reanudar and (args.pedido or args.definicion):
        print("--reanudar no se combina con --pedido ni --definicion.", file=sys.stderr)
        return 2
    if not args.reanudar and not (args.pedido and args.definicion):
        print("una corrida nueva exige --pedido y --definicion.", file=sys.stderr)
        return 2

    declarado = modo_declarado(args)

    # El almacén se abre antes de elegir productor: en una reanudación el modo
    # sale de ahí, y elegir productor sin haberlo leído sería justamente el bug.
    store = _store(args.db)

    try:
        try:
            if args.reanudar:
                modo = modo_para_reanudar(store, args.reanudar, declarado)
            else:
                modo = declarado or grafo.MODO_MODELO
            producir_fn, costo, nombre_modelo = elegir_productor(modo, args.vault)
        except ModoContradictorio as error:
            print("error: %s" % error, file=sys.stderr)
            return 2
        except (
            ModoNoRegistrado,
            grafo.CorridaInexistente,
            SinCredencial,
            productor.ModeloSinPrecio,
        ) as error:
            print("error: %s" % error, file=sys.stderr)
            return 1

        checkpointer = _checkpointer(args.checkpointer)

        if args.reanudar:
            estado = grafo.reanudar(
                args.reanudar, store, checkpointer, producir_fn, args.vault, costo
            )
            print("corrida %s: %s" % (args.reanudar, estado.get("resultado") or "en curso"))
            return 0

        try:
            with open(args.pedido, encoding="utf-8") as fh:
                pedido = json.load(fh)
        except OSError as error:
            print("no se pudo leer el pedido: %s" % error, file=sys.stderr)
            return 1
        except json.JSONDecodeError as error:
            print("el pedido no es JSON válido: %s" % error, file=sys.stderr)
            return 1

        run_id = grafo.ejecutar(
            args.definicion,
            pedido,
            producir_fn,
            store,
            checkpointer,
            args.vault,
            costo,
            modo=modo,
            modelo=nombre_modelo,
        )
        print(run_id)
        return 0

    except CargaFallida as error:
        for motivo in error.motivos:
            print("definición rechazada: %s" % motivo, file=sys.stderr)
        return 1
    except PedidoRechazado as error:
        for motivo in error.motivos:
            print("pedido rechazado: %s" % motivo, file=sys.stderr)
        return 1
    except (grafo.CorridaBloqueada, grafo.CorridaInexistente) as error:
        print("error: %s" % error, file=sys.stderr)
        return 1
    except productor.ProductorSinContexto as error:
        print("error: %s" % error, file=sys.stderr)
        return 1
    except OSError as error:
        # Definición inexistente, Vault mal apuntado, permisos. Un error de
        # entorno se informa; no se convierte en traceback.
        print("no se pudo leer un archivo declarado: %s" % error, file=sys.stderr)
        return 1
    finally:
        store.cerrar()


if __name__ == "__main__":
    sys.exit(main())
