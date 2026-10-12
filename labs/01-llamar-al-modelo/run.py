"""Lab 01: qué cambia al variar modelo, system prompt, temperatura y largo máximo.

Uso:
    uv run labs/01-llamar-al-modelo/run.py              # corre lo que falte y escribe results.md
    uv run labs/01-llamar-al-modelo/run.py --solo A     # un solo experimento (A, B, C o D)

Cada llamada se guarda en corridas.jsonl apenas termina. Si se corta (límite de uso, red),
al volver a correr retoma donde quedó: las llamadas ya hechas no se repiten.
"""

import argparse
import json
import statistics
import time
import unicodedata
from collections import defaultdict
from datetime import date
from pathlib import Path

from llm_lab.modelos import Modelo, completar

AQUI = Path(__file__).parent
PREGUNTAS = [json.loads(l) for l in (AQUI / "preguntas.jsonl").read_text().splitlines()]
CORRIDAS = AQUI / "corridas.jsonl"

SYSTEM = (
    "Sos un asistente que responde preguntas sobre guías de trámites usando solo el texto "
    "que se te da. Respondé exactamente en el formato pedido, sin explicaciones."
)

MODELOS = [
    Modelo("nvidia", "z-ai/glm-5.3"),
    Modelo("nvidia", "moonshotai/kimi-k3"),
    Modelo("groq", "openai/gpt-oss-120b"),
    Modelo("groq", "qwen/qwen3.8-27b"),
    Modelo("gemini", "gemini-3.5-flash"),
    Modelo("openrouter", "nvidia/nemotron-3-super-120b-a12b:free"),
]
RAPIDO = Modelo("groq", "qwen/qwen3.8-27b")          # sin razonamiento visible: ideal para B
RAZONADOR = Modelo("groq", "openai/gpt-oss-120b")    # razona antes de contestar: ideal para D

# Pausa mínima entre llamadas por proveedor, para no pasar el límite por minuto del free tier.
PAUSA_S = {"groq": 2.2, "nvidia": 1.6, "gemini": 6.5, "openrouter": 3.2}

# Cada experimento es una lista de configuraciones: (modelo, con_system, temperatura, max_tokens, repeticion)
EXPERIMENTOS = {
    "A": [(m, True, 0.0, None, 0) for m in MODELOS],
    "B": [(RAPIDO, True, t, None, rep) for t in (0.0, 0.7, 1.5) for rep in range(3)],
    "C": [(m, s, 0.0, None, 0) for m in (RAPIDO, RAZONADOR) for s in (False, True)],
    "D": [(RAZONADOR, True, 0.0, mt, 0) for mt in (16, 64, 512, None)],
}


