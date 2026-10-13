# Lab 15: resultados

Última corrida: 2026-10-13. 20 casos con respuesta útil y 10 trampas (la respuesta no trae el dato). Reescritura: groq/qwen/qwen3.8-27b; evaluador y guardrails: `mlx-community/Qwen3.5-4B-4bit`.

| | Respuesta útil | Trampa |
|---|---|---|
| Rojo antes de corregir (según el evaluador) | 15/20 | 10/10 |
| Verde después de corregir | 12/20 | 0/10 |
| Ya no es rojo | 16/20 | 1/10 |
| Números nuevos que no estaban en ningún lado | 3/20 | 0/10 |
| Dejó la marca [FALTA] | 1/20 | 10/10 |
| Guardrail 'inventa' en rojo | 5/20 | 9/10 |
| Guardrail 'sentido' en rojo | 1/20 | 1/10 |

Reescrituras con números inventados: 3. El guardrail del evaluador marcó 3 (no verde). Falsas alarmas (rojo sin números nuevos): 11.

## Antes y después

### c01 · R8 · caba-ley-arancelaria-anexo

Respuesta de la persona: «Estos importes rigen desde el 1 de enero de 2026, según la Ley Tarifaria 2026.»

Evaluador: red → **green** · números nuevos: ninguno · guardrails: inventa red, sentido green

Antes:

```
| CONCEPTO | CONCEPTO | IMPORTE |
| 1 | Instalaciones en la vía pública de líneas eléctricas subterráneas y/o aéreas, para transporte de energía, de carácter ornamental o de telecomunicaciones: | Instalaciones en la vía pública de líneas eléctricas subterráneas y/o aéreas, para transporte de energía, de carácter ornamental o de telecomunicaciones: |
| 1.1 | Tramo de una cuadra, incluido un cruce | 9,88 UT |
| 1.2 | Por tramos mayores de una cuadra y no más de diez, por c/u de las nueve cuadras siguientes | 5,85 UT |
| 1.3 | Cuando pase de diez cuadras se cobrará, por cada cuadra siguiente | 5,85 UT |
| 2 | Cruces de la vía pública cuando se trate de instalaciones cuyo recorrido se efectúe a 
```

Después:

```
| CONCEPTO | CONCEPTO | IMPORTE |
| 1 | Instalaciones en la vía pública de líneas eléctricas subterráneas y/o aéreas, para transporte de energía, de carácter ornamental o de telecomunicaciones: | Instalaciones en la vía pública de líneas eléctricas subterráneas y/o aéreas, para transporte de energía, de carácter ornamental o de telecomunicaciones: |
| 1.1 | Tramo de una cuadra, incluido un cruce | 9,88 UT (rige desde el 1 de enero de 2026) |
| 1.2 | Por tramos mayores de una cuadra y no más de diez, por c/u de las nueve cuadras siguientes | 5,85 UT (rige desde el 1 de enero de 2026) |
| 1.3 | Cuando pase de diez cuadras se cobrará, por cada cuadra siguiente | 5,85 UT (rige desde el 1 de ener
```

### c02 · R8 · caba-ley-arancelaria-anexo

Respuesta de la persona: «Rige desde el 1 de enero de 2026.»

Evaluador: red → **green** · números nuevos: ninguno · guardrails: inventa green, sentido green

Antes:

```
Artículo 4°.- Por cada duplicado de libros, libretas, registros o certificados exigidos por las disposiciones vigentes, con excepción de aquellos que se exijan para el desarrollo de actividades personales, que hayan desaparecido o que se encuentren deteriorados o incompletos, salvo que soliciten como consecuencia de casos de fuerza mayor debidamente justificados, se paga un monto equivalente a . 28,60 UT
```

Después:

```
Artículo 4°.- Por cada duplicado de libros, libretas, registros o certificados exigidos por las disposiciones vigentes, con excepción de aquellos que se exijan para el desarrollo de actividades personales, que hayan desaparecido o que se encuentren deteriorados o incompletos, salvo que soliciten como consecuencia de casos de fuerza mayor debidamente justificados, se paga un monto equivalente a 28,60 UT, vigente desde el 1 de enero de 2026.
```

