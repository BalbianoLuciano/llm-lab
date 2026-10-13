# Lab 11: resultados

Última corrida: 2026-10-12. Set de oro: 6 documentos etiquetados a mano (`gold.json`).

## 1. Contra el set de oro

| Métrica | manual | docling |
|---|---|---|
| Títulos encontrados (recall) | 66% (23/35) | 63% (22/35) |
| Títulos correctos (precisión) | 83% (25/30) | 88% (23/26) |
| Ítems de lista como ítem | 86% (31/36) | 100% (36/36) |
| Tablas encontradas | 100% (2/2) | 100% (2/2) |
| Tablas con todas sus filas | 50% (1/2) | 100% (2/2) |
| Tablas de más (falsos positivos) | 60% (3/5) | 33% (1/3) |
| Enlaces con su URL | 90% (9/10) | 100% (10/10) |
| Datos clave presentes en el texto | 97% (29/30) | 97% (29/30) |
| Ruido de la web que se coló (menos es mejor) | 0% (0/8) | 0% (0/8) |
| Encabezados/pies repetidos (menos es mejor) | 2 | 12 |

Por documento (títulos recall / precisión · ítems · tablas · enlaces · datos):

| Documento | manual | docling |
|---|---|---|
| caba-licencias-exencion-bui-jubilados | 2/3 · 2/2 · 0/0 · 1/1 · 0/0 · 4/4 | 2/3 · 2/2 · 0/0 · 1/1 · 0/0 · 4/4 |
| pba-arba-baja-exencion | 6/9 · 9/10 · 12/17 · 1/1 · 2/2 · 5/5 | 9/9 · 11/11 · 17/17 · 1/1 · 2/2 · 5/5 |
| caba-resolucion-tarifas-colectivos-julio-2026 | 3/3 · 2/2 · 0/0 · 0/0 · 0/0 · 5/5 | 3/3 · 2/2 · 0/0 · 0/0 · 0/0 · 5/5 |
| caba-licencias-aranceles | 4/4 · 4/4 · 9/9 · 0/0 · 3/3 · 5/5 | 2/4 · 2/2 · 9/9 · 0/0 · 3/3 · 5/5 |
| caba-registro-civil-partidas-urgentes | 6/14 · 6/9 · 10/10 · 0/0 · 4/5 · 6/7 | 6/14 · 6/9 · 10/10 · 0/0 · 5/5 · 6/7 |
| pba-transporte-formulario-d-sube | 2/2 · 2/3 · 0/0 · — · 0/0 · 4/4 | 0/2 · 0/0 · 0/0 · — · 0/0 · 4/4 |

## 2. Todo el corpus

| | manual | docling |
|---|---|---|
| Documentos parseados | 49 | 49 |
| Bloques | 4986 | 5618 |
| Títulos | 1135 | 965 |
| Ítems de lista | 1145 | 1355 |
| Tablas | 414 | 408 |
| Enlaces | 264 | 222 |
| Docs sin ningún título | 3 | 8 |
| Tiempo total (s) | 86 | 1490 |
| Segundos por página PDF (mediana) | 0.06 | 0.40 |
| Segundos por documento no PDF (mediana) | 0.01 | 0.04 |
