"""The quality-gate app: upload a document, see its traffic light, fix the reds one by one,
index it, ask questions about what is indexed.

    uv run uvicorn app.main:app --reload
    # http://localhost:8000

Three screens (SDD §5.7): Documento (upload, gate, guided review), Chat, Reglas.
"""

import json
import os
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.services import Services, word_diff
from app.store import Store
from llm_lab.chunking import block_text

HERE = Path(__file__).parent
DATA = Path(os.environ.get("LLM_LAB_APP_DATA", HERE.parent / "data" / "app"))

app = FastAPI(title="Semáforo de calidad documental")
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
templates = Jinja2Templates(directory=HERE / "templates")
services = Services(Store(DATA / "app.sqlite"))


def sse(events) -> StreamingResponse:
    def gen():
        for e in events:
            yield f"data: {json.dumps(e, ensure_ascii=False)}\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream")


# ---------------------------------------------------------------- documents


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request, "index.html",
                                      {"documents": services.store.documents()})


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
        "evaluated": bool(verdicts), "rules": services.rules,
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
        "block": (block_text(doc.blocks[p.block]) if p.block >= 0
                  else services.document_state(doc).split("]\n", 1)[-1]),
        "path": (" > ".join(doc.blocks[p.block].path) if p.block >= 0
                 else "Documento completo: la corrección agrega una oración al comienzo"),
        "question": f"{rule.levels.red} ¿Qué dato falta o cómo debería decirse?",
    })


@app.post("/documents/{doc_id}/review", response_class=HTMLResponse)
def propose(request: Request, doc_id: str, block: int = Form(...), rule: str = Form(...),
            answer: str = Form(...), n: int = Form(0)):
    review_id = services.propose(doc_id, block, rule, answer)
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
    return templates.TemplateResponse(request, "chat.html",
                                      {"indexed": services.store.indexed()})


@app.get("/chat/ask")
def ask(q: str):
    return sse(services.ask(q))


@app.get("/rules", response_class=HTMLResponse)
def rules(request: Request):
    return templates.TemplateResponse(request, "rules.html", {"rules": services.rules})


@app.post("/rules/compile", response_class=HTMLResponse)
def compile_rule_view(request: Request, text: str = Form(...)):
    from llm_lab.compiler import compile_rule
    result, attempts, error = compile_rule(text)
    return templates.TemplateResponse(request, "_compiled.html", {
        "result": result, "error": error, "attempts": attempts,
        "yaml": result.rule.model_dump_json(indent=2) if result and result.rule else None})
