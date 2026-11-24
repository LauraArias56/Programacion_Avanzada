# visualizacion

Front-end de la aplicacion: captura de imagen o video (camara / archivo) y
presentacion de resultados (etiqueta, confianza, perfil y venta estimada).

Esta carpeta cubre el componente **Visualizacion / Front-End** de la rubrica.
El codigo vive junto a Flask, que sirve HTML y assets estaticos:

| Recurso | Ruta real |
|---|---|
| Pagina de captura y resultados | `../video_games_web/app/templates/vision/` |
| Historial de inferencias | `../video_games_web/app/templates/vision/history.html` |
| Camara, canvas y envio de la imagen | `../video_games_web/app/static/js/vision.js` |
| Estilos de la captura | `../video_games_web/app/static/css/vision.css` |
| Metricas del modelo (matriz, curvas) | `../vision_api/artifacts/figures/` |

Flujo que ve el usuario:

1. Activa la camara o sube un JPG/PNG/WebP.
2. Flask recibe el archivo en `POST /vision/predict`.
3. La interfaz muestra clase visual, confianza, top-k, perfil inferido y venta.
4. El historial queda en PostgreSQL y se consulta en `/vision/history`.
