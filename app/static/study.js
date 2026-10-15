// "Estudio" reader: render the Markdown, keep links between documents inside the reader,
// build the "on this page" index and highlight the section being read.
(function () {
  const article = document.getElementById("markdown");
  const source = document.getElementById("markdown-source");
  if (!article || !source) return;
  const doc = article.dataset.doc;
  const lang = article.dataset.lang;

  // The template escapes the Markdown; a textarea decodes it back to the original text
  article.innerHTML = marked.parse(source.value, { gfm: true });

  // ---------------------------------------------------------------- links
  const base = new URL(doc, "http://repo/");
  for (const a of article.querySelectorAll("a[href]")) {
    const href = a.getAttribute("href");
    if (/^(https?:|mailto:|#)/.test(href)) {
      if (/^https?:/.test(href)) { a.target = "_blank"; a.rel = "noopener"; }
      continue;
    }
    let path = decodeURIComponent(new URL(href, base).pathname).replace(/^\//, "");
    if (path.endsWith("/")) path += "README.md";
    if (path.endsWith(".en.md")) path = path.replace(/\.en\.md$/, ".md");
    if (path.endsWith(".md")) {
      a.href = `/estudio?doc=${encodeURIComponent(path)}&lang=${lang}`;
    } else {
      // code and data files: open them on GitHub
      a.href = `https://github.com/BalbianoLuciano/llm-lab/blob/main/${path}`;
      a.target = "_blank"; a.rel = "noopener";
    }
  }

  // ---------------------------------------------------------------- "on this page"
  const toc = document.getElementById("toc");
  const headings = [...article.querySelectorAll("h2, h3")];
  const slug = (t) => t.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "")
    .replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
  const used = new Set();
  for (const h of headings) {
    let id = slug(h.textContent) || "seccion";
    while (used.has(id)) id += "-";
    used.add(id); h.id = id;
    if (toc) {
      const a = document.createElement("a");
      a.href = `#${id}`; a.textContent = h.textContent; a.className = h.tagName.toLowerCase();
      toc.appendChild(a);
    }
  }
  if (toc && headings.length < 2) toc.hidden = true;

  if (toc && "IntersectionObserver" in window) {
    const links = new Map([...toc.querySelectorAll("a")].map((a) => [a.getAttribute("href").slice(1), a]));
    const observer = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          links.forEach((a) => a.classList.remove("on"));
          links.get(entry.target.id)?.classList.add("on");
        }
      }
    }, { rootMargin: "-80px 0px -70% 0px" });
    headings.forEach((h) => observer.observe(h));
  }
})();
