"""The "Estudio" section: a reader for every Markdown document in the repo, in Spanish or
English (`X.en.md` next to `X.md`). Only the files listed here can be read."""

from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

GENERAL = [
    ("README.md", "Inicio del laboratorio", "Lab overview"),
    ("docs/sdd-semaforo.md", "Diseño del semáforo (SDD)", "Quality gate design (SDD)"),
    ("notes/00-mapa-rag.md", "Mapa del RAG", "RAG map"),
]
# Pipeline order, as the labs were run
LABS = [
    ("01-llamar-al-modelo", "Llamar al modelo", "Calling the model"),
    ("02-salida-estructurada", "Salida estructurada", "Structured output"),
    ("11-parseo", "Parseo", "Parsing"),
    ("03-chunking", "Chunking", "Chunking"),
    ("04-embeddings-busqueda", "Embeddings y búsqueda", "Embeddings and search"),
    ("12-base-vectorial", "Base vectorial", "Vector database"),
    ("05-reranking", "Re-ranking", "Re-ranking"),
    ("13-logprobs", "Decisiones por logprobs", "Logprob decisions"),
    ("14-reglas", "Reglas en lenguaje natural", "Natural-language rules"),
    ("15-revision-guiada", "Revisión guiada", "Guided review"),
    ("06-rag-completo", "RAG completo", "Full RAG"),
    ("07-cuando-no-sabe", "Cuándo no sabe", "When it doesn't know"),
    ("10-evaluacion", "Evaluación", "Evaluation"),
    ("16-app", "App y experimento final", "App and final experiment"),
]


@dataclass
class Entry:
    path: str  # the Spanish file, relative to the repo root
    title: str  # in the selected language
    group: str
    has_en: bool


def english(path: str) -> str:
    return path[:-3] + ".en.md"


def entries(lang: str) -> list[Entry]:
    out = []
    for path, es, en in GENERAL:
        out.append(Entry(path, en if lang == "en" else es, "general",
                         (ROOT / english(path)).exists()))
    for folder, es, en in LABS:
        number = folder.split("-")[0]
        title = f"{number} · {en if lang == 'en' else es}"
        readme = f"labs/{folder}/README.md"
        if (ROOT / readme).exists():
            out.append(Entry(readme, title, "labs", (ROOT / english(readme)).exists()))
        results = f"labs/{folder}/results.md"
        if (ROOT / results).exists():
            out.append(Entry(results, "Results (numbers)" if lang == "en" else "Resultados (números)",
                             f"results:{folder}", False))
    return out


def read(path: str, lang: str) -> tuple[str, str, bool]:
    """(markdown, language actually served, whether it fell back to Spanish)."""
    allowed = {e.path for e in entries("es")}
    if path not in allowed:
        raise KeyError(path)
    if lang == "en" and (ROOT / english(path)).exists():
        return (ROOT / english(path)).read_text(), "en", False
    return (ROOT / path).read_text(), "es", lang == "en"


@dataclass
class Stage:
    number: str
    folder: str
    kind: str
    title: str
    metric: str
    caption: str
    highlight: bool = False


# The home page rail. Every number comes from the lab's results.md.
STAGES = [
    Stage("01", "01-llamar-al-modelo", "base", "Llamar al modelo", "0 %",
          "de aciertos con un tope de 16 o 64 tokens: el razonamiento se come la respuesta"),
    Stage("02", "02-salida-estructurada", "base", "Salida estructurada", "34/34",
          "montos extraídos; el problema real son las fechas que solo dicen mes y año"),
    Stage("11", "11-parseo", "ingesta", "Parseo", "17/17",
          "ítems de lista con Docling en un PDF con diseño; 12 con el parser a mano"),
    Stage("03", "03-chunking", "recuperación", "Chunking", "+11 pts",
          "de recall@1 por anteponer la ruta de títulos a cada chunk"),
    Stage("04", "04-embeddings-busqueda", "recuperación", "Embeddings y búsqueda", "66 → 55 %",
          "recall@1 de bge-m3 solo y con BM25: la búsqueda híbrida empeora"),
    Stage("12", "12-base-vectorial", "recuperación", "Base vectorial", "77 → 97 %",
          "recall del HNSW propio al elegir vecinos con la heurística de diversidad"),
    Stage("05", "05-reranking", "recuperación", "Re-ranking", "0,77 → 0,84",
          "MRR al reordenar los 10 primeros con un cross-encoder local"),
    Stage("13", "13-logprobs", "semáforo", "Decisiones por logprobs", "0,03 vs 0,24",
          "error de calibración leyendo logprobs contra pedirle JSON al mismo modelo"),
    Stage("14", "14-reglas", "semáforo", "Reglas en lenguaje natural", "6/6",
          "reglas vagas detectadas; 14 de 24 compiladas bien sin editar"),
    Stage("15", "15-revision-guiada", "semáforo", "Revisión guiada", "0/10",
          "trampas en las que el modelo inventó un dato que la persona no dio"),
    Stage("06", "06-rag-completo", "respuesta", "RAG completo", "55/57",
          "respuestas respaldadas por los fragmentos que citan; ninguna inventada"),
    Stage("07", "07-cuando-no-sabe", "respuesta", "Cuándo no sabe", "10/10",
          "abstenciones correctas del modelo; el umbral del re-ranker detecta 4"),
    Stage("10", "10-evaluacion", "respuesta", "Evaluación", "κ 0,82",
          "acuerdo del juez local con las etiquetas; el de 120B, 0,51"),
    Stage("16", "16-app", "integración", "Experimento final", "13 = 13",
          "corregir antes de indexar empató con no corregir. El porqué está en el estudio.",
          highlight=True),
]

FINDINGS = [
    ("Recuperación", "La estructura le gana al modelo",
     ("Anteponer la ruta de títulos a cada chunk sumó 11 puntos de recall@1, más que pasar "
     "de e5-large a bge-m3 (6). Y la búsqueda híbrida, que se daba por hecha, empeoró.")),
    ("Semáforo", "La confianza vale tanto como la respuesta",
     ("Leer las probabilidades de A/B/C da una confianza honesta. Pedir JSON acierta parecido "
     "pero dice 98 % siempre, y así no hay forma de marcar un bloque como dudoso.")),
    ("Revisión", "No inventa, pero puede cambiar el sentido",
     ("Cuando la persona no trae el dato, el modelo deja la marca [FALTA]. Pero al pasar un "
     "texto normativo a voz activa, cambió quién tenía que retener la licencia.")),
    ("Hipótesis", "El RAG compensa lo que el semáforo marca",
     ("Una vigencia que falta en un bloque, el RAG la encuentra en otro. La corrección cambia "
     "las respuestas cuando agrega un dato que el documento no tenía, como quién lo publica.")),
]
