"""Ejemplo de consumo de la API desde otro sistema.

Arranca primero la API:
    python -m uvicorn api.main:app --port 8000

Luego:
    python examples/client.py
"""

import httpx

BASE_URL = "http://127.0.0.1:8000"


def main() -> None:
    with httpx.Client(base_url=BASE_URL, timeout=10) as client:
        health = client.get("/health").json()
        print(f"Servicio: {health['status']} | modelo {health['model_version']}")

        game = {
            "platform": "PS4",
            "genre": "Action",
            "publisher": "Activision",
            "year": 2015,
        }
        response = client.post("/predict", json=game)
        response.raise_for_status()
        print("\nUna prediccion:")
        print(response.json())

        batch = {
            "games": [
                {"platform": "PS2", "genre": "Sports", "publisher": "Nintendo", "year": 2006},
                {"platform": "Wii", "genre": "Racing", "publisher": "Nintendo", "year": 2008},
                {"platform": "X360", "genre": "Shooter", "publisher": "Electronic Arts", "year": 2011},
            ]
        }
        response = client.post("/predict/batch", json=batch)
        response.raise_for_status()
        data = response.json()
        print(f"\nLote de {data['count']} videojuegos:")
        for pred in data["predictions"]:
            print(f"  {pred['predicted_sales_millions']:>6} millones "
                  f"(IC95: {pred['interval_95_millions']})")

        # Caso invalido: la API responde 422 con el detalle
        bad = client.post(
            "/predict",
            json={"platform": "PS9", "genre": "Action", "publisher": "X", "year": 2015},
        )
        print(f"\nPlataforma invalida -> {bad.status_code}: {bad.json()['detail']}")


if __name__ == "__main__":
    main()
