// Evaluation progress (SSE), chat streaming (SSE) and the review keyboard shortcuts.

function streamJSON(url, onEvent) {
  const source = new EventSource(url);
  source.onmessage = (msg) => {
    const event = JSON.parse(msg.data);
    onEvent(event);
    if (event.done === true || (event.total && event.done === event.total)) source.close();
  };
  source.onerror = () => source.close();
  return source;
}

document.addEventListener("DOMContentLoaded", () => {
  // Document screen: run the quality gate and show progress
  const evaluate = document.getElementById("evaluate");
  if (evaluate) {
    evaluate.addEventListener("click", () => {
      const bar = document.getElementById("progress");
      const text = document.getElementById("progress-text");
      bar.hidden = false;
      evaluate.disabled = true;
      const source = new EventSource(`/documents/${evaluate.dataset.doc}/evaluate`);
      source.onmessage = (msg) => {
        const e = JSON.parse(msg.data);
        bar.max = e.total;
        bar.value = e.done;
        text.textContent = `${e.done}/${e.total} · ${e.rule} · ${e.level}`;
        const el = e.block !== null && document.getElementById(`b${e.block}`);
        if (el && e.level !== "green") el.classList.add(e.level);
      };
      source.onerror = () => { source.close(); location.reload(); };
    });
  }

  // Chat screen: stream the answer, then list the cited sources
  const ask = document.getElementById("ask");
  if (ask) {
    ask.addEventListener("submit", (ev) => {
      ev.preventDefault();
      const q = new FormData(ask).get("q");
      const answer = document.getElementById("answer");
      const sources = document.getElementById("sources");
      const stage = document.getElementById("stage");
      answer.textContent = "";
      sources.innerHTML = "";
      streamJSON(`/chat/ask?q=${encodeURIComponent(q)}`, (e) => {
        if (e.stage) stage.textContent = e.stage === "buscando" ? "Buscando en los documentos…" : "Respondiendo…";
        if (e.token) answer.textContent += e.token;
        if (e.done) {
          stage.textContent = e.abstained ? "No encontré la respuesta en los documentos." : "";
          for (const s of e.sources) {
            const li = document.createElement("li");
            li.value = s.n;
            li.innerHTML = `<b></b> <small></small><p></p>`;
            li.querySelector("b").textContent = s.doc;
            li.querySelector("small").textContent = s.path;
            li.querySelector("p").textContent = s.text;
            sources.appendChild(li);
          }
        }
      });
    });
  }

  // Review screen: n / p to move, Enter to accept the proposal, Esc to skip
  const review = document.querySelector(".review");
  if (review) {
    const { doc, n, total } = review.dataset;
    const go = (k) => { location.href = `/documents/${doc}/review?n=${k}`; };
    document.addEventListener("keydown", (ev) => {
      const typing = ev.target.tagName === "TEXTAREA" || ev.target.tagName === "INPUT";
      if (ev.key === "Enter" && !ev.shiftKey && document.getElementById("accept-form")) {
        ev.preventDefault();
        document.getElementById("accept-form").submit();
      } else if (ev.key === "Escape" || (!typing && ev.key === "n")) {
        go(Math.min(Number(n) + 1, Number(total) - 1));
      } else if (!typing && ev.key === "p") {
        go(Math.max(Number(n) - 1, 0));
      }
    });
  }
});