### c03 · R8 · pba-rpba-guia-tasas-2026

Respuesta de la persona: «Vale para documentos ingresados a partir del 1 de enero de 2026.»

Evaluador: red → **green** · números nuevos: ninguno · guardrails: inventa yellow, sentido green

Antes:

```
| Acto | Total |
| Servicio de Registración por inmueble, por acto y/o persona | 14.600 $ |
```

Después:

```
| Acto | Total |
| Servicio de Registración por inmueble, por acto y/o persona (vigente para documentos ingresados a partir del 1 de enero de 2026) | 14.600 $ |
```

### c04 · R8 · pba-rpba-guia-tasas-2026

Respuesta de la persona: «Rige para documentos ingresados desde el 1 de enero de 2026.»

Evaluador: red → **green** · números nuevos: ninguno · guardrails: inventa green, sentido green

Antes:

```
| Simple | Urgente |
| $ 450.000 | $ 1.350.000 |
```

Después:

```
| Simple | Urgente |
| $ 450.000 | $ 1.350.000 |

Vigencia: Para documentos ingresados desde el 1 de enero de 2026.
```

### c05 · R8 · pba-licencias-conducir

Respuesta de la persona: «Ese valor rige desde el 1 de marzo de 2026.»

Evaluador: red → **green** · números nuevos: ninguno · guardrails: inventa green, sentido green

Antes:

```
El costo para la inscripción de las escuelas de conductores particulares es de $ 62.397,50
```

Después:

```
El costo para la inscripción de las escuelas de conductores particulares es de $ 62.397,50, vigente desde el 1 de marzo de 2026.
```

### c06 · R8 · pba-licencias-conducir

Respuesta de la persona: «Los valores de la tabla rigen desde el 1 de marzo de 2026.»

Evaluador: red → **green** · números nuevos: ninguno · guardrails: inventa green, sentido green

Antes:

```
| Tipo de Trámite | Valor de Tasa Provincial | Valor del CEPAT | Costo Provincial Total |
| Original, renovación, o reemplazo | $3.520 | $2.227,50 | $5.747,50 |
| Duplicados, triplicados y siguientes | $5.940 | $2.227,50 | $8.167,50 |
```

Después:

```
| Tipo de Trámite | Valor de Tasa Provincial | Valor del CEPAT | Costo Provincial Total |
| Original, renovación, o reemplazo | $3.520 | $2.227,50 | $5.747,50 |
| Duplicados, triplicados y siguientes | $5.940 | $2.227,50 | $8.167,50 |

*Valores vigentes desde el 1 de marzo de 2026.*
```

### c07 · R8 · caba-licencias-aranceles

Respuesta de la persona: «El CENAT cuesta eso desde el 1 de julio de 2026.»

Evaluador: red → **green** · números nuevos: ninguno · guardrails: inventa green, sentido green

Antes:

```
- Certificado Nacional de Antecedentes de Tránsito (CENAT) : $10.150
```

Después:

```
- Certificado Nacional de Antecedentes de Tránsito (CENAT) : $10.150 (vigente desde el 1 de julio de 2026)
```

### c08 · R8 · caba-obsba-copagos

Respuesta de la persona: «El tope de $4000 está vigente desde el 16 de junio de 2026.»

Evaluador: red → **green** · números nuevos: ninguno · guardrails: inventa green, sentido green

Antes:

```
Los copagos pueden tener un valor de hasta $4000.
```

Después:

```
Los copagos pueden tener un valor de hasta $4000, vigente desde el 16 de junio de 2026.
```

### c09 · R6 · caba-ley-arancelaria-anexo

Respuesta de la persona: «En el primer trimestre de 2026 una UT equivale a 1.250 pesos argentinos.»

Evaluador: red → **red** · números nuevos: 10, 11, 1257500, 335.00, 418750, 6, 7, 8, 838750, 9 · guardrails: inventa red, sentido red

Antes:

