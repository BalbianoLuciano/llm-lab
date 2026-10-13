"""App flow without heavy models: a fake evaluator and a fake RAG stand in for the real ones.

    uv run pytest tests/test_app.py
"""

import importlib
import json

import pytest
from fastapi.testclient import TestClient

from llm_lab.evaluator import Verdict

HTML = """<html><head><title>Tasa de prueba</title></head><body><main>
<h1>Tasa de prueba</h1>
<p>Este trámite sirve para pedir un certificado. Lo emite el Organismo de Prueba.</p>
<h2>Costo</h2>
<p>El certificado cuesta $ 5.000.</p>
<p>Presentá el DNI en la ventanilla.</p>
</main></body></html>""".encode()


class FakeEvaluator:
    """Red for amounts without an effective date, green for everything else."""

    def evaluate(self, state, rule):
        block = state.split("[BLOQUE A EVALUAR")[-1]
        red = (rule.id == "r8-vigencia" and "$" in block and "desde" not in block) or (
            rule.id == "r9-emisor-fecha" and "Publicado" not in block)
        level = "red" if red else "green"
        return Verdict(level, {"green": 0.1 if red else 0.9, "yellow": 0.0,
                               "red": 0.9 if red else 0.1})


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_LAB_APP_DATA", str(tmp_path))
    from app import main
    main = importlib.reload(main)
    main.services.evaluator = FakeEvaluator()
    monkeypatch.setattr("app.services.rewrite_block",
                        lambda state, block, rule, answer, models: block.rstrip(".")
                        + ", vigente desde el 1 de marzo de 2026.")

    class Answer:
        text = "Publicado por el Organismo de Prueba el 1 de marzo de 2026."
    monkeypatch.setattr("app.services.complete", lambda *a, **k: Answer())
    return TestClient(main.app), main


def test_upload_evaluate_review_index(client):
    c, main = client
    r = c.post("/documents", files={"file": ("tasa-prueba.html", HTML, "text/html")},
               follow_redirects=False)
    assert r.status_code == 303
    doc_id = r.headers["location"].rsplit("/", 1)[-1]

    events = [json.loads(line[6:]) for line in c.get(f"/documents/{doc_id}/evaluate").text
              .splitlines() if line.startswith("data: ")]
    assert events and events[-1]["done"] == events[-1]["total"]
    assert any(e["rule"] == "r8-vigencia" and e["level"] == "red" for e in events)

    # a blocking red: the document cannot be indexed yet
    assert c.post(f"/documents/{doc_id}/index").status_code == 409
    page = c.get(f"/documents/{doc_id}").text
    assert "2 rojos" in page and "Revisar" in page

    # guided review: a document problem (who publishes it) and a block problem (no date)
    review = c.get(f"/documents/{doc_id}/review").text
    assert "r9-emisor-fecha" in review and "Documento completo" in review
    answers = {"r9-emisor-fecha": "Lo publica el Organismo de Prueba, 1 de marzo de 2026",
               "r8-vigencia": "Rige desde el 1 de marzo de 2026"}
    for _ in range(2):
        problem = main.services.problems(doc_id)[0]
        r = c.post(f"/documents/{doc_id}/review",
                   data={"block": problem.block, "rule": problem.rule,
                         "answer": answers[problem.rule], "n": 0})
        assert "<ins>" in r.text and "Aceptar" in r.text
        review_id = int(r.text.split("/reviews/")[1].split("/")[0])
        assert c.post(f"/reviews/{review_id}/accept", data={"n": 0},
                      follow_redirects=False).status_code == 303

    # two new versions: a sentence added at the top, and the fixed block (shifted by one)
    doc = main.services.store.document(doc_id)
    assert doc.blocks[0].text.startswith("Publicado por")
    assert main.services.store.latest_version(doc_id) == 3
    assert main.services.can_index(doc_id)
    assert c.post(f"/documents/{doc_id}/index", follow_redirects=False).status_code == 303
    assert main.services.store.indexed() == [(doc_id, 3)]


def test_invented_numbers_cannot_be_accepted(client, monkeypatch):
    c, main = client
    r = c.post("/documents", files={"file": ("tasa-prueba.html", HTML, "text/html")},
               follow_redirects=False)
    doc_id = r.headers["location"].rsplit("/", 1)[-1]
    list(main.services.evaluate(doc_id))
    monkeypatch.setattr("app.services.rewrite_block",
                        lambda *a: "El certificado cuesta $ 5.000, vigente desde el 1/3/2026, "
                                   "con un recargo de $ 900.")
    problem = next(p for p in main.services.problems(doc_id) if p.rule == "r8-vigencia")
    r = c.post(f"/documents/{doc_id}/review", data={"block": problem.block,
                                                     "rule": problem.rule,
                                                     "answer": "desde marzo", "n": 0})
    assert "No se puede aceptar" in r.text
    assert c.post("/reviews/1/accept", data={"n": 0}).status_code == 409


def test_pages_render(client):
    c, _ = client
    assert c.get("/").status_code == 200
    assert "r6-moneda" in c.get("/rules").text
    assert c.get("/chat").status_code == 200


def test_concision_rule():
    from app.services import concision
    assert concision("Una oración corta.") == "green"
    assert concision(" ".join(["palabra"] * 35) + ".") == "yellow"
    assert concision(" ".join(["palabra"] * 160)) == "red"
