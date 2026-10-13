# Lab 12: Base vectorial a fondo

**La pregunta:** búsqueda exacta con numpy, un HNSW escrito a mano y Qdrant: ¿cuánto recall se
pierde a cambio de velocidad, y qué pasa cuando hay filtros?

## 1. Concepto

Buscar los vectores más parecidos a una pregunta es calcular la distancia contra **todos**
(búsqueda exacta). Con 15 mil vectores eso es una multiplicación de matrices y tarda 2 ms. Con
millones ya no: hacen falta índices **aproximados** (ANN), que miran una fracción de los
vectores y a veces se pierden alguno de los verdaderos más cercanos. Ese "a veces" se mide como
**recall contra la búsqueda exacta**.

**HNSW** (Hierarchical Navigable Small World) es el índice que usan casi todas las bases
vectoriales, Qdrant incluida:
- Un grafo donde cada vector está unido a sus M vecinos más cercanos. Buscar es caminar:
  desde un punto de entrada, pasar al vecino más cercano a la pregunta, y repetir.
- Para no cruzar todo el grafo a pasitos, hay **capas**: las de arriba tienen pocos nodos y
  saltos largos, la de abajo tiene todos y saltos cortos (como una skip list).
- `ef` es cuántos candidatos se mantienen mientras se camina: más `ef`, más recall y más
  lento.

`hnsw.py` lo implementa en unas 120 líneas para ver cada pieza.

**Filtros.** "Buscá solo en documentos de CABA" o "solo lo que este usuario puede ver". Hay dos
formas: buscar y después filtrar (post-filtro), o filtrar mientras se camina el grafo. La
primera es trivial y tiene una trampa que el lab mide.

## 2. Método

- **Vectores**: todos los chunks que generaron las 8 estrategias del lab 03, sin repetir:
  15.506 vectores reales de `bge-m3` (1024 dimensiones). Muchos son casi duplicados (el mismo
  texto cortado de formas parecidas), que es lo que pasa en un índice real con versiones.
- **Consultas**: las 72 preguntas de `evals/questions.jsonl`.
- **Verdad**: los 10 más cercanos según numpy exacto. Recall@10 = qué fracción de esos 10
  devuelve cada índice.
- **Índices**: numpy exacto, HNSW propio (M=16, ef_construction=100) con dos reglas para
  elegir vecinos, Qdrant en modo local (`QdrantClient(path=...)`) y el servidor de Qdrant
  1.19.2 (binario oficial para macOS, sin Docker) con los mismos M y ef_construction.
- **Filtros**: por jurisdicción (pasa la mitad de los vectores) y por documento (pasa el 1 %).

```bash
# el binario de Qdrant va en data/interim/qdrant-bin/ (gh release download -R qdrant/qdrant)
uv run labs/12-base-vectorial/run.py
```

## 3. Resultados

Números completos en [`results.md`](results.md). Recall@10 contra la búsqueda exacta:

| Índice | ef=10 | ef=50 | ef=200 | Construcción |
|---|---|---|---|---|
| HNSW propio, vecinos más cercanos | 56 % | 68 % | 77 % | 22 s |
| HNSW propio, **heurística de diversidad** | 77 % | 90 % | **97 %** | 442 s |
| Qdrant servidor (corrida 1 / corrida 2) | 87 % / 80 % | 96 % / 88 % | 99 % / 95 % | 12–36 s |
| Qdrant modo local | exacto: 99,7 % | | | 16 s |
| numpy exacto | 100 %, 2 ms por consulta | | | 0 s |

Filtros (recall contra la búsqueda exacta filtrada):

| Filtro | Top 10 y después filtrar | Top 100 y después filtrar | Qdrant, filtro durante la búsqueda |
|---|---|---|---|
| Jurisdicción (50 % pasa) | 92 % | 97 % | **99,8 %** |
| Un documento (1 % pasa) | 75 %, devuelve 7,6 de 10 | 95 % | **99,7 %** |

## 4. Conclusión

1. **Cómo se eligen los vecinos importa más que todo lo demás.** Con la regla obvia ("los M
   más cercanos"), los vecinos de un nodo son todos casi duplicados entre sí y el grafo queda
   partido en grupos que no se conectan: 77 % de recall aun mirando 1.170 vectores. Con la
   heurística del paper (aceptar un vecino solo si está más cerca del nodo que de los vecinos
   ya elegidos) los enlaces apuntan en direcciones distintas: 90 % con ef=50. Es la razón por
   la que este índice funciona en la práctica.
2. **Qdrant en modo local no tiene HNSW.** `QdrantClient(path=...)` es una implementación en
   Python que compara contra todos los vectores (lo dice su código y lo avisa al crear
   índices de payload). Es exacto y, a esta escala, alcanza; pero los índices y los filtros
   durante la búsqueda, que fueron la razón para elegir Qdrant en el SDD, existen solo en el
   servidor. **Problema para el diseño:** la app (lab 16) arranca en modo local por simpleza;
   pasar al servidor es cambiar la URL, pero hay que decidirlo antes de tener volumen.
3. **Post-filtrar pierde resultados justo cuando el filtro es selectivo.** Buscando el top 10
   y filtrando por documento, vuelven en promedio 7,6 resultados y se pierde un cuarto de los
   correctos. Para permisos esto es grave: un usuario con acceso a pocos documentos recibiría
   respuestas peores. Filtrar durante la búsqueda (Qdrant con índice de payload) no pierde
   nada. Confirma la decisión del SDD: **el filtro de permisos va en la base**.
4. **El recall de un índice aproximado no es un número fijo.** El mismo servidor, mismos
   datos y parámetros, dio 95 % y 99 % en dos construcciones (construye en paralelo y los
   niveles son aleatorios). Hay que medirlo con los datos propios y no confiar en un valor.
5. **A esta escala, numpy gana.** 15 mil vectores se buscan exactos en 2 ms. Un índice ANN
   empieza a pagar con cientos de miles de vectores.

### Límites
- La latencia de la segunda corrida está inflada: compartía la máquina con el lab 04.
- 72 consultas; los recall tienen un margen de un par de puntos.
