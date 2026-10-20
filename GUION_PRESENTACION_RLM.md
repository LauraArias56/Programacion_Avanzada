# Guion completo — Presentación de Regresión Lineal Múltiple

**Proyecto:** Predicción del promedio mensual de generación eléctrica en Colombia (datos.gov.co)  
**Evento:** Evaluativo 18 de octubre · Valor 15%  
**Duración objetivo:** 17 minutos (presentación + preguntas)  
**Archivo de diapositivas:** `Presentacion_Regresion_Lineal_Multiple.pptx`

---

## Índice

1. [Distribución del tiempo](#distribucion-del-tiempo)
2. [Guion diapositiva por diapositiva](#guion-diapositiva-por-diapositiva)
3. [Las 10 preguntas más probables del jurado](#10-preguntas-del-jurado)
4. [Consejos prácticos para la exposición](#consejos-practicos)

---

## Distribución del tiempo

| Bloque | Diapositivas | Tiempo estimado |
|--------|--------------|-----------------|
| Introducción y datos | 1, 2, 3 | 4 min |
| Modelo y cálculo paso a paso | 4, 5, 6, 7 | 6 min |
| Validación, métricas y predicción | 8, 9, 10 | 4 min |
| Crítica y cierre | 11, 12 | 2 min |
| Preguntas del jurado | — | 4–5 min |
| **Total** | | **~20–21 min** *(márgen cómodo para 17 min)* |

> **Nota:** Si el estricto límite es 17 minutos, reduzca ligeramente los bloques de introducción y cierre, y deje 3 minutos para preguntas. El guion está escrito con suficiente detalle para que pueda expandirse o comprimirse según necesite.

---

## Guion diapositiva por diapositiva

### Diapositiva 1 — Portada

**Tiempo sugerido:** 1 minuto

**Qué mostrar en pantalla:** La portada del PowerPoint (título, fuente datos.gov.co, evento 18 de octubre, valor 15%, pipeline 01→02→03).

**Qué decir:**

> Buenas tardes. Mi nombre es [su nombre] y voy a presentar el trabajo de Regresión Lineal Múltiple aplicado a la generación eléctrica en Colombia. El objetivo de este análisis es predecir el promedio mensual de generación, expresado en GWh, a partir del máximo y del mínimo registrados en un mes por fuente energética. Los datos provienen de la API oficial de datos.gov.co, vista tq63-itzr, con 2.786 registros entre los años 2000 y 2026. Todo el desarrollo se hizo con Python y NumPy puro, sin utilizar librerías de machine learning tipo sklearn, para poder mostrar el cálculo matemático paso a paso. El entregable formal es un informe en Word
**Puntos clave que debe mencionar:**
- Nombre del proyecto y objetivo general.
- Fuente de datos (datos.gov.co).
- Enfoque pedagógico: NumPy puro, sin sklearn.
- Entregable: informe DOCX automático.

**Pregunta probable del jurado:** *¿Por qué datos.gov.co?*  
**Respuesta:** Es una fuente pública oficial de Colombia, los datos son descentralizados y verificables, y la vista tq63-itzr contiene exactamente las variables que necesitamos: promedio mensual, máximo y mínimo por fuente energética.

---

### Diapositiva 2 — Objetivo del problema

**Tiempo sugerido:** 1 minuto 30 segundos

**Qué mostrar en pantalla:** Señale la fórmula grande ŷ = b₀ + b₁·X₁ + b₂·X₂ y explique brevemente cada término. Señale también el panel derecho con las tres fórmulas (ecuación de regresión, ecuación normal, función de costo).

**Qué decir:**

> El problema es de regresión supervisada con una variable objetivo continua: el promedio mensual de generación en GWh. Como predictores usamos dos variables continuas: el máximo mensual (X₁) y el mínimo mensual (X₂) observados en ese mes y para esa fuente energética. ¿Por qué tiene sentido físico modelarlo así? Porque el promedio de un mes debe estar, lógicamente, entre el mínimo y el máximo registrados. Por lo tanto, modelar el promedio como una combinación lineal de ambos es coherente con la realidad del sistema eléctrico. No usamos año, mes ni fuente como predictores numéricos; esas variables sirven solo para trazabilidad y para estratificar la muestra. Además, descartamos la generación total como predictor, porque el análisis exploratorio mostró que el cociente entre generación total y promedio mensual da aproximadamente los días del mes; predecir el total sería trivial y estaría contaminado por la duración de cada mes.

**Puntos clave:**
- Regresión supervisada, objetivo continuo.
- Dos predictores: máximo (X₁) y mínimo (X₂).
- Razonamiento físico: promedio entre mínimo y máximo.
- Año, mes y fuente solo como trazabilidad.
- Generación total descartada por fugas de información (días del mes).

**Pregunta probable del jurado:** *¿Y por qué no usar más variables predictoras?*  
**Respuesta:** Con solo dos predictores el modelo sigue siendo interpretable: cada coeficiente se lee directamente en GWh. Además, el objetivo pedagógico es desarrollar el cálculo a mano con matrices 3×3, algo inviable si tuviéramos muchas variables.

---

### Diapositiva 3 — Origen de los datos

**Tiempo sugerido:** 1 minuto 30 segundos

**Qué mostrar en pantalla:** Señale los cuadros del panel derecho (2.786 filas, periodo 2000–2026, 13 fuentes, 0 nulos) y mencione el script 01_descargar.py.

**Qué decir:**

> Los datos se descargan automáticamente de la API de datos.gov.co mediante el script 01_descargar.py. Se trata de 2.786 filas que cubren el periodo de 2000 a 2026, con 13 fuentes energéticas diferentes —agua, gas, carbón, ACPM, bagazo, combustóleo, entre otras—. El dataset no tiene valores nulos, lo que simplifica la limpieza. Tomamos dos decisiones importantes al preparar la información: primero, no usar la generación total como predictor, porque está fuertemente ligada a los días del mes y introduciría una fuga de información. Segundo, trabajamos con una muestra intencional estratificada de solo 10 registros para que todo el cálculo de la ecuación normal sea verificable a mano, sin depender de una caja negra.

**Puntos clave:**
- API pública de datos.gov.co, vista tq63-itzr.
- 2.786 registros, 2000–2026, 13 fuentes.
- Sin valores nulos.
- Decisión 1: no usar generación total (ratio ≈ días del mes).
- Decisión 2: muestra intencional n = 10 para cálculo manual verificable.

**Pregunta probable del jurado:** *¿Por qué solo 10 registros si hay 2.786?*  
**Respuesta:** Es intencionalmente pequeña con fines didácticos. Queremos mostrar el cálculo exacto paso a paso de la ecuación normal con matrices pequeñas que se puedan revisar manualmente. Las 2.786 filas están disponibles para una versión productiva o de operación real.

---

### Diapositiva 4 — Muestra de trabajo (n = 10)

**Tiempo sugerido:** 2 minutos

**Qué mostrar en pantalla:** Recorra la tabla fila por fila. Señale que hay fuentes repetidas (AGUA dos veces, GAS dos veces) y el resto una cada una. Señale el rango bajo (Bagazo, Jet-A1), rango medio (Gas, ACPM) y rango alto (Agua). Señale las medias al pie de la tabla.

**Qué decir:**

> Esta es la muestra de trabajo: 10 registros elegidos intencionalmente para cubrir 8 fuentes distintas y todo el rango de valores observados. Tenemos desde 0,29 GWh en Bagazo hasta 90,37 GWh en Agua, pasando por valores intermedios en Gas, Carbón, ACPM y otras fuentes. Las medias de la muestra son: promedio de Y igual a 23,5006 GWh, promedio de X₁ igual a 28,0531 GWh y promedio de X₂ igual a 17,3434 GWh. No hay valores nulos en esta muestra y no eliminamos los valores extremos —como los de Agua, que superan los 70 GWh— porque son informativos, no errores de medición.

**Puntos clave:**
- Muestra intencional estratificada (8 fuentes, rango bajo/medio/alto).
- Rango de Y: 0,29 a 90,37 GWh.
- Medias: Ȳ = 23,5006, media X₁ = 28,0531, media X₂ = 17,3434.
- Sin nulos, sin eliminar atípicos.

**Pregunta probable del jurado:** *¿No es muy pequeña la muestra para generalizar?*  
**Respuesta:** Sí, es muy pequeña, y eso es precisamente una limitación que discutiremos más adelante. Aquí se usa con fines pedagógicos para hacer el cálculo manual verificable. En operación real se requeriría la base completa o al menos una muestra mucho mayor.

---

### Diapositiva 5 — Modelo matemático (OLS)

**Tiempo sugerido:** 2 minutos

**Qué mostrar en pantalla:** Señale la ecuación grande en el centro, las tres viñetas de "¿Por qué este algoritmo?" y las hipótesis del modelo a la derecha.

**Qué decir:**

> El modelo que utilizamos es regresión lineal múltiple por mínimos cuadrados ordinarios (OLS). La ecuación es ŷ = b₀ + b₁·X₁ + b₂·X₂, donde b₀ es el intercepto, b₁ mide el efecto del máximo mensual y b₂ mide el efecto del mínimo mensual. ¿Por qué elegimos este algoritmo? Primero, porque da una ecuación explícita e interpretable: cada coeficiente tiene una lectura operativa directa en GWh. Segundo, porque con solo dos predictores podemos resolverlo con una matriz 3×3 y desarrollar el cálculo a mano, lo cual cumple el objetivo pedagógico de este trabajo. Tercero, porque descartamos alternativas como KNN o árboles de decisión, que no entregan una ecuación cerrada que podamos auditar, y una regresión simple desperdiciaría uno de los dos predictores disponibles. Las suposiciones del modelo son linealidad, errores de media cero, independencia y homocedasticidad. Como advertencia honesta, les anticipo que X₁ y X₂ están muy correlacionados (r = 0,986), lo cual trataremos como una limitación más adelante.

**Puntos clave:**
- Ecuación OLS: ŷ = b₀ + b₁·X₁ + b₂·X₂.
- Interpretabilidad: cada coeficiente en GWh.
- Solución cerrada con matrices 3×3 (objetivo pedagógico).
- Descartados: KNN/árboles (sin ecuación explícita), regresión simple (pierde predictor).
- Hipótesis: linealidad, errores media cero, independencia, homocedasticidad.
- Advertencia: colinealidad X₁–X₂ con r = 0,986.

**Pregunta probable del jurado:** *¿Qué significa homocedasticidad?*  
**Respuesta:** Significa que la varianza de los errores es aproximadamente constante a lo largo de todo el rango de los predictores; no se "abanica" ni se vuelve más grande en ciertos valores de X.

---

### Diapositiva 6 — Ecuación normal paso a paso (1/2)

**Tiempo sugerido:** 2 minutos 30 segundos

**Qué mostrar en pantalla:** Señale la matriz XᵀX (3×3) con los valores reales de XtX.csv, el vector Xᵀy, y el valor del determinante resaltado en verde.

**Qué decir:**

> Vamos ahora al núcleo del cálculo. Primero construimos la matriz de diseño X, que tiene 10 filas y 3 columnas: una columna de unos para el intercepto, la columna X₁ correspondiente al máximo mensual, y la columna X₂ correspondiente al mínimo mensual. Luego calculamos XᵀX, que es una matriz 3×3, y el vector Xᵀy, que tiene 3 componentes. Los valores que ven en pantalla son los reales extraídos del archivo XtX.csv y del script 02_modelo.py. Por ejemplo, la suma de Y es 235,0061; la suma de X₁ por Y es 16.150,53; y la suma de X₂ por Y es 11.232,44. El paso crucial es verificar el determinante de XᵀX, que es 17 millones 73 mil 437, aproximadamente. Como este valor es distinto de cero, la matriz es invertible y por lo tanto existe una solución única para los coeficientes.

**Puntos clave:**
- Matriz de diseño X (10×3): columna de unos + X₁ + X₂.
- Operaciones: calcular XᵀX (3×3) y Xᵀy (3×1).
- Valores reales de XtX.csv.
- det(XᵀX) = 17.073.437,13 ≠ 0 → matriz invertible, solución única.

**Pregunta probable del jurado:** *¿Qué es XᵀX y por qué es importante?*  
**Respuesta:** XᵀX es la matriz transpuesta de X multiplicada por X. Resume las sumas de productos cruzados entre las columnas de X y es el corazón de la ecuación normal de mínimos cuadrados. Si su determinante es cero, no hay solución única.

---

### Diapositiva 7 — Resultado: coeficientes theta

**Tiempo sugerido:** 2 minutos

**Qué mostrar en pantalla:** Señale la ecuación grande ŷ = 0,3387 + 0,3988·X₁ + 0,6904·X₂ y las cuatro viñetas de interpretación operativa. Señale también la matriz inversa (XtX_inv.csv) como evidencia del cálculo matricial.

**Qué decir:**

> Después de calcular la inversa de XᵀX y multiplicarla por el vector Xᵀy, obtenemos los coeficientes finales theta: b₀ = 0,3387, b₁ = 0,3988 y b₂ = 0,6904. La ecuación aprendida es: ŷ = 0,3387 + 0,3988·X₁ + 0,6904·X₂. ¿Cómo se interpreta esto operativamente? El intercepto de 0,34 GWh es un ajuste de base cuando ambos predictores son cero. Cada GWh adicional en el máximo mensual eleva el promedio en aproximadamente 0,40 GWh. Y cada GWh adicional en el mínimo mensual eleva el promedio en aproximadamente 0,69 GWh. Observen que b₂ es mayor que b₁; esto tiene sentido físico porque el mínimo —el "piso" de generación del mes— sostiene el promedio más que un pico aislado. La matriz inversa que ven a la derecha es la prueba numérica de que cada paso del cálculo matricial se ejecutó correctamente.

**Puntos clave:**
- b₀ = 0,3387 (intercepto de ajuste).
- b₁ = 0,3988 (efecto del máximo: +0,40 GWh por cada GWh de máx).
- b₂ = 0,6904 (efecto del mínimo: +0,69 GWh por cada GWh de mín).
- b₂ > b₁: el piso sostiene el promedio más que el pico.
- Evidencia: XtX_inv.csv.

**Pregunta probable del jurado:** *¿Por qué b₂ es mayor que b₁?*  
**Respuesta:** Porque el mínimo mensual es un mejor indicador del nivel base sostenido de generación, mientras que el máximo puede ser un pico puntual que no representa tanto el promedio del mes.

---

### Diapositiva 8 — Gradiente descendente (validación)

**Tiempo sugerido:** 2 minutos

**Qué mostrar en pantalla:** Señale la figura de convergencia (costo J vs. iteración) embebida y las viñetas del lado izquierdo con los valores del gradiente.

**Qué decir:**

> Para verificar que el cálculo manual de la ecuación normal es correcto, usamos un segundo método completamente independiente: el gradiente descendente. Estandarizamos las variables X₁ y X₂ para que tengan media 0 y desviación estándar 1, inicializamos los coeficientes en cero, usamos una tasa de aprendizaje de 0,1 y ejecutamos 2.000 iteraciones. La función de costo J inicia en 713,88 y desciende progresivamente hasta 0,1038, estabilizándose a partir de la iteración 500 aproximadamente. Al volver los coeficientes a la escala original, obtenemos b₀ = 0,3210, b₁ = 0,4025 y b₂ = 0,6855, los cuales coinciden con la ecuación normal con una diferencia menor a 0,018. Esta pequeña diferencia se debe simplemente a que el gradiente se detuvo en 2.000 iteraciones y no alcanzó la convergencia exacta. En resumen, el método iterativo valida el cálculo analítico exacto.

**Puntos clave:**
- Método iterativo independiente para validar la ecuación normal.
- Estandarización de X₁ y X₂.
- α = 0,1, 2.000 iteraciones.
- Costo: 713,88 → 0,1038.
- Coeficientes en escala original coinciden (diferencia < 0,018).
- Convergencia lenta por alta correlación entre predictores.

**Pregunta probable del jurado:** *¿Por qué el gradiente descendente converge lento?*  
**Respuesta:** Por la alta correlación entre X₁ y X₂ (r = 0,986): el valle del costo es alargado y el gradiente avanza con pasos cortos, necesitando más iteraciones para estabilizarse.

---

### Diapositiva 9 — Métricas de error y ajuste

**Tiempo sugerido:** 2 minutos

**Qué mostrar en pantalla:** Señale la tabla de métricas, especialmente la fila de R² resaltada, y el panel derecho con la lectura rápida.

**Qué decir:**

> Evaluemos qué tan bien ajusta el modelo sobre la misma muestra de entrenamiento. El error cuadrado medio (MSE) es 0,2072, el error cuadrado medio raíz (RMSE) es 0,4552 GWh, y el error absoluto medio (MAE) es 0,3833 GWh. Para poner esto en perspectiva, el RMSE representa solo el 1,9 % de la media de Y, que es 23,5 GWh. El coeficiente de determinación R² es 0,999763, es decir, el 99,98 % de la varianza del promedio mensual es explicada por el máximo y el mínimo en esta muestra. El error más grande ocurre en Combustóleo con 0,97 GWh, y el más pequeño en Jet-A1 con apenas 0,0064 GWh. Sin embargo, les pido que seamos honestos: con solo 10 registros, este R² de entrenamiento está inflado y no garantiza que el modelo se comporte igual con datos nuevos que no haya visto antes.

**Puntos clave:**
- SSE = 2,0719; MSE = 0,2072; RMSE = 0,4552 GWh (1,9 % de la media).
- MAE = 0,3833 GWh.
- R² = 0,999763 (99,98 % de varianza explicada).
- R² ajustado = 0,999696.
- Advertencia: R² inflado por muestra pequeña (n = 10).

**Pregunta probable del jurado:** *¿Si R² es tan alto, por qué no confiar plenamente en el modelo?*  
**Respuesta:** Porque con n = 10 es fácil sobreajustar (memorizar la muestra). El R² mide qué tan bien recuerda los datos de entrenamiento, no qué tan bien predice datos nuevos. Por eso recomendamos más datos y validación cruzada antes de usar el modelo en operación.

---

### Diapositiva 10 — Predicción para un dato nuevo

**Tiempo sugerido:** 1 minuto 30 segundos

**Qué mostrar en pantalla:** Haga la sustitución en voz alta mientras señala la fórmula en pantalla. Señale la figura de real vs. predicho (puntos alineados en la diagonal).

**Qué decir:**

> Probemos el modelo con un dato que no estuvo en el entrenamiento: supongamos un máximo mensual de 20 GWh y un mínimo de 10 GWh. Sustituyendo directamente en la ecuación final: ŷ = 0,3387 + 0,3988 × 20 + 0,6904 × 10, lo que nos da una predicción de 15,2191 GWh. Si usamos un intervalo orientativo de ± RMSE, el valor real probablemente cae entre 14,76 y 15,67 GWh. El resultado es plausible: queda entre el mínimo (10) y el máximo (20), como debería ser físicamente, y se ubica cerca del centro ponderado que el modelo aprendió de la muestra.

**Puntos clave:**
- Dato de prueba no visto: X₁ = 20, X₂ = 10.
- Sustitución: ŷ = 0,3387 + 0,3988×20 + 0,6904×10 = 15,2191 GWh.
- Intervalo ±RMSE: [14,7639 ; 15,6743] GWh.
- Plausibilidad: está entre 10 y 20.

**Pregunta probable del jurado:** *¿Qué tan confiable es esta predicción?*  
**Respuesta:** Es una interpolación dentro del rango de la muestra (0–103 GWh), por lo que es razonable. Pero no es una garantía absoluta; el intervalo ±RMSE da una idea de la incertidumbre asociada.

---

### Diapositiva 11 — Limitaciones y advertencias

**Tiempo sugerido:** 2 minutos

**Qué mostrar en pantalla:** Señale las tres viñetas principales y el cuadro "¿Qué pasaría si…?" con los escenarios alternativos.

**Qué decir:**

> Ahora les presento las limitaciones del modelo, porque un buen análisis debe ser honesto sobre sus debilidades. Primero, el tamaño de la muestra es muy pequeño: n = 10 significa que el modelo esencialmente memoriza los datos de entrenamiento, por lo que no se puede generalizar directamente a las 2.786 filas originales. Segundo, existe multicolinealidad alta entre el máximo y el mínimo (r = 0,986); esto hace que los coeficientes b₁ y b₂ sean sensibles a pequeños cambios en los datos, aunque el pronóstico global siga siendo bueno. Tercero, no debemos extrapolar fuera del rango de 0 a 103 GWh ni a fuentes energéticas no representadas en la muestra. Para ilustrar la sensibilidad: si forzáramos el intercepto b₀ a ser cero, el error al cuadrado se triplicaría, perdiendo el ajuste fino en valores bajos como Bagazo o Jet-A1. Si elimináramos la variable X₂ (el mínimo), el R² caería porque el mínimo aporta información independiente del pico. Finalmente, la inversa de XᵀX contiene entradas grandes y opuestas que se compensan entre sí, lo que revela inestabilidad numérica.

**Puntos clave:**
- n = 10: muestra muy pequeña, riesgo de memorización.
- Colinealidad r = 0,986: coeficientes inestables individualmente.
- No extrapolar fuera de 0–103 GWh ni a fuentes no representadas.
- Escenario "b₀ = 0": SSE se triplica.
- Escenario "sin X₂": R² cae.
- Inversa de XᵀX con entradas grandes y opuestas.

**Pregunta probable del jurado:** *¿Cuál es la limitación más grave?*  
**Respuesta:** La combinación del tamaño muestral pequeño (n = 10) con la alta colinealidad (r = 0,986). Esto inestabiliza los coeficientes individuales y hace peligroso extrapolar o generalizar sin más datos.

---

### Diapositiva 12 — Conclusiones y reproducibilidad

**Tiempo sugerido:** 1 minuto 30 segundos

**Qué mostrar en pantalla:** Señale el panel derecho con la cadena de scripts (01 → 02 → 03) y el archivo DOCX final.

**Qué decir:**

> Para concluir: la regresión lineal múltiple entrega una ecuación explícita, auditable y barata de calcular —invertir una matriz 3×3 toma milisegundos—. Frente a una caja negra, cada coeficiente tiene una lectura operativa útil para la planeación energética. El valor pedagógico de este trabajo está en entender qué optimiza la máquina; el valor productivo está en automatizarlo con NumPy. Para una operación real, recomiendo reentrenar con las 2.786 filas completas, añadir estacionalidad por mes y reportar intervalos de predicción, no solo valores puntuales. Todo lo presentado es reproducible: el script 01 descarga y limpia los datos, el script 02 calcula el modelo, genera las métricas y las figuras, y el script 03 genera el informe de Word automáticamente.

**Puntos clave:**
- Ventaja: ecuación explícita, auditable, barata (O(p³) con p = 2).
- Valor pedagógico vs. productivo.
- Recomendación real: más datos, estacionalidad (mes), intervalos no solo puntos.
- Reproducibilidad: 01_descargar.py → 02_modelo.py → 03_informe.py + CSV intermedios + DOCX.

**Pregunta probable del jurado:** *¿Qué entregarían en un entorno real?*  
**Respuesta:** Un modelo reentrenado con más datos, validación cruzada, reporte de errores con intervalos de confianza y documentación completa del pipeline de datos.

---

## Las 10 preguntas más probables del jurado

A continuación, las preguntas que con mayor probabilidad le harán los evaluadores, junto con una respuesta sugerida para cada una.

### 1. ¿Por qué eligieron Regresión Lineal Múltiple y no otro algoritmo?

**Respuesta sugerida:**  
Porque el objetivo es predecir una variable continua (promedio mensual en GWh) a partir de dos predictores continuos, y porque buscábamos un modelo interpretable con una ecuación explícita que pudiéramos desarrollar a mano. Alternativas como KNN, árboles o redes neuronales no entregan una fórmula cerrada que podamos auditar paso a paso, y una regresión simple desperdiciaría uno de los dos predictores disponibles. Además, con solo dos predictores la ecuación normal se resuelve con una matriz 3×3, ideal para el objetivo pedagógico del trabajo.

---

### 2. ¿Por qué usaron solo 10 registros si el dataset tiene 2.786?

**Respuesta sugerida:**  
Fue una decisión intencional con fines didácticos. Queríamos mostrar el cálculo exacto de la ecuación normal con matrices pequeñas que se puedan verificar manualmente, sin depender de una caja negra. Las 2.786 filas originales están disponibles en `datos_completos.csv` para una versión productiva, pero para este trabajo académico la muestra de 10 permite demostrar cada paso del cálculo de forma transparente.

---

### 3. ¿Qué significa que el máximo y el mínimo estén correlacionados (r = 0,986)?

**Respuesta sugerida:**  
Significa que cuando el máximo mensual es alto, el mínimo tiende a ser también alto, y viceversa. Esta multicolinealidad alta hace que los coeficientes individuales b₁ y b₂ sean inestables y sensibles a pequeños cambios en los datos, aunque el pronóstico combinado (ŷ) siga siendo bueno. Es una limitación importante: los coeficientes no deben interpretarse de forma aislada sin considerar esta correlación.

---

### 4. ¿El R² de 99,98 % no es demasiado bueno para ser cierto?

**Respuesta sugerida:**  
Sí, es demasiado bueno y precisamente por eso hay que ser cauteloso. Con solo 10 registros, es fácil que el modelo sobreajuste (memorice) la muestra. El R² mide qué tan bien explica los datos de entrenamiento, no qué tan bien predice datos nuevos. Por eso advertimos que no debe extrapolarse y que se necesita validación cruzada con más datos antes de confiar plenamente en el modelo.

---

### 5. ¿Cómo interpretan los coeficientes b₁ y b₂ en términos operativos?

**Respuesta sugerida:**  
b₁ = 0,3988 significa que, manteniendo todo lo demás constante, cada GWh adicional en el máximo mensual eleva el promedio mensual en aproximadamente 0,40 GWh. b₂ = 0,6904 significa que cada GWh adicional en el mínimo mensual eleva el promedio en aproximadamente 0,69 GWh. Como b₂ > b₁, el mínimo (el "piso" de generación) tiene un efecto más sostenido sobre el promedio que el máximo, que puede ser un pico puntual.

---

### 6. ¿Por qué descartaron la generación total como predictor?

**Respuesta sugerida:**  
Porque el análisis exploratorio mostró que la razón entre generación total y promedio mensual es aproximadamente igual a los días del mes (mediana del cociente = 30,0). Usar la generación total como predictor sería predecir algo trivial y estaría contaminado por la duración del mes, lo que introduciría una fuga de información. El problema limpio y físicamente coherente es predecir el promedio a partir del máximo y el mínimo.

---

### 7. ¿Qué pasaría si forzaran el intercepto b₀ a ser cero?

**Respuesta sugerida:**  
Según el análisis crítico del informe, el error al cuadrado (SSE) se triplicaría. El intercepto absorbe el sesgo global del modelo y permite un ajuste fino en valores bajos, como los registros de Bagazo y Jet-A1. Sin él, el modelo perdería precisión en esos casos.

---

### 8. ¿Qué tan confiable es la predicción de 15,22 GWh para el dato de prueba?

**Respuesta sugerida:**  
Es una interpolación dentro del rango observado de la muestra (0 a 103 GWh), por lo que es razonable y físicamente plausible, ya que cae entre el mínimo (10) y el máximo (20). Sin embargo, no es una garantía absoluta; el intervalo orientativo de ± RMSE ([14,76 ; 15,67] GWh) da una idea de la incertidumbre asociada.

---

### 9. ¿Cómo reproducir todo este trabajo?

**Respuesta sugerida:**  
El pipeline está completamente automatizado con tres scripts:
- `01_descargar.py`: descarga los datos de la API de datos.gov.co y genera `datos_completos.csv`.
- `02_modelo.py`: construye la muestra, resuelve la ecuación normal, ejecuta el gradiente descendente, calcula métricas, predice un dato nuevo y genera las figuras.
- `03_informe.py`: genera el documento Word `Informe_Regresion_Lineal_Multiple.docx` automáticamente con todas las tablas, fórmulas y figuras.
Además, los archivos CSV intermedios (`XtX.csv`, `XtX_inv.csv`, `theta.csv`, `tabla_metricas.csv`, `gradiente_iters.csv`) permiten verificar cada paso individualmente.

---

### 10. ¿Qué recomendarían para llevar este modelo a operación real?

**Respuesta sugerida:**  
Cuatro recomendaciones principales: (1) reentrenar con las 2.786 filas completas o al menos con una muestra mucho mayor que 10 registros; (2) añadir estacionalidad, por ejemplo el mes del año, como variable predictora; (3) reportar intervalos de predicción, no solo valores puntuales; y (4) realizar validación cruzada para evaluar el desempeño en datos no vistos antes de desplegar el modelo en producción.

---

## Consejos prácticos para la exposición

### Antes de presentar
1. **Abra los archivos CSV** (`theta.csv`, `tabla_metricas.csv`, `XtX.csv`) en una pestaña aparte para consultar los números exactos si se le olvida algo.
2. **Pruebe el PowerPoint** en la computadora donde presentará para verificar que las dos imágenes (`fig_convergencia.png` y `fig_real_vs_pred.png`) se vean correctamente.
3. **Practique la sustitución en vivo** de la diapositiva 10: ŷ = 0,3387 + 0,3988×20 + 0,6904×10 = 15,2191. Hacer el cálculo en voz alta genera más impacto que solo leerlo.

### Durante la presentación
1. **No se limite a leer las diapositivas.** Use las diapositivas como apoyo visual y el guion para explicar con sus propias palabras.
2. **Señale los números clave** con el puntero o el mouse: R² = 0,999763, RMSE = 0,4552, r = 0,986, theta = [0,3387, 0,3988, 0,6904].
3. **Mantenga el contacto visual** con el jurado, especialmente al hablar de las limitaciones (diapositiva 11), donde la honestidad genera credibilidad.
4. **Si le preguntan algo que no sabe**, no invente. Diga: "Ese es un buen punto; lo revisamos y le damos respuesta después".

### Manejo del tiempo
- Si ve que se va del tiempo, reduzca la diapositiva 6 (puede omitir mostrar todos los valores de Xᵀy en detalle) y la diapositiva 11 (resuma las limitaciones en 30 segundos).
- Deje al menos 3 minutos para preguntas del jurado. Es mejor terminar la presentación un poco antes y tener tiempo de calidad en el Q&A.

---

## Archivos relacionados en la carpeta

| Archivo | Rol en la presentación |
|---------|------------------------|
| `Presentacion_Regresion_Lineal_Multiple.pptx` | Diapositivas visuales (este guion las acompaña) |
| `01_descargar.py` | Descarga y limpieza de datos |
| `02_modelo.py` | Cálculo del modelo, métricas y figuras |
| `03_informe.py` | Generación del informe DOCX |
| `datos_completos.csv` | Dataset completo (2.786 filas) |
| `muestra_10.csv` | Muestra de trabajo (n = 10) |
| `theta.csv` | Coeficientes finales |
| `tabla_metricas.csv` | Errores y métricas por registro |
| `XtX.csv` / `XtX_inv.csv` | Matrices intermedias de la ecuación normal |
| `gradiente_iters.csv` / `costo_hist.csv` | Evolución del gradiente descendente |
| `fig_convergencia.png` / `fig_real_vs_pred.png` | Figuras embebidas en las diapositivas |
| `Informe_Regresion_Lineal_Multiple.docx` | Entregable formal |

---

**Fin del guion.** ¡Éxito en su presentación!