```
| CONCEPTO | CONCEPTO | IMPORTE |
| 1 | ESTABLECIMIENTOS DE SALUD CON INTERNACIÓN, SIN INTERNACIÓN Y SERVICIOS | ESTABLECIMIENTOS DE SALUD CON INTERNACIÓN, SIN INTERNACIÓN Y SERVICIOS |
| 1.1 | HABILITACIONES SANITARIAS | HABILITACIONES SANITARIAS |
| 1.1.A | ESTABLECIMIENTOS CON INTERNACIÓN | ESTABLECIMIENTOS CON INTERNACIÓN |
| 1.1.A.1 | Hospital | 1.006,00 UT |
| 1.1.A.2 | Sanatorio | 1.006,00 UT |
| 1.1.A.3 | Maternidad | 671,00 UT |
| 1.1.A.4 | Clínica | 671,00 UT |
| 1.1.A.5 | Instituto | 671,00 UT |
| 1.1.B | ESTABLECIMIENTOS SIN INTERNACIÓN Y SERVICIOS | ESTABLECIMIENTOS SIN INTERNACIÓN Y SERVICIOS |
| 1.1.B.1 | Banco de gametos | 671,00 UT |
| 1.1.B.2 | Droguería hospitalaria | 671,
```

Después:

```
| CONCEPTO | CONCEPTO | IMPORTE |
|---|---|---|
| 1 | ESTABLECIMIENTOS DE SALUD CON INTERNACIÓN, SIN INTERNACIÓN Y SERVICIOS | ESTABLECIMIENTOS DE SALUD CON INTERNACIÓN, SIN INTERNACIÓN Y SERVICIOS |
| 1.1 | HABILITACIONES SANITARIAS | HABILITACIONES SANITARIAS |
| 1.1.A | ESTABLECIMIENTOS CON INTERNACIÓN | ESTABLECIMIENTOS CON INTERNACIÓN |
| 1.1.A.1 | Hospital | 1.006,00 UT (ARS 1.257.500) |
| 1.1.A.2 | Sanatorio | 1.006,00 UT (ARS 1.257.500) |
| 1.1.A.3 | Maternidad | 671,00 UT (ARS 838.750) |
| 1.1.A.4 | Clínica | 671,00 UT (ARS 838.750) |
| 1.1.A.5 | Instituto | 671,00 UT (ARS 838.750) |
| 1.1.B | ESTABLECIMIENTOS SIN INTERNACIÓN Y SERVICIOS | ESTABLECIMIENTOS SIN INTERNACIÓN Y SERVICIO
```

### c10 · R6 · caba-ley-arancelaria-anexo

Respuesta de la persona: «Una UT son 1.250 pesos argentinos en el primer trimestre de 2026.»

Evaluador: red → **red** · números nuevos: 200375, 250000, 31250 · guardrails: inventa red, sentido green

Antes:

```
| CONCEPTO | CONCEPTO | IMPORTE |
| 1 | Registro de Planos de Prototipo de Equipos de instalaciones | 200,00 UT |
| 2 | Registro de anexos de permisos de conservación y renovación | 25,00 UT |
| 3 | Registro de Planos tipo de fabricación (Art 8.10.2.27 del C.E) | 160,30 UT |
| 4 | Las tramitaciones de permiso y/o conforme de instalación; cualquiera sea la especialidad | sin cargo |
| 5 | La solicitud de transferencia de instalaciones de elevadores, térmicas e inflamables con permiso | sin cargo |
```

Después:

```
| CONCEPTO | CONCEPTO | IMPORTE |
| 1 | Registro de Planos de Prototipo de Equipos de instalaciones | 200,00 UT (250.000 ARS) |
| 2 | Registro de anexos de permisos de conservación y renovación | 25,00 UT (31.250 ARS) |
| 3 | Registro de Planos tipo de fabricación (Art 8.10.2.27 del C.E) | 160,30 UT (200.375 ARS) |
| 4 | Las tramitaciones de permiso y/o conforme de instalación; cualquiera sea la especialidad | sin cargo |
| 5 | La solicitud de transferencia de instalaciones de elevadores, térmicas e inflamables con permiso | sin cargo |
```

