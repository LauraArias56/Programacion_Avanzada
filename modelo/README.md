# modelo

Modelo de vision por computadora (transfer learning) y librerias de
entrenamiento / inferencia. Cubre el componente **Modelo de IA** de la rubrica.

El codigo y los artefactos estan en `../vision_api/`:

| Recurso | Ruta real |
|---|---|
| Arquitectura MobileNetV3-Small | `../vision_api/src/model.py` |
| Preprocesado (160x160, ImageNet, NCHW) | `../vision_api/src/transforms.py` |
| Entrenamiento CIFAR-10 | `../vision_api/train.py` |
| Inferencia HTTP (`POST /predict`) | `../vision_api/api/` |
| Checkpoint, metricas y figuras | `../vision_api/artifacts/` |

Librerias de modelacion: PyTorch, torchvision, scikit-learn.

## Por que CIFAR-10

No se usa CIFAR-10 para reconocer el titulo de un videojuego. Se usa como
dataset de vision reproducible, con 10 clases visuales claras, para demostrar
transfer learning (ImageNet -> CIFAR-10) en un servidor academico.

La clase predicha (avion, automovil, barco, etc.) se interpreta como **tema
visual** y se traduce a un perfil aproximado de videojuego (plataforma, genero,
editorial y ano) en `../video_games_web/app/services/game_profile.py`. El
usuario puede corregir ese perfil antes de estimar ventas.
