# Podcast: un semáforo para los documentos

Guion para dos voces, escrito para escuchar. Lo convierte en audio `podcast/render.py`.
Cada línea que empieza con `ANA:` o `TOMÁS:` es una intervención; las líneas `[pausa]` agregan
un silencio largo entre bloques.

ANA: Hola, bienvenidos. Hoy vamos a contar una investigación de punta a punta: un laboratorio que se armó para entender cómo funcionan los buscadores con inteligencia artificial, y para probar una idea concreta.

TOMÁS: Y la idea es bastante simple de decir. Cuando una organización arma un buscador con inteligencia artificial sobre sus documentos, normalmente mete todo adentro, tal cual está. Lo que se quiso probar acá es qué pasa si, antes de meter un documento, alguien revisa que esté bien escrito.

ANA: Un control de calidad en la puerta.

TOMÁS: Exacto. Le pusieron de nombre el semáforo. Cada pedazo del documento queda en verde, en amarillo o en rojo según unas reglas. Y si hay rojos importantes, el documento no entra hasta que se corrija.

ANA: Antes de seguir, aclaremos qué es un buscador con inteligencia artificial, porque vamos a hablar mucho de eso.

TOMÁS: Se lo conoce como RAG, por sus siglas en inglés: generación aumentada por recuperación. Funciona en dos pasos. Primero, cuando alguien hace una pregunta, el sistema busca en los documentos los pedazos que parecen tener la respuesta. Y después, un modelo de lenguaje lee esos pedazos y escribe una respuesta, citando de dónde sacó cada dato.

ANA: O sea que el modelo no responde de memoria: responde leyendo.

TOMÁS: Esa es la gracia. Y por eso la hipótesis tiene sentido: si los documentos dicen cosas ambiguas, el modelo va a leer cosas ambiguas.

ANA: ¿Con qué documentos se trabajó?

TOMÁS: Con cuarenta y nueve guías de trámites públicas, de la Provincia y de la Ciudad de Buenos Aires. Licencias de conducir, partidas de nacimiento, exenciones de impuestos, la obra social, el registro de la propiedad. Hay PDF, páginas web y documentos de Word. Y todo se hizo a costo cero: con modelos gratuitos por internet y con modelos que corren en una computadora común.

[pausa]

ANA: Arranquemos por el principio. Lo primero que se hizo fue algo muy básico: aprender a hablarle a un modelo.

TOMÁS: Y ahí apareció el primer hallazgo curioso. Hay modelos que piensan antes de contestar. Escriben un razonamiento interno que el usuario no ve, y después responden. Ese razonamiento gasta palabras. Entonces, si le ponés un límite chico de largo a la respuesta, el modelo se queda sin espacio mientras piensa… y devuelve una respuesta vacía. Sin ningún error. Simplemente nada.

ANA: Eso es peligroso, porque parece que funcionó.

TOMÁS: Exacto. Fue la primera lección: una respuesta vacía tiene que tratarse como una falla.

ANA: El segundo paso fue pedirle al modelo respuestas con formato. Por ejemplo, que de un párrafo saque cada monto de dinero, con su moneda y la fecha desde la que rige.

TOMÁS: Y acá la sorpresa fue que el formato ya no es un problema. Los modelos buenos devolvieron el formato correcto el cien por ciento de las veces. Los problemas estaban en los datos. Por ejemplo, muchos documentos dicen "a partir de abril de dos mil veintiséis", sin día. Y un campo de fecha te obliga a inventar el día.

ANA: Y había uno muy argentino.

TOMÁS: Sí. En la Argentina el punto separa los miles. Un modelo leyó "ciento ocho mil quinientos cuatro pesos" como ciento ocho coma cinco. Mil veces menos. Y el resultado tenía un formato perfecto. Ningún control de formato detecta eso.

[pausa]

ANA: Después vino una parte que parece aburrida y resultó fundamental: leer los documentos.

TOMÁS: Un PDF, por dentro, no tiene párrafos ni títulos. Tiene letras dibujadas en posiciones de una página. Reconstruir qué es un título, qué es una lista y qué es una tabla es un problema en sí mismo.

ANA: Y se compararon dos formas de hacerlo.

TOMÁS: Una escrita a mano, con reglas: si la letra es más grande es un título, si empieza con un punto es un ítem de lista. Y otra con una herramienta llamada Docling, que usa un modelo entrenado para reconocer la estructura de una página. En los PDF con diseño ganó Docling: reconoció los diecisiete ítems de lista de un instructivo, contra doce de las reglas a mano. Pero en las páginas web empataron, y en los documentos de Word ganaron las reglas a mano.

ANA: ¿Y qué problemas aparecieron?