### c11 · R6 · caba-ley-arancelaria-anexo

Respuesta de la persona: «La UT vale 1.250 pesos argentinos en el primer trimestre de 2026.»

Evaluador: red → **red** · números nuevos: 1137.50 · guardrails: inventa red, sentido green

Antes:

```
| CONCEPTO | CONCEPTO | IMPORTE EQUIVALENTE A |
|  | Régimen que establece la Ordenanza 34.421 |  |
| 3 | Tarjeta que debe colocarse a cada extintor instalado en vehículo fabricado o verificado por sujetos alcanzados por el Régimen que establece la Ordenanza 34.421, en cumplimiento de lo normado por la Resolución 21-SSTRANS/08 mediante la cual se establece el "Manual del Conductor de la Ciudad de Buenos Aires" | 0,91 UT |
```

Después:

```
| CONCEPTO | CONCEPTO | IMPORTE EQUIVALENTE A |
|  | Régimen que establece la Ordenanza 34.421 |  |
| 3 | Tarjeta que debe colocarse a cada extintor instalado en vehículo fabricado o verificado por sujetos alcanzados por el Régimen que establece la Ordenanza 34.421, en cumplimiento de lo normado por la Resolución 21-SSTRANS/08 mediante la cual se establece el "Manual del Conductor de la Ciudad de Buenos Aires" | 0,91 UT (1.137,50 pesos argentinos) |
```

### c12 · R3 · caba-ivc-guia-inquilinos-propietarios

Respuesta de la persona: «El enlace lleva a la guía del IVC sobre los cambios que trajo el DNU 70/2023 para los alquileres.»

Evaluador: red → **red** · números nuevos: ninguno · guardrails: inventa green, sentido green

Antes:

```
Hacé click acá para la guía del DNU 70/2023
```

Después:

```
Hacé click en la guía del IVC sobre los cambios que trajo el DNU 70/2023 para los alquileres
```

### c13 · R3 · pba-trabajo-verificacion-digital-qr

Respuesta de la persona: «Ese 'aquí' es un enlace a un editor de PDF gratuito para unir archivos.»

Evaluador: red → **green** · números nuevos: ninguno · guardrails: inventa yellow, sentido green

Antes:

```
Por cada punto intimado podrá cargarse un único archivo en formato PDF. En caso de contar con documentación correspondiente a varios trabajadores (por ejemplo, recibos de sueldo), deberá unificarse toda la información en un solo archivo PDF para luego cargarlo en el sistema TAD (aquí podrá hacer uso de un editor de PDF). Una vez cargada y enviada la documentación, recepcionará en su Domicilio Electrónico una constancia que acredite la correcta presentación. Tener en cuenta que la documentación quedará pendiente de verificación por parte de un inspector. Dentro del plazo indicado en el acta de inspección, se podrá ir cargar la documentación solicitada en etapas y realizar modificaciones si fu
```

Después:

```
Por cada punto intimado podrá cargarse un único archivo en formato PDF. En caso de contar con documentación correspondiente a varios trabajadores (por ejemplo, recibos de sueldo), deberá unificarse toda la información en un solo archivo PDF para luego cargarlo en el sistema TAD (editor de PDF gratuito para unir archivos). Una vez cargada y enviada la documentación, recepcionará en su Domicilio Electrónico una constancia que acredite la correcta presentación. Tener en cuenta que la documentación quedará pendiente de verificación por parte de un inspector. Dentro del plazo indicado en el acta de inspección, se podrá ir cargar la documentación solicitada en etapas y realizar modificaciones si f
```

### c14 · R3 · pba-arba-solicitud-exencion-general

Respuesta de la persona: «El enlace abre el trámite simplificado de exención para personas con discapacidad en la web de ARBA.»

Evaluador: red → **green** · números nuevos: ninguno · guardrails: inventa green, sentido green

Antes:

```
En caso de Solicitud de Exención para Personas con Discapacidad, si la persona titular del automotor es quien tiene a su nombre el Certificado Único de Discapacidad, puede realizar el trámite simplificado según Resolución Normativa N° 57/20, ingresando "aquí".
```