def normalizar(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sin_tildes.strip().strip(".").upper().replace(" ", "")


def clave(experimento, modelo, con_system, temp, max_tokens, rep, pregunta_id) -> str:
    return f"{experimento}|{modelo}|{con_system}|{temp}|{max_tokens}|{rep}|{pregunta_id}"


def cargar_corridas() -> dict[str, dict]:
    if not CORRIDAS.exists():
        return {}
    filas = [json.loads(l) for l in CORRIDAS.read_text().splitlines() if l.strip()]
    return {f["clave"]: f for f in filas}


def correr(experimento: str, hechas: dict[str, dict]) -> None:
    ultimo = defaultdict(float)
    for modelo, con_system, temp, max_tokens, rep in EXPERIMENTOS[experimento]:
        for p in PREGUNTAS:
            k = clave(experimento, modelo, con_system, temp, max_tokens, rep, p["id"])
            if k in hechas:
                continue
            espera = PAUSA_S[modelo.proveedor] - (time.time() - ultimo[modelo.proveedor])
            if espera > 0:
                time.sleep(espera)
            mensajes = [{"role": "system", "content": SYSTEM}] if con_system else []
            mensajes.append({"role": "user",
                             "content": f"Texto:\n{p['contexto']}\n\nPregunta: {p['pregunta']}"})
            ultimo[modelo.proveedor] = time.time()
            try:
                r = completar(mensajes, modelo, temperature=temp, max_tokens=max_tokens,
                              aceptar_vacia=True)  # el experimento D mide justo eso
            except Exception as e:  # noqa: BLE001 — sin respaldo a propósito: medimos ESTE modelo
                print(f"  ! {modelo} {p['id']}: {str(e)[:120]}")
                continue
            fila = {
                "clave": k, "experimento": experimento, "modelo": str(modelo),
                "con_system": con_system, "temperatura": temp, "max_tokens": max_tokens,
                "rep": rep, "pregunta": p["id"], "tipo": p["tipo"], "esperado": p["esperado"],
                "respuesta": r.texto, "correcta": normalizar(r.texto) == normalizar(p["esperado"]),
                "tokens_entrada": r.tokens_entrada, "tokens_salida": r.tokens_salida,
                "latencia_s": r.latencia_s,
            }
            with CORRIDAS.open("a") as f:
                f.write(json.dumps(fila, ensure_ascii=False) + "\n")
            hechas[k] = fila
            print(f"  {experimento} {modelo!s:50} {p['id']} {'✓' if fila['correcta'] else '✗'}")


def resumen(filas: list[dict], por: tuple[str, ...]) -> list[str]:
    grupos = defaultdict(list)
    for f in filas:
        grupos[tuple(f[c] for c in por)].append(f)
    lineas = [
        "| " + " | ".join(por) + " | n | aciertos | latencia p50 (s) | tokens salida p50 |",
        "|" + "---|" * (len(por) + 4),
    ]
    for g, fs in sorted(grupos.items(), key=lambda x: str(x[0])):
        ac = sum(f["correcta"] for f in fs) / len(fs)
        lat = statistics.median(f["latencia_s"] for f in fs)
        tok = statistics.median(f["tokens_salida"] for f in fs)
        lineas.append("| " + " | ".join(str(x) for x in g)
                      + f" | {len(fs)} | {ac:.0%} | {lat:.2f} | {tok:.0f} |")
    return lineas


def consistencia(filas: list[dict]) -> list[str]:
    """Para B: ¿qué fracción de preguntas recibe la misma respuesta en las 3 repeticiones?"""
    por_temp = defaultdict(lambda: defaultdict(set))
    for f in filas:
        por_temp[f["temperatura"]][f["pregunta"]].add(normalizar(f["respuesta"]))
    lineas = ["| temperatura | preguntas con la misma respuesta en las 3 repeticiones |",
              "|---|---|"]
    for t, preguntas in sorted(por_temp.items()):
        iguales = sum(len(r) == 1 for r in preguntas.values())
        lineas.append(f"| {t} | {iguales}/{len(preguntas)} |")
    return lineas


def escribir_resultados(hechas: dict[str, dict]) -> None:
    filas = list(hechas.values())
    de = lambda e: [f for f in filas if f["experimento"] == e]
    errores_a = [f for f in de("A") if not f["correcta"]]
    md = [
        "# Lab 01: resultados", "", (f"Última corrida: {date.today().isoformat()}. "
        f"{len(filas)} llamadas, costo US$ 0 (free tiers)."), "",
        "## A. Modelos (temperatura 0, con system prompt)", "", *resumen(de("A"), ("modelo",)),
        "", "Por tipo de pregunta:", "", *resumen(de("A"), ("modelo", "tipo")), "",
        "Errores:", "",
        *[f"- `{f['modelo']}` {f['pregunta']}: esperado `{f['esperado']}`, "
          f"respondió `{f['respuesta'].strip()[:80]}`" for f in errores_a],
        "", f"## B. Temperatura ({RAPIDO}, 3 repeticiones)", "",
        *resumen(de("B"), ("temperatura",)), "", *consistencia(de("B")), "",
        "## C. System prompt (temperatura 0)", "", *resumen(de("C"), ("modelo", "con_system")),
        "", f"## D. Largo máximo ({RAZONADOR})", "", *resumen(de("D"), ("max_tokens",)), "",
        "Respuestas vacías por max_tokens:", "",
        *[f"- max_tokens={mt}: {sum(1 for f in de('D') if f['max_tokens'] == mt and not f['respuesta'].strip())}"
          f"/{sum(1 for f in de('D') if f['max_tokens'] == mt)}" for mt in (16, 64, 512, None)],
    ]
    (AQUI / "results.md").write_text("\n".join(md) + "\n")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--solo", choices=list(EXPERIMENTOS))
    args = p.parse_args()
    hechas = cargar_corridas()
    for e in [args.solo] if args.solo else list(EXPERIMENTOS):
        print(f"Experimento {e}")
        correr(e, hechas)
    escribir_resultados(hechas)
    print(f"\nresultados: {AQUI / 'results.md'}")


if __name__ == "__main__":
    main()