TOMÁS: Varios, y todos vuelven más adelante. El más importante: algunos PDF se cortaban renglón por renglón. Un monto quedaba en un pedazo, y la fecha desde la que rige, en el pedazo siguiente. Eso parece un detalle técnico, pero después le complica la vida a todo el sistema.

[pausa]

ANA: Pasemos a la búsqueda. ¿Cómo encuentra el sistema el pedazo correcto?

TOMÁS: Primero hay que decidir cómo cortar los documentos. Esos pedazos se llaman chunks. Si son muy chicos, el dato queda partido. Si son muy grandes, mezclan muchos temas y no se parecen a ninguna pregunta.

ANA: ¿Y qué funcionó mejor?

TOMÁS: Lo que más rindió fue algo simple: a cada pedazo se le agrega adelante el título del documento y la ruta de títulos donde está. Por ejemplo: "Solicitud de partidas urgentes, sección Costos del trámite". Con eso, la probabilidad de encontrar el pedazo correcto en el primer lugar subió once puntos.

ANA: Más que cambiar de modelo.

TOMÁS: Más que pasar de uno de los buenos modelos al mejor, sí. La estructura le ganó a la tecnología.

ANA: Y ahí hubo una sorpresa con la búsqueda híbrida, que era una de las decisiones del diseño.

TOMÁS: Sí. Hay dos formas de buscar. Una por significado, que entiende que "sacar el registro" y "obtener la licencia de conducir" son lo mismo. Y otra por palabras exactas, que es la búsqueda clásica. La recomendación habitual es combinarlas. Acá, combinarlas empeoró los resultados: el acierto en primer lugar bajó de sesenta y seis a cincuenta y cinco por ciento. La búsqueda por palabras era mucho más débil y arrastraba a la otra.

ANA: Así que la sacaron.

TOMÁS: La sacaron. Y eso pasó varias veces: medir dio vuelta decisiones que parecían obvias.

ANA: También se armó a mano un índice para buscar rápido.

TOMÁS: Sí, un índice llamado HNSW, que es el que usan casi todas las bases de datos de este tipo. Es un grafo: cada pedazo está conectado con sus vecinos parecidos, y buscar es caminar de vecino en vecino. La primera versión encontraba los resultados correctos el setenta y siete por ciento de las veces. Cambiando una sola cosa, cómo se eligen los vecinos, pasó al noventa y siete.

ANA: ¿Qué cambio?

TOMÁS: Elegir vecinos que apunten en direcciones distintas, y no todos al mismo grupito de pedazos casi iguales. Y de paso se descubrió que la versión local de la base de datos que se había elegido, Qdrant, no usa ese índice: compara contra todo. Y que si filtrás los resultados después de buscar, por ejemplo por permisos de usuario, perdés un cuarto de las respuestas correctas. Los filtros tienen que estar en la base de datos.

ANA: Y el último paso de la búsqueda fue el reordenamiento.

TOMÁS: Fue la mejora más grande de todas. Se traen los diez mejores candidatos y un segundo modelo los lee junto con la pregunta, uno por uno, y los reordena. Con eso, el pedazo correcto queda entre los tres primeros el noventa y cinco por ciento de las veces.

[pausa]

ANA: Ahora sí, el corazón del proyecto: el semáforo.

TOMÁS: Para cada pedazo y cada regla, hay que decidir verde, amarillo o rojo. Las reglas no son opiniones: salen de normas. Por ejemplo, que un enlace diga a dónde lleva, de las normas de accesibilidad web. O que todo monto diga en qué moneda está, de la norma internacional de monedas.

ANA: ¿Y cómo decide el modelo?

TOMÁS: Acá está una de las ideas más lindas del proyecto. En vez de pedirle al modelo que escriba una respuesta, se le hace una pregunta con tres opciones, A, B y C, y se mira directamente qué probabilidad le asigna a cada letra. No escribe nada. Y eso da algo muy valioso: una confianza.

ANA: ¿Y por qué importa la confianza?

TOMÁS: Porque si el modelo duda, el pedazo no debería quedar en verde: tiene que quedar en amarillo, "a revisar". Y la comparación fue clara. Leyendo las probabilidades, la confianza es honesta: cuando dice setenta, acierta más o menos setenta. Pidiéndole que conteste en texto, acierta parecido, pero dice "estoy noventa y ocho por ciento seguro" siempre. Esa confianza no sirve para nada.

ANA: ¿Y qué tan bien acierta?

TOMÁS: Alrededor de setenta por ciento. Y ese es uno de los límites honestos de la investigación: deja pasar casi un tercio de los rojos. Para bloquear documentos, es poco.

ANA: Las reglas, además, se pueden escribir en lenguaje natural.

