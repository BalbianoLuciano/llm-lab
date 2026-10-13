# Lab 14: resultados

Última corrida: 2026-10-13. 30 reglas en lenguaje natural: 24 compilables y 6 vagas.

| Modelo | Esquema válido | Vagas detectadas | Compilables marcadas vagas | kind | scope | blocking | applies_to (Jaccard) | Norma correcta | Todo bien sin editar | Intentos medios |
|---|---|---|---|---|---|---|---|---|---|---|
| groq/qwen/qwen3.8-27b | 30/30 | 6/6 | 0/24 | 96% | 92% | 100% | 0.89 | 100% | 14/24 | 1.00 |
| groq/openai/gpt-oss-120b | 30/30 | 6/6 | 0/24 | 46% | 92% | 100% | 0.73 | 100% | 2/24 | 1.00 |
| nvidia/z-ai/glm-5.3 | 12/12 | 6/6 | 0/6 | 100% | 83% | 100% | 0.94 | 100% | 4/6 | 1.00 |

## Diferencias con la referencia (primer modelo)

- r3-enlaces: applies_to: ['paragraph', 'list_item'] (ref ['paragraph', 'list_item', 'table'])
- r7-fechas: kind: deterministic (ref semantic)
- r9-emisor-fecha: applies_to: ['paragraph', 'heading'] (ref ['heading', 'paragraph', 'list_item', 'table'])
- r10-proposito: applies_to: ['heading', 'paragraph'] (ref ['heading', 'paragraph', 'list_item'])
- r11-pasos-listas: scope: document (ref block)
- horarios-atencion: scope: document (ref block)
- plazo-respuesta: applies_to: ['paragraph', 'list_item', 'table'] (ref ['paragraph', 'list_item'])
- requisitos-antes-pasos: applies_to: ['heading', 'paragraph', 'list_item', 'table'] (ref ['heading', 'paragraph', 'list_item'])
- lenguaje-inclusivo-consistente: applies_to: ['heading', 'paragraph', 'list_item', 'table'] (ref ['paragraph', 'list_item'])
- correos-validos: applies_to: ['paragraph', 'list_item'] (ref ['paragraph', 'list_item', 'table'])
- vaga «Que el documento sea claro.» → ambiguous: La regla 'que el documento sea claro' es demasiado vaga para ser evaluada de forma verificable. Por favor, especificá un criterio concreto (
- vaga «Los textos tienen que estar bien escritos y verse profesionales.» → ambiguous: La regla 'bien escritos y verse profesionales' es subjetiva y no tiene un criterio verificable concreto. Por favor, especificá qué aspectos 
- vaga «Que sea amigable para el ciudadano.» → ambiguous: La expresión 'amigable para el ciudadano' es subjetiva y no define un criterio verificable. Por favor, especificá qué aspecto concreto queré
- vaga «El documento no puede tener errores.» → ambiguous: La regla 'no puede tener errores' es demasiado vaga para ser evaluada de forma verificable. ¿A qué tipo de errores te referís exactamente? P
- vaga «Que la información esté completa.» → ambiguous: La regla 'que la información esté completa' es demasiado vaga para ser evaluada de forma verificable. ¿Podés especificar qué campos o datos 
- vaga «Evitar textos aburridos.» → ambiguous: La expresión 'textos aburridos' es subjetiva y no permite una evaluación verificable. Por favor, especificá un criterio concreto (por ejempl
