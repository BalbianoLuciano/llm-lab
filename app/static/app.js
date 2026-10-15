// Evaluation progress, block filters, upload dropzone, chat streaming and the review shortcuts.

function toast(message, label = "Error") {
  const slot = document.getElementById("toast-slot");
  if (!slot) return;
  const el = document.createElement("div");
  el.className = "toast";
  el.setAttribute("role", "alert");
  el.innerHTML = `<span class="label"></span><span></span>`;
  el.firstChild.textContent = label;
  el.lastChild.textContent = message;
  slot.replaceChildren(el);
  setTimeout(() => el.remove(), 9000);
}

const levelName = { green: "verde", yellow: "amarillo", red: "rojo" };

document.addEventListener("DOMContentLoaded", () => {
  // ---------------------------------------------------------------- upload dropzone
  const drop = document.getElementById("dropzone");
  if (drop) {
    const input = drop.querySelector("input[type=file]");
    const send = () => { document.getElementById("uploading").classList.add("on"); drop.submit(); };
    drop.addEventListener("click", (e) => { if (e.target !== input) input.click(); });
    input.addEventListener("change", () => input.files.length && send());
    ["dragenter", "dragover"].forEach((t) => drop.addEventListener(t, (e) => { e.preventDefault(); drop.classList.add("over"); }));
    ["dragleave", "drop"].forEach((t) => drop.addEventListener(t, (e) => { e.preventDefault(); drop.classList.remove("over"); }));
    drop.addEventListener("drop", (e) => { input.files = e.dataTransfer.files; if (input.files.length) send(); });
  }

  // ---------------------------------------------------------------- document: filters
  for (const button of document.querySelectorAll(".filters button")) {
    button.addEventListener("click", () => {
      document.querySelectorAll(".filters button").forEach((b) => b.classList.toggle("on", b === button));
      const f = button.dataset.filter;
      for (const block of document.querySelectorAll(".block")) {
        block.classList.toggle("hidden", f !== "all" && block.dataset.level !== f);
      }
    });
  }

  // ---------------------------------------------------------------- document: run the gate
  const evaluate = document.getElementById("evaluate");
  if (evaluate) {
    evaluate.addEventListener("click", () => {
      const bar = document.getElementById("progress");
      const text = document.getElementById("progress-text");
      bar.hidden = false; text.hidden = false;
      bar.classList.add("indeterminate");
      text.textContent = "Cargando el evaluador local (la primera vez tarda unos segundos)…";
      evaluate.disabled = true;
      let finished = false;
      const source = new EventSource(`/documents/${evaluate.dataset.doc}/evaluate`);
      source.onmessage = (msg) => {
        const e = JSON.parse(msg.data);
        if (e.error) { finished = true; source.close(); toast(e.error); evaluate.disabled = false; bar.hidden = true; return; }
        bar.classList.remove("indeterminate");
        bar.firstElementChild.style.width = `${(100 * e.done) / e.total}%`;
        const where = e.block === null || e.block < 0 ? "documento" : `bloque ${e.block}`;
        text.textContent = `${e.done} de ${e.total} · ${e.rule} · ${where} · ${levelName[e.level] || e.level}`;
        const el = e.block !== null && e.block >= 0 && document.getElementById(`b${e.block}`);
        if (el) {
          const rank = { none: 0, green: 1, yellow: 2, red: 3 };
          if (rank[e.level] > rank[el.dataset.level || "none"]) {
            el.classList.remove("none", "green", "yellow");
            el.classList.add(e.level);
            el.dataset.level = e.level;
          }
          el.classList.remove("flash"); void el.offsetWidth; el.classList.add("flash");
        }
        if (e.done === e.total) { finished = true; source.close(); text.textContent = "Listo. Actualizando…"; setTimeout(() => location.reload(), 500); }
      };
      source.onerror = () => { source.close(); if (!finished) location.reload(); };
    });
  }

  // ---------------------------------------------------------------- chat
  const ask = document.getElementById("ask");
  if (ask) {
    const input = ask.querySelector("input");
    const answer = document.getElementById("answer");
    const sources = document.getElementById("sources");
    const stages = document.getElementById("stages");
    const setStage = (name) => {
      const order = ["buscando", "respondiendo", "listo"];
      for (const s of stages.querySelectorAll("span")) {
        const i = order.indexOf(s.dataset.stage), j = order.indexOf(name);
        s.classList.toggle("on", i === j);
        s.classList.toggle("done", i < j);
        s.querySelector(".dot").className = `dot ${i < j ? "green" : i === j ? "yellow" : "none"}`;
      }
    };
    const run = (q) => {
      answer.textContent = ""; answer.classList.add("caret");
      sources.replaceChildren(); sources.hidden = true; stages.hidden = false;
      setStage("buscando");
      const button = ask.querySelector("button"); button.disabled = true;
      const source = new EventSource(`/chat/ask?q=${encodeURIComponent(q)}`);
      source.onmessage = (msg) => {
        const e = JSON.parse(msg.data);
        if (e.error) toast(e.error);
        if (e.stage) setStage(e.stage);
        if (e.token) answer.textContent += e.token;
        if (e.done) {
          source.close(); button.disabled = false; answer.classList.remove("caret"); setStage("listo");
          // citations [n] become small superscripts
          answer.innerHTML = answer.textContent.replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]))
            .replace(/[\[【](\d+)[\]】]/g, '<span class="cite">[$1]</span>');
          for (const s of e.sources || []) {
            const li = document.createElement("li");
            li.innerHTML = `<span class="n"></span><div><span class="label"></span><p></p></div>`;
            li.querySelector(".n").textContent = s.n;
            li.querySelector(".label").textContent = `${s.doc}${s.path ? " · " + s.path : ""}`;
            li.querySelector("p").textContent = s.text;
            sources.appendChild(li);
          }
          sources.hidden = !(e.sources || []).length;
        }
      };
      source.onerror = () => { source.close(); button.disabled = false; answer.classList.remove("caret"); };
    };
    ask.addEventListener("submit", (ev) => { ev.preventDefault(); if (input.value.trim()) run(input.value.trim()); });
    for (const b of document.querySelectorAll(".suggestions button")) {
      b.addEventListener("click", () => { input.value = b.textContent; run(b.textContent); });
    }
  }

  // ---------------------------------------------------------------- review: keyboard
  const review = document.querySelector(".review");
  if (review) {
    const { doc, n, total } = review.dataset;
    const go = (k) => { location.href = `/documents/${doc}/review?n=${k}`; };
    document.addEventListener("keydown", (ev) => {
      const typing = ev.target.tagName === "TEXTAREA" || ev.target.tagName === "INPUT";
      const accept = document.getElementById("accept-form");
      if (ev.key === "Enter" && !ev.shiftKey && accept) {
        ev.preventDefault(); accept.submit();
      } else if (ev.key === "Escape" || (!typing && ev.key === "n")) {
        go(Math.min(Number(n) + 1, Number(total) - 1));
      } else if (!typing && ev.key === "p") {
        go(Math.max(Number(n) - 1, 0));
      }
    });
  }
});

// htmx: show failed requests instead of failing silently
document.addEventListener("htmx:responseError", (e) => toast(`El servidor respondió ${e.detail.xhr.status}.`));
document.addEventListener("htmx:sendError", () => toast("No hay conexión con el servidor."));