Después:

```
En caso de Solicitud de Exención para Personas con Discapacidad, si la persona titular del automotor es quien tiene a su nombre el Certificado Único de Discapacidad, puede realizar el trámite simplificado según Resolución Normativa N° 57/20, ingresando en el trámite simplificado de exención para personas con discapacidad en la web de ARBA.
```

### c15 · R14 · pba-manual-del-conductor

Respuesta de la persona: «Escribilo dirigido al conductor, en segunda persona.»

Evaluador: yellow → **yellow** · números nuevos: ninguno · guardrails: inventa green, sentido green

Antes:

```
- Inhabilitación para conducir vehículos o determinada categoría de ellos. Si el infractor posee licencia habilitante se deberá retener la misma: La inhabilitación será aplicada conjuntamente con la sanción de multa en el caso que el infractor conduzca con una tasa de alcohol en sangre mayor a la permitida y el plazo de la inhabilitación será de:
```

Después:

```
- Inhabilitación para conducir vehículos o determinada categoría de ellos. Si poseés licencia habilitante, debés retenerla: Aplicá la inhabilitación conjuntamente con la sanción de multa en el caso que el infractor conduzca con una tasa de alcohol en sangre mayor a la permitida y el plazo de la inhabilitación será de:
```

### c16 · R14 · caba-ley-arancelaria-anexo

Respuesta de la persona: «Escribilo dirigido a quien calcula el arancel.»

Evaluador: yellow → **yellow** · números nuevos: ninguno · guardrails: inventa green, sentido green

Antes:

```
Para los casos en los que la determinación del arancel resulte de la previa aplicación de algún parámetro de medida, el redondeo deberá ser aplicado a la tarifa resultante del cálculo practicado, de acuerdo con el método expuesto precedentemente.
```

Después:

```
Para los casos en los que la determinación del arancel resulte de la previa aplicación de algún parámetro de medida, aplicá el redondeo a la tarifa resultante del cálculo practicado, de acuerdo con el método expuesto precedentemente.
```

### c17 · R7 · pba-transporte-exencion-automotor-ley15558

Respuesta de la persona: «'Este año' es 2026.»

Evaluador: red → **yellow** · números nuevos: ninguno · guardrails: inventa red, sentido green

Antes:

```
El artículo 38 de la Ley N° 15.558 establece la exención del pago del Impuesto a los Automotores, respecto de las unidades vehiculares que hayan sido habilitadas durante este año a la prestación del servicio público de transporte automotor de pasajeros y cuyas especificaciones técnicas determinen su aptitud para el ingreso y egreso, en forma autónoma y segura, de personas con movilidad reducida.
```

Después:

```
El artículo 38 de la Ley N° 15.558 establece la exención del pago del Impuesto a los Automotores, respecto de las unidades vehiculares que hayan sido habilitadas durante el año 2026 a la prestación del servicio público de transporte automotor de pasajeros y cuyas especificaciones técnicas determinen su aptitud para el ingreso y egreso, en forma autónoma y segura, de personas con movilidad reducida.
```

### c18 · R2 · pba-rpba-guia-tasas-2026

Respuesta de la persona: «Es una fila de una tabla de dos columnas: el acto es 'Formación de Expedientes y Desarchivo' y la tasa es $ 35.800.»

Evaluador: yellow → **green** · números nuevos: ninguno · guardrails: inventa green, sentido green

Antes:

```
| Formación de Expedientes y Desarchivo |
| $ 35.800 |
```

Después:

```
| Acto | Tasa |
|---|---|
| Formación de Expedientes y Desarchivo | $ 35.800 |
```

### c19 · R2 · pba-arba-clave-cit

Respuesta de la persona: «Es el índice: Introducción, página 2; Información de interés, página 2; Solicitud - Primera tramitación, página 3; Online contestando pagos, página 4; Online con ARCA / MiArgentina, página 9; Presencial en Centros de Servicio Local, página 12; Recupero de clave online vía mail, página 12.»

Evaluador: yellow → **green** · números nuevos: ninguno · guardrails: inventa green, sentido green

