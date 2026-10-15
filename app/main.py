"""The quality-gate app: upload a document, see its traffic light, fix the reds one by one,
index it, ask questions about what is indexed, and read the study behind every decision.

    uv run uvicorn app.main:app --reload
    # http://localhost:8000

Screens: Inicio (the project and its pipeline), Documentos, Documento (traffic light and
guided review), Chat, Reglas, Estudio (every lab's write-up, in Spanish and English).
"""

import json
import os
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import study
from app.services import Services, word_diff
from app.store import Store
from llm_lab.chunking import block_text

HERE = Path(__file__).parent
DATA = Path(os.environ.get("LLM_LAB_APP_DATA", HERE.parent / "data" / "app"))

app = FastAPI(title="Semáforo de calidad documental")
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
templates = Jinja2Templates(directory=HERE / "templates")


def asset(name: str) -> str:
    """Static URL with the file's modification time, so browsers never keep a stale copy."""
    return f"/static/{name}?v={int((HERE / 'static' / name).stat().st_mtime)}"


templates.env.globals["asset"] = asset
services = Services(Store(DATA / "app.sqlite"))


def friendly(error: Exception) -> str:
    """What the person sees when a model call fails."""
    text = str(error)
    if "RateLimit" in text or "429" in text:
        return ("Se agotó la cuota gratuita de los modelos por API (Groq limita los tokens por "
                "día). Probá de nuevo en un rato o mañana.")
    if "No model answered" in text:
        return "Ningún modelo respondió: revisá la conexión o las claves en .env."
    return f"Algo falló: {text[:200]}"


def sse(events) -> StreamingResponse:
    def gen():
        try:
            for e in events:
                yield f"data: {json.dumps(e, ensure_ascii=False)}\n\n"
        except Exception as e:  # noqa: BLE001 — tell the page instead of cutting the stream
            yield f"data: {json.dumps({'error': friendly(e), 'done': True})}\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream")


# ---------------------------------------------------------------- home and documents


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    findings = [{"label": a, "title": b, "text": c} for a, b, c in study.FINDINGS]
    return templates.TemplateResponse(request, "home.html",
                                      {"stages": study.STAGES, "findings": findings})


@app.get("/documentos", response_class=HTMLResponse)
def documents(request: Request):
    docs = services.store.documents()
    corpus = services.corpus_ids()
    return templates.TemplateResponse(request, "documents.html", {
        "documents": docs, "corpus_size": len(corpus),
        "imported": sum(d["id"] in corpus for d in docs)})


@app.post("/documentos/importar")
def import_corpus():
    services.import_corpus()
    return RedirectResponse("/documentos", status_code=303)


@app.post("/documents")
async def upload(file: UploadFile):
    allowed = (".pdf", ".html", ".htm", ".doc", ".docx")
    if not file.filename or not file.filename.lower().endswith(allowed):
        raise HTTPException(400, f"Formatos aceptados: {', '.join(allowed)}")
    doc_id = services.ingest(file.filename, await file.read(), DATA / "uploads")
    return RedirectResponse(f"/documents/{doc_id}", status_code=303)


@app.get("/documents/{doc_id}", response_class=HTMLResponse)
def document(request: Request, doc_id: str):
    doc = services.store.document(doc_id)
    version = services.store.latest_version(doc_id)
    verdicts: dict[int, list[dict]] = {}
    for e in services.store.evaluations(doc_id, version):
        verdicts.setdefault(e["block"], []).append(e)
    problems = services.problems(doc_id)
    blocks = []
    for i, b in enumerate(doc.blocks):
        levels = [v["level"] for v in verdicts.get(i, [])]
        worst = "red" if "red" in levels else "yellow" if "yellow" in levels else (
            "green" if levels else "none")
        blocks.append({"i": i, "kind": b.kind, "level": b.level, "text": block_text(b),
                       "worst": worst, "verdicts": verdicts.get(i, [])})
    return templates.TemplateResponse(request, "document.html", {
        "doc": doc, "version": version, "blocks": blocks,
        "doc_verdicts": verdicts.get(-1, []), "problems": problems,
        "reds": sum(p.level == "red" for p in problems),
        "yellows": sum(p.level == "yellow" for p in problems),
        "blocking": sum(p.blocking for p in problems),
        "can_index": services.can_index(doc_id),
        "indexed": doc_id in dict(services.store.indexed()),
        "evaluated": bool(verdicts), "rules": services.rules,
        "pending": len(services.checks(doc)) - sum(len(v) for v in verdicts.values()),
        "history": services.store.history(doc_id),
    })


@app.get("/documents/{doc_id}/evaluate")
def evaluate(doc_id: str):
    return sse(services.evaluate(doc_id))


