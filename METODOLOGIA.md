# Trazabilidad metodológica

Fuente primaria: Rea Sánchez, Víctor (2022), Factores para la adopción de soluciones basadas en software libre, Universidad de Sevilla.
Ficha: https://idus.us.es/items/8087afd1-867c-47fb-b05d-592f69ae49e7
PDF: https://idus.us.es/server/api/core/bitstreams/0e76e5a2-73d2-41ef-9b45-ead884623ce3/content

Se consultaron la Tabla 5.1 (páginas impresas 75–79), los indicadores del capítulo 5 (página 86), la Tabla 5.3 (página 88), la Tabla 5.4 y la ecuación 5.3 (páginas 90–91). La documentación del proyecto suministrada contiene además la matriz de importancia y las reglas RN01–RN10.

## Catálogo

Se sustituyeron los enunciados ilustrativos del HTML por paráfrasis operativas de los criterios de la Tabla 5.1. No se presenta la redacción adaptada como transcripción literal ni como instrumento validado empíricamente. Se conservan las tres dimensiones, los 18 factores y el total de 61 subfactores.

La Tabla 5.1 ubica dos enunciados bajo apoyo de la alta dirección y uno bajo actitud hacia el cambio. La Tabla 5.3 y el documento del proyecto distribuyen esos conteos como uno y dos. Esta versión sigue los enunciados de la Tabla 5.1: incluye respaldo directivo y respaldo del personal de TI bajo apoyo, y resistencia al cambio bajo actitud. El administrador puede ajustar la clasificación; toda evaluación conserva una copia de su catálogo.

IL e IE se cargan por separado: IE inicial es 3; IL usa los valores de la Tabla 5.3. Se calcula IS combinando ambos mediante la matriz. El prototipo anterior igualaba IL, IE e IS, lo que se corrigió.

## Reglas implementadas

IR combina ID e IS con la matriz 4 × 4. Solo IR > 1 entra en el cuestionario. Las respuestas admiten 1, 2, 3 y 4; la opción 2 significa desconocimiento, no un valor faltante.

PM es la media aritmética. Se conserva la precisión para clasificar; el redondeo a dos decimales es de presentación. PM >= 3 produce fortaleza si el impacto es interno u oportunidad si es externo. PM < 3 produce debilidad o amenaza. Soporte exige elegir impacto.

Para cargas de expertos, se promedia por subfactor y luego entre subfactores activos, con igual peso por subfactor y redondeo de mitades hacia arriba al obtener IE. Se exige cobertura completa de los subfactores activos de cada factor afectado. Se conservan las valoraciones originales; una importación inválida se revierte entera. Este orden de agregación hace explícita la interpretación operativa del texto de la tesis, incluso cuando hay distinto número de expertos por subfactor.

## Decisión propia de SEAS

RN09 proviene del proyecto, no de una regla de decisión automática validada en la tesis. Entre los factores con IR >= 3: cero desfavorables sugiere adoptar; hasta la mitad, adoptar con condiciones; más de la mitad, no adoptar por ahora. Si no hay factores críticos, la aplicación muestra ese hecho y aplica literalmente la primera condición. La organización conserva la decisión final.

RN10 bloquea edición y recálculo al finalizar. Duplicar genera un nuevo registro con el catálogo actual y respuestas vacías, para evitar que un cambio de enunciado herede una respuesta antigua.

## Alcance de la adaptación

GUIOS se centra en FLOSS. Los criterios de acceso al código, licencia y comparación con una alternativa propietaria conservan ese contexto. Antes de evaluar otro tipo de software, administración debe configurar un catálogo aplicable y definir cuál es la alternativa de referencia. No se interpreta una condición que no aplica como incumplimiento automático.

La revisión documental y las pruebas técnicas no sustituyen una validación de contenido por expertos ni la aceptación del docente.