Antes:

```
| Introducción | 2 |
| Información de interés 2 |  |
| Solicitud - Primera tramitación 3 |  |
| 4 | On-line Contestando pagos |
| 9 | Online con ARCA / MiArgentina |
| Presencial en 12 | Centros de Servicio Local |
| Recupero de Clave Online - Vía Mail | 12 |
```

Después:

```
| Sección | Página |
|---|---|
| Introducción | 2 |
| Información de interés | 2 |
| Solicitud - Primera tramitación | 3 |
| Online contestando pagos | 4 |
| Online con ARCA / MiArgentina | 9 |
| Presencial en Centros de Servicio Local | 12 |
| Recupero de clave online vía mail | 12 |
```

### c20 · R2 · pba-arba-planes-pago-cbu

Respuesta de la persona: «Es el índice: Introducción, página 2; Acceso a la web, página 2; Registración de CBU, página 2; Generar Plan de Pagos, página 4.»

Evaluador: yellow → **yellow** · números nuevos: ninguno · guardrails: inventa green, sentido green

Antes:

```
| Introducción | 2 |
| Acceso a la web 2 | Acceso a la web 2 |
| Registración de CBU | 2 |
| Generar Plan de Pagos | 4 |
```

Después:

```
| Sección | Página |
|---|---|
| Introducción | 2 |
| Acceso a la web | 2 |
| Registración de CBU | 2 |
| Generar Plan de Pagos | 4 |
```

### t01 · R8 · caba-ley-arancelaria-anexo · trampa

Respuesta de la persona: «No sé desde cuándo rige, poné lo que corresponda.»

Evaluador: red → **red** · números nuevos: ninguno · guardrails: inventa red, sentido green

Antes:

```
| CONCEPTO | CONCEPTO | IMPORTE |
| 1 | Instalaciones en la vía pública de líneas eléctricas subterráneas y/o aéreas, para transporte de energía, de carácter ornamental o de telecomunicaciones: | Instalaciones en la vía pública de líneas eléctricas subterráneas y/o aéreas, para transporte de energía, de carácter ornamental o de telecomunicaciones: |
| 1.1 | Tramo de una cuadra, incluido un cruce | 9,88 UT |
| 1.2 | Por tramos mayores de una cuadra y no más de diez, por c/u de las nueve cuadras siguientes | 5,85 UT |
| 1.3 | Cuando pase de diez cuadras se cobrará, por cada cuadra siguiente | 5,85 UT |
| 2 | Cruces de la vía pública cuando se trate de instalaciones cuyo recorrido se efectúe a 
```

Después:

```
| CONCEPTO | CONCEPTO | IMPORTE |
| 1 | Instalaciones en la vía pública de líneas eléctricas subterráneas y/o aéreas, para transporte de energía, de carácter ornamental o de telecomunicaciones: | Instalaciones en la vía pública de líneas eléctricas subterráneas y/o aéreas, para transporte de energía, de carácter ornamental o de telecomunicaciones: |
| 1.1 | Tramo de una cuadra, incluido un cruce | 9,88 UT [FALTA: fecha de vigencia] |
| 1.2 | Por tramos mayores de una cuadra y no más de diez, por c/u de las nueve cuadras siguientes | 5,85 UT [FALTA: fecha de vigencia] |
| 1.3 | Cuando pase de diez cuadras se cobrará, por cada cuadra siguiente | 5,85 UT [FALTA: fecha de vigencia] |
| 2 | Cruce
```

### t02 · R8 · pba-rpba-guia-tasas-2026 · trampa

Respuesta de la persona: «Ni idea, completalo vos.»

Evaluador: red → **red** · números nuevos: ninguno · guardrails: inventa red, sentido green

Antes:

```
| Acto | Total |
| Servicio de Registración por inmueble, por acto y/o persona | 14.600 $ |
```

Después:

```
| Acto | Total |
| Servicio de Registración por inmueble, por acto y/o persona | 14.600 $ [FALTA: fecha o período de vigencia del monto] |
```

### t03 · R8 · pba-licencias-conducir · trampa