TOMÁS: Sí. Alguien escribe "los links tienen que decir a dónde llevan", y un modelo lo convierte en una regla con todos sus campos. Compiló bien catorce de veinticuatro reglas sin tocar nada. Y algo importante: cuando le dieron reglas vagas, como "que el documento sea claro", en vez de inventar un criterio, pidió uno concreto. Las seis veces.

ANA: Y cuando un pedazo queda en rojo, viene la corrección.

TOMÁS: La revisión guiada. El sistema le muestra a la persona qué está mal y le pregunta qué falta. La persona contesta con sus palabras, y un modelo reescribe solo ese pedazo. Se probó con trampas: respuestas que no traían el dato, como "no sé, poné lo que corresponda".

ANA: ¿Y el modelo inventó?

TOMÁS: Ni una vez en diez. Dejó una marca visible que dice "falta tal dato". Pero apareció un problema más sutil. Una regla pide que los textos le hablen al lector en voz activa. Y en un texto que decía que la autoridad tiene que retener la licencia del infractor, el modelo lo reescribió como "si tenés licencia, debés retenerla". Cambió quién tiene que hacer qué. Y ningún control automático lo detectó.

ANA: Por eso el diseño insiste en que una persona acepte cada cambio.

TOMÁS: Exacto. Con el antes y el después a la vista.

[pausa]

ANA: Vamos a las respuestas finales.

TOMÁS: Con todo junto, el sistema respondió bien la gran mayoría de las preguntas, y lo más importante: ninguna respuesta afirmaba algo que no estuviera en lo que citaba. Cuando se equivocó, fue por prudencia: dijo "no tengo esa información" teniéndola.

ANA: ¿Y con preguntas que no tienen respuesta?

TOMÁS: Se armaron diez preguntas cuya respuesta no estaba en los documentos, como cuánto cuesta el pasaporte. El modelo se abstuvo en las diez. Y acá hubo otra decisión del diseño que se cayó. Se pensaba usar el puntaje del reordenamiento como alarma: si es bajo, no responder. Pero a la pregunta "cuánto cuesta la verificación técnica en la Ciudad" le dio un puntaje altísimo, porque había un documento sobre la verificación en la Provincia. El puntaje mide si el tema se parece, no si responde la pregunta.

ANA: Y hubo un experimento sobre los propios jueces.

TOMÁS: Sí, porque para saber si una respuesta es correcta también se usa un modelo como juez. Y había que saber si ese juez es confiable. Resultó que un modelo chico, corriendo en la computadora, coincidía más con las etiquetas que uno enorme por internet. El grande no se equivocaba al azar: era más exigente.

[pausa]

ANA: Y llegamos al final. Se armó una aplicación con todo, y se hizo el experimento que respondía la pregunta del principio.

TOMÁS: Se tomaron los documentos tal cual, y los mismos documentos después de pasar por el semáforo y las correcciones. Mismas preguntas, mismo sistema, mismo juez.

ANA: ¿Y?

TOMÁS: Empate. Trece respuestas correctas en los dos casos.

ANA: O sea, la hipótesis no se confirmó.

TOMÁS: No se confirmó. Y la explicación es lo más interesante de toda la investigación. El semáforo mira cada pedazo por separado. Pero el buscador lee varios pedazos a la vez. Si a un monto le falta la fecha de vigencia, pero el documento la dice en otra sección, el buscador trae los dos pedazos y el modelo los conecta solo. Lo que es rojo para una persona que lee un párrafo suelto, no es necesariamente rojo para el buscador.

ANA: ¿Entonces el semáforo no sirve?

TOMÁS: Sirve en otros casos, y eso también se vio. Cuando la corrección agrega un dato que el documento directamente no tenía. Por ejemplo, una página que no decía quién la publicaba. Después de corregirla, la pregunta "¿quién publica esta información?" pasó a tener respuesta. Antes era imposible. Y cuando la corrección vuelve a juntar datos que la lectura del PDF había separado, como un monto y su fecha.

ANA: Así que el valor está en otro lado del que se pensaba.

TOMÁS: Exacto. Y eso abre la próxima pregunta: medir el semáforo pensando en una persona que lee, y no solo en las respuestas del chat.

[pausa]

ANA: Para cerrar, ¿qué te llevás de todo esto?

TOMÁS: Tres cosas. La primera: medir antes de decidir. Tres decisiones que parecían obvias, la búsqueda combinada, la alarma por puntaje y la base de datos local, se cayeron al medirlas. La segunda: los problemas más difíciles estuvieron en los datos, no en los modelos. Cómo se lee un PDF, cómo se escribe una fecha, qué significa un punto en un número. Y la tercera: que una buena investigación también es la que se anima a decir "esto no funcionó como esperábamos, y esta es la razón".

ANA: Y todo está documentado, con los números de cada prueba, en el repositorio del laboratorio.

TOMÁS: Con cada paso explicado, en español y en inglés.

ANA: Gracias por escuchar.