@app.post("/documents/{doc_id}/index")
def index_document(doc_id: str):
    try:
        services.index(doc_id)
    except ValueError as e:
        raise HTTPException(409, str(e)) from e
    return RedirectResponse(f"/documents/{doc_id}", status_code=303)


# ---------------------------------------------------------------- guided review


@app.get("/documents/{doc_id}/review", response_class=HTMLResponse)
def review(request: Request, doc_id: str, n: int = 0):
    problems = services.problems(doc_id)
    if not problems:
        return RedirectResponse(f"/documents/{doc_id}", status_code=303)
    n = max(0, min(n, len(problems) - 1))
    p = problems[n]
    doc = services.store.document(doc_id)
    rule = services.rules[p.rule]
    return templates.TemplateResponse(request, "review.html", {
        "doc": doc, "n": n, "total": len(problems), "problem": p, "rule": rule,
        "problems": problems,
        "block": (block_text(doc.blocks[p.block]) if p.block >= 0
                  else services.document_state(doc).split("]\n", 1)[-1]),
        "path": (" > ".join(doc.blocks[p.block].path) if p.block >= 0
                 else "Documento completo: la corrección agrega una oración al comienzo"),
        "question": "¿Qué dato falta o cómo debería decirse?",
    })


@app.post("/documents/{doc_id}/review", response_class=HTMLResponse)
def propose(request: Request, doc_id: str, block: int = Form(...), rule: str = Form(...),
            answer: str = Form(...), n: int = Form(0)):
    try:
        review_id = services.propose(doc_id, block, rule, answer)
    except Exception as e:  # noqa: BLE001 — a failed model call is shown, not raised
        return templates.TemplateResponse(request, "_error.html", {"message": friendly(e)})
    r = services.store.review(review_id)
    return templates.TemplateResponse(request, "_proposal.html", {
        "doc_id": doc_id, "r": r, "n": n, "diff": word_diff(r["before"], r["after"]),
        "invented": json.loads(r["invented"])})


@app.post("/reviews/{review_id}/accept")
def accept(review_id: int, n: int = Form(0)):
    r = services.store.review(review_id)
    if json.loads(r["invented"]):
        raise HTTPException(409, "La reescritura agrega números que no estaban: no se acepta.")
    services.accept(review_id)
    return RedirectResponse(f"/documents/{r['doc_id']}/review?n={n}", status_code=303)


# ---------------------------------------------------------------- chat and rules


@app.get("/chat", response_class=HTMLResponse)
def chat(request: Request):
    titles = {d["id"]: d["title"] for d in services.store.documents()}
    indexed = [(doc_id, titles.get(doc_id, doc_id)) for doc_id, _ in services.store.indexed()]
    return templates.TemplateResponse(request, "chat.html", {"indexed": indexed})


@app.get("/chat/ask")
def ask(q: str):
    return sse(services.ask(q))


@app.get("/rules", response_class=HTMLResponse)
def rules(request: Request):
    groups: dict[str, list] = {}
    for r in services.rules.values():
        family = r.source.split(",")[0].split(" (")[0]
        groups.setdefault(family, []).append(r)
    return templates.TemplateResponse(request, "rules.html", {"groups": groups})


@app.post("/rules/compile", response_class=HTMLResponse)
def compile_rule_view(request: Request, text: str = Form(...)):
    from llm_lab.compiler import compile_rule
    try:
        result, attempts, error = compile_rule(text)
    except Exception as e:  # noqa: BLE001
        return templates.TemplateResponse(request, "_error.html", {"message": friendly(e)})
    return templates.TemplateResponse(request, "_compiled.html", {
        "result": result, "error": error, "attempts": attempts,
        "yaml": result.rule.model_dump_json(indent=2) if result and result.rule else None})


# ---------------------------------------------------------------- study: the labs' documents


@app.get("/estudio", response_class=HTMLResponse)
def estudio(request: Request, doc: str = "README.md", lang: str = "es"):
    lang = "en" if lang == "en" else "es"
    try:
        markdown, served, fallback = study.read(doc, lang)
    except KeyError as e:
        raise HTTPException(404, "Ese documento no está en el estudio.") from e
    entries = study.entries(lang)
    readable = [e for e in entries if not e.group.startswith("results")]
    current = next((i for i, e in enumerate(readable) if e.path == doc), None)
    prev_doc = readable[current - 1] if current else None
    next_doc = (readable[current + 1] if current is not None and current + 1 < len(readable)
                else None)
    return templates.TemplateResponse(request, "study.html", {
        "doc": doc, "lang": lang, "served": served, "fallback": fallback,
        "markdown": markdown, "entries": entries, "prev_doc": prev_doc, "next_doc": next_doc,
        "generated": doc.endswith("results.md"),
    })