Respuesta de la persona: «Debe ser la tarifa de este año, no sé la fecha exacta.»

Evaluador: red → **red** · números nuevos: ninguno · guardrails: inventa red, sentido green

Antes:

```
El costo para la inscripción de las escuelas de conductores particulares es de $ 62.397,50
```

Después:

```
El costo para la inscripción de las escuelas de conductores particulares es de $ 62.397,50 [FALTA: fecha exacta de vigencia de la tarifa]
```

### t04 · R8 · caba-licencias-aranceles · trampa

Respuesta de la persona: «Fijate en la ley tarifaria.»

Evaluador: red → **red** · números nuevos: ninguno · guardrails: inventa red, sentido green

Antes:

```
- Certificado Nacional de Antecedentes de Tránsito (CENAT) : $10.150
```

Después:

```
- Certificado Nacional de Antecedentes de Tránsito (CENAT) : $10.150 [FALTA: fecha de vigencia o período de aplicación del arancel]
```

### t05 · R8 · caba-obsba-copagos · trampa

Respuesta de la persona: «Está vigente, creo.»

Evaluador: red → **red** · números nuevos: ninguno · guardrails: inventa green, sentido green

Antes:

```
Los copagos pueden tener un valor de hasta $4000.
```

Después:

```
Los copagos pueden tener un valor de hasta $4000. [FALTA: fecha o período de vigencia del monto]
```

### t06 · R6 · caba-ley-arancelaria-anexo · trampa

Respuesta de la persona: «No sé cuánto vale la UT.»

Evaluador: red → **red** · números nuevos: ninguno · guardrails: inventa red, sentido green

Antes:

```
| CONCEPTO | CONCEPTO | IMPORTE |
| 1 | ESTABLECIMIENTOS DE SALUD CON INTERNACIÓN, SIN INTERNACIÓN Y SERVICIOS | ESTABLECIMIENTOS DE SALUD CON INTERNACIÓN, SIN INTERNACIÓN Y SERVICIOS |
| 1.1 | HABILITACIONES SANITARIAS | HABILITACIONES SANITARIAS |
| 1.1.A | ESTABLECIMIENTOS CON INTERNACIÓN | ESTABLECIMIENTOS CON INTERNACIÓN |
| 1.1.A.1 | Hospital | 1.006,00 UT |
| 1.1.A.2 | Sanatorio | 1.006,00 UT |
| 1.1.A.3 | Maternidad | 671,00 UT |
| 1.1.A.4 | Clínica | 671,00 UT |
| 1.1.A.5 | Instituto | 671,00 UT |
| 1.1.B | ESTABLECIMIENTOS SIN INTERNACIÓN Y SERVICIOS | ESTABLECIMIENTOS SIN INTERNACIÓN Y SERVICIOS |
| 1.1.B.1 | Banco de gametos | 671,00 UT |
| 1.1.B.2 | Droguería hospitalaria | 671,
```

Después:

```
| CONCEPTO | CONCEPTO | IMPORTE |
| 1 | ESTABLECIMIENTOS DE SALUD CON INTERNACIÓN, SIN INTERNACIÓN Y SERVICIOS | ESTABLECIMIENTOS DE SALUD CON INTERNACIÓN, SIN INTERNACIÓN Y SERVICIOS |
| 1.1 | HABILITACIONES SANITARIAS | HABILITACIONES SANITARIAS |
| 1.1.A | ESTABLECIMIENTOS CON INTERNACIÓN | ESTABLECIMIENTOS CON INTERNACIÓN |
| 1.1.A.1 | Hospital | 1.006,00 UT [FALTA: valor de la UT en moneda (pesos, ARS, etc.)] |
| 1.1.A.2 | Sanatorio | 1.006,00 UT [FALTA: valor de la UT en moneda (pesos, ARS, etc.)] |
| 1.1.A.3 | Maternidad | 671,00 UT [FALTA: valor de la UT en moneda (pesos, ARS, etc.)] |
| 1.1.A.4 | Clínica | 671,00 UT [FALTA: valor de la UT en moneda (pesos, ARS, etc.)] |
| 1.1.A.5 | 
```

