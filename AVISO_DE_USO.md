# Aviso de uso

`polface` es una herramienta **para investigación**. Identifica personas en vídeo mediante reconocimiento facial, lo que supone tratar datos biométricos. Antes de usarla, léete esto.

## Uso previsto
- Análisis descriptivo de la visibilidad de **personas públicas** (por ejemplo, políticos) en contenido audiovisual de difusión pública, como los informativos de televisión.
- Investigación académica con las autorizaciones que correspondan a tu institución.

## Usos no previstos y desaconsejados
- Vigilancia, seguimiento o elaboración de perfiles de personas privadas.
- Identificar a personas que no han dado su consentimiento y no son figuras públicas en el contexto analizado.
- Uso comercial (ver licencia de los modelos, más abajo).
- Tomar decisiones sobre personas a partir de los resultados sin verificación humana.

## Responsabilidad de quien la usa
- **Eres responsable del cumplimiento legal** en tu contexto: RGPD (el reconocimiento facial para identificar personas es tratamiento de datos biométricos, art. 9), Reglamento Europeo de IA, y las normas de tu institución. Consulta a tu delegado de protección de datos y, si procede, a tu comité de ética antes de empezar.
- **No subas ni compartas la galería de referencia** (`galeria.npz`): contiene embeddings faciales. El repositorio ya la excluye por defecto con `.gitignore`; no lo cambies.
- **No publiques vídeos ni fotogramas** de terceros sin tener derechos para ello. Las transcripciones completas de emisiones de televisión tampoco deben publicarse sin comprobar los derechos; el repositorio las excluye por defecto.
- Los **resultados** (`detecciones.csv`) contienen el nombre de personas por momento de vídeo. Publica solo agregados (como los de `polface resumen`) salvo que tengas base legal para más.
- Las fotos de referencia deben ser de personas públicas y obtenerse de fuentes cuya licencia permita este uso.

## Limitaciones
- El reconocimiento facial **comete errores**, que no se distribuyen por igual (iluminación, ángulo, edad, calidad de imagen, características de la persona). Las cifras de tiempo en pantalla son **estimaciones** basadas en un fotograma cada N segundos.
- El umbral por defecto (`--umbral 0.5`) es un punto de partida. **Valídalo con una muestra etiquetada a mano** de tus propios vídeos y publica la precisión y la cobertura junto con tus resultados.
- **Las transcripciones no atribuyen el habla a nadie.** El texto unido a cada aparición es el audio que suena alrededor del momento en que se ve a la persona; no se separan hablantes. No cites ese texto como dicho por ella.
- **Sentimiento y toxicidad.** Son clasificadores automáticos entrenados con otros tipos de texto (reseñas, tuits, comentarios en línea). No miden el tono político de una noticia y marcan como tóxico cualquier texto con insultos o palabrotas, incluso citados o denunciados, lo que puede sesgar los resultados. Solo se puntúan los idiomas que cada modelo declara soportar (ver README); valídalos con una muestra codificada a mano en cada idioma.
- Whisper también comete errores (nombres propios, siglas, ruido, música, solapamientos) y puede inventar texto en pasajes sin voz. Revisa una muestra a mano.
- Esta versión no infiere emociones. Si en el futuro se añade, será un módulo opcional con advertencias de validez: que un algoritmo clasifique una expresión no demuestra que la persona sienta esa emoción.

## Licencia de los modelos
El código de este repositorio es MIT. Los modelos preentrenados de **InsightFace** (por ejemplo `buffalo_l`) se descargan aparte y, según la documentación del proyecto, solo pueden usarse para **investigación no comercial**. Comprueba las condiciones vigentes en <https://github.com/deepinsight/insightface> antes de usarlos. Los modelos Whisper (OpenAI) y faster-whisper (SYSTRAN) se distribuyen con licencia MIT.
