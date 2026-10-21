# Lab 17: resultados

Última corrida: 2026-10-20. 62 preguntas con respuesta en el corpus.

## Recuperación

| Base | Chunks | Denso: en el top 10 | Re-ranking: primero | Re-ranking: en el top 5 |
|---|---|---|---|---|
| Limpia (producción) | 1881 | 61/62 | 46/62 | 60/62 |
| Limpia sin ruta de títulos | 1881 | 57/62 | 38/62 | 56/62 |
| Bloques limpios, cortes fijos | 1263 | 62/62 | 49/62 | 62/62 |
| Sucia (texto crudo, cortes fijos) | 1280 | 58/62 | 41/62 | 57/62 |

## Respuestas (mismo modelo y mismo juez en las dos bases)

| Base | Correctas | Parciales | Incorrectas | Dijo que no sabe teniendo el dato | Se abstuvo sin respuesta en el corpus |
|---|---|---|---|---|---|
| Limpia (producción) | 48/62 | 7/62 | 7/62 | 6 | 10/10 |
| Sucia (texto crudo, cortes fijos) | 49/62 | 9/62 | 4/62 | 3 | 10/10 |

Modelos que respondieron: local/mlx-community/Qwen3.5-9B-4bit (144)

### Preguntas que cambian de una base a la otra

- **q01** ¿Cuánto sale sacar la licencia de conducir por primera vez en la Ciudad? — esperado: $42.230 — limpia: incorrecta — sucia: correcta: Para sacar la licencia por primera vez en la Ciudad tenés que pagar $42.230,00 por la solicitud de la licencia [2]. Además, tenés que hacer el curso de Educación Vial, el examen psicofísico, el teóric
- **q04** ¿Cuánto tiempo tengo para pagar la boleta de la licencia en CABA? — esperado: 48 horas — limpia: incorrecta — sucia: correcta: Tenés que abonar la boleta dentro de las 48 horas, según lo que dice el fragmento [1].
- **q05** ¿Un ex combatiente de Malvinas tiene que pagar la licencia de conducir en la Ciudad? — esperado: No, los veteranos de Malvinas están exceptuados del pago — limpia: correcta — sucia: parcial: No, un ex combatiente de Malvinas está exento del pago de los trámites de habilitación de prestación de servicios de vehículos en la Ciudad, pero los fragmentos no mencionan si esta exención aplica es
- **q10** ¿En qué dirección atiende el Registro Civil de la Ciudad y en qué horario? — esperado: Uruguay 753, lunes a viernes de 7:30 a 19 h — limpia: correcta — sucia: incorrecta: No tengo esa información en los documentos. Los fragmentos mencionan que el Archivo del Registro Civil de la Ciudad posee los libros parroquiales, pero no dan su dirección ni horario de atención, solo
- **q24** ¿Dónde queda la Dirección General de Tesorería y cuál es su horario? — esperado: Martín García 346, PB; lunes a viernes de 9:30 a 14:30 — limpia: parcial — sucia: correcta: La Dirección General de Tesorería está ubicada en Martin Garcia 346, PB y atiende de lunes a viernes de 9:30 a 14:30 h [1].
- **q28** ¿Qué edad hay que tener para entrar como afiliado voluntario a IOMA? — esperado: Entre 18 y 35 años — limpia: incorrecta — sucia: correcta: Para ingresar como afiliado tenés que tener entre 18 y 35 años de edad [1].
- **q29** ¿Cuántos meses sin pagar la cuota de IOMA tienen que pasar para que me den de baja? — esperado: Más de tres meses de mora — limpia: correcta — sucia: parcial: Tienen que pasar 90 días sin pagar la cuota para que te den de baja automáticamente. [5]
- **q32** ¿Cuánto vale el bono de consulta médica de IOMA en la categoría C? — esperado: $7.000 (más 10% para afiliados voluntarios) — limpia: parcial — sucia: correcta: El bono de consulta médica en la categoría C vale $ 7.000, aunque si tenés afiliación voluntaria te suman un 10% extra por el IVA [1].
- **q35** ¿Cuánto sale alquilar un casillero en el Registro de la Propiedad bonaerense? — esperado: $154.000 por año — limpia: incorrecta — sucia: correcta: Alquilar un casillero en el Registro de la Propiedad bonaerense cuesta $ 154.000 por año [1].
- **q42** Para dar de baja una exención en ARBA, ¿en qué formato subo los documentos? — esperado: Comprimidos en .rar o .zip — limpia: correcta — sucia: incorrecta: No tengo esa información en los documentos. Los fragmentos mencionan que los documentos deben presentarse en original, copia o copia certificada por Escribano/a [1], pero no especifican formatos digit
- **q48** Se me venció la licencia en Provincia, ¿hasta cuándo puedo renovarla sin hacer el trámite de original? — esperado: Hasta 3 meses (90 días corridos) de vencida — limpia: correcta — sucia: parcial: Podés renovar tu licencia hasta un mes antes de que se vence, ya que la diferencia con el trámite de original es solo administrativa [1]. Si pasados los 90 días de vencimiento, tenés que hacer el trám
- **q59** ¿Hasta qué edad puedo tener a mi hijo estudiante en la ObSBA? — esperado: De 21 a 25 años, con constancia de alumno regular — limpia: incorrecta — sucia: parcial: Podés tener a tu hijo estudiante afiliado hasta los 25 años, siempre que esté cursando estudios incorporados a la enseñanza oficial [1].

## Score tipo Jev sobre chunks al azar

100 chunks por base, Qwen3.5-4B por logprobs, dos órdenes. Rúbrica de 1 a 5:

1. Nada: es ruido (menús, pie de página, texto cortado) o no se entiende
2. Poco: hay datos sueltos pero sin saber a qué se refieren
3. A medias: se entiende el tema pero faltan partes para responder
4. Bastante: responde preguntas concretas aunque le falte algo de contexto
5. Todo: se entiende solo y tiene los datos con su contexto

| Base | Media | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|
| Limpia (producción) | 3.14 | 11 | 12 | 0 | 77 | 0 |
| Sucia (texto crudo, cortes fijos) | 2.94 | 13 | 31 | 1 | 55 | 0 |

Los tres chunks de la base sucia con menor puntaje:

- `caba-abl-exencion-jubilados#5` (1.28): 911 - Policía Ver todos los teléfonos Redes de la ciudad Facebook Instagram X YouTube LinkedIn TikTok Pinterest Footer Legales Boletín oficial Oficios judiciales Política de privac
- `caba-registro-civil-partidas-urgentes#5` (2.13): Te fue útil esta página? No me sirvió Sí, me fue útil Actual Paso 1 de 2 Paso 2 de 2 Completo Ayudanos a mejorar ¿En qué aspectos esta página no es útil? Es difícil encontrar secci
- `caba-ley-arancelaria-anexo#380` (2.45): 078-159D 40 078-159E 40 078-159F 40 078-160 40 078-161A 40 078-161B 40 078-162 40 078-163 40 078-REM 40 079-001 60 079-002 60 079-003 80 079-004A 40 079-004B 70 079-005A 60 079-005