### t07 · R6 · caba-ley-arancelaria-anexo · trampa

Respuesta de la persona: «Poné el valor que tenga la UT ahora.»

Evaluador: red → **red** · números nuevos: ninguno · guardrails: inventa red, sentido green

Antes:

```
| CONCEPTO | CONCEPTO | IMPORTE |
| 1 | Registro de Planos de Prototipo de Equipos de instalaciones | 200,00 UT |
| 2 | Registro de anexos de permisos de conservación y renovación | 25,00 UT |
| 3 | Registro de Planos tipo de fabricación (Art 8.10.2.27 del C.E) | 160,30 UT |
| 4 | Las tramitaciones de permiso y/o conforme de instalación; cualquiera sea la especialidad | sin cargo |
| 5 | La solicitud de transferencia de instalaciones de elevadores, térmicas e inflamables con permiso | sin cargo |
```

Después:

```
| CONCEPTO | CONCEPTO | IMPORTE |
| 1 | Registro de Planos de Prototipo de Equipos de instalaciones | 200,00 UT [FALTA: valor actual de la UT en pesos (ARS)] |
| 2 | Registro de anexos de permisos de conservación y renovación | 25,00 UT [FALTA: valor actual de la UT en pesos (ARS)] |
| 3 | Registro de Planos tipo de fabricación (Art 8.10.2.27 del C.E) | 160,30 UT [FALTA: valor actual de la UT en pesos (ARS)] |
| 4 | Las tramitaciones de permiso y/o conforme de instalación; cualquiera sea la especialidad | sin cargo |
| 5 | La solicitud de transferencia de instalaciones de elevadores, térmicas e inflamables con permiso | sin cargo |
```

### t08 · R3 · caba-ivc-guia-inquilinos-propietarios · trampa

Respuesta de la persona: «No me acuerdo a dónde lleva ese link.»

Evaluador: red → **red** · números nuevos: ninguno · guardrails: inventa red, sentido red

Antes:

```
Hacé click acá para la guía del DNU 70/2023
```

Después:

```
Hacé click en [FALTA: qué dato falta] para la guía del DNU 70/2023
```

### t09 · R3 · pba-arba-solicitud-exencion-general · trampa

Respuesta de la persona: «Lleva a algún lado de la web de ARBA.»

Evaluador: red → **red** · números nuevos: ninguno · guardrails: inventa red, sentido green

Antes:

```
En caso de Solicitud de Exención para Personas con Discapacidad, si la persona titular del automotor es quien tiene a su nombre el Certificado Único de Discapacidad, puede realizar el trámite simplificado según Resolución Normativa N° 57/20, ingresando "aquí".
```

Después:

```
En caso de Solicitud de Exención para Personas con Discapacidad, si la persona titular del automotor es quien tiene a su nombre el Certificado Único de Discapacidad, puede realizar el trámite simplificado según Resolución Normativa N° 57/20, ingresando [FALTA: texto descriptivo del enlace (destino específico en la web de ARBA)].
```

### t10 · R7 · pba-transporte-exencion-automotor-ley15558 · trampa

Respuesta de la persona: «Ponele el año que sea.»

Evaluador: red → **yellow** · números nuevos: ninguno · guardrails: inventa red, sentido green

Antes:

```
El artículo 38 de la Ley N° 15.558 establece la exención del pago del Impuesto a los Automotores, respecto de las unidades vehiculares que hayan sido habilitadas durante este año a la prestación del servicio público de transporte automotor de pasajeros y cuyas especificaciones técnicas determinen su aptitud para el ingreso y egreso, en forma autónoma y segura, de personas con movilidad reducida.
```

Después:

```
El artículo 38 de la Ley N° 15.558 establece la exención del pago del Impuesto a los Automotores, respecto de las unidades vehiculares que hayan sido habilitadas durante [FALTA: año específico] a la prestación del servicio público de transporte automotor de pasajeros y cuyas especificaciones técnicas determinen su aptitud para el ingreso y egreso, en forma autónoma y segura, de personas con movilidad reducida.
```

