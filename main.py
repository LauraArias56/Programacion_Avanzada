"""
main.py

Punto de entrada de la aplicación. Consume la API, arma el menú por
consola y usa polimórficamente el algoritmo elegido por el usuario.
Toda la lógica de negocio (API, modelo de datos, algoritmos) vive en
`operaciones.py`; aquí solo hay flujo e interacción con el usuario.
"""

import time
from operaciones import (
    URL_API,
    CAMPOS_ORDENABLES,
    ClienteAPI,
    APIException,
    Asociacion,
    FabricaAlgoritmos,
)


def cargar_asociaciones() -> list:
    """Consulta la API y convierte cada registro en un objeto Asociacion."""
    cliente = ClienteAPI(URL_API)
    datos = cliente.obtener_datos()
    return [Asociacion(registro) for registro in datos]


def elegir_campo():
    print("\nCampos disponibles para ordenar:")
    for codigo, (etiqueta, _) in CAMPOS_ORDENABLES.items():
        print(f"  {codigo}. {etiqueta}")
    print("  0. Salir")
    opcion = input("Seleccione un campo: ").strip()
    if opcion == "0":
        return None
    campo = CAMPOS_ORDENABLES.get(opcion)
    if campo is None:
        print("Opción inválida.")
        return elegir_campo()
    return campo


def elegir_algoritmo():
    while True:
        print("\nAlgoritmos disponibles:")
        for codigo, nombre in FabricaAlgoritmos.opciones().items():
            print(f"  {codigo}. {nombre}")
        print("  C. Comparar los 9 algoritmos (tiempos)")
        opcion = input("Seleccione un algoritmo: ").strip().upper()
        if opcion == "C":
            return "COMPARAR"
        algoritmo = FabricaAlgoritmos.obtener(opcion)
        if algoritmo is not None:
            return algoritmo
        print("Opción inválida. Intente nuevamente.")


def verificar_orden(resultado, clave) -> bool:
    """CA 2.4 - Exactitud: confirma que el resultado quedó descendente."""
    return all(clave(resultado[i]) >= clave(resultado[i + 1]) for i in range(len(resultado) - 1))


def mostrar_resultado(resultado, etiqueta, clave, limite=15):
    print(f"\n{'Asociación':<45}{'Municipio':<18}{etiqueta:>18}")
    print("-" * 81)
    for obj in resultado[:limite]:
        print(f"{obj.nombre[:43]:<45}{obj.municipio:<18}{clave(obj):>18.2f}")
    if len(resultado) > limite:
        print(f"... y {len(resultado) - limite} registros más.")


def ordenar_y_mostrar(asociaciones, campo, algoritmo):
    etiqueta, atributo = campo
    extraer = lambda a: a.obtener_atributo(atributo)  # noqa: E731
    clave = lambda a: -extraer(a)  # noqa: E731

    inicio = time.perf_counter()
    resultado = algoritmo.ordenar(asociaciones, clave)
    duracion_ms = (time.perf_counter() - inicio) * 1000

    if not verificar_orden(resultado, extraer):
        print("ADVERTENCIA: el resultado no quedó correctamente ordenado.")

    print(f"\nOrdenado por '{etiqueta}' (descendente) con {algoritmo.nombre} — {duracion_ms:.3f} ms")
    mostrar_resultado(resultado, etiqueta, extraer)


def comparar_algoritmos(asociaciones, campo):
    etiqueta, atributo = campo
    extraer = lambda a: a.obtener_atributo(atributo)  # noqa: E731
    clave = lambda a: -extraer(a)  # noqa: E731

    print(f"\nComparando los 9 algoritmos ordenando por '{etiqueta}' (descendente):\n")
    print(f"{'Algoritmo':<25}{'Tiempo (ms)':>15}")
    print("-" * 40)
    for algoritmo in FabricaAlgoritmos.todos():
        inicio = time.perf_counter()
        resultado = algoritmo.ordenar(asociaciones, clave)
        duracion_ms = (time.perf_counter() - inicio) * 1000
        estado = "" if verificar_orden(resultado, extraer) else "  (¡FALLÓ!)"
        print(f"{algoritmo.nombre:<25}{duracion_ms:>15.3f}{estado}")


def main():
    print("=" * 60)
    print(" PROYECTO DE ORDENAMIENTO - ASOCIACIONES AGROPECUARIAS")
    print(" Fuente: datos.gov.co (API SODA2) - Gobernación de Boyacá")
    print("=" * 60)

    try:
        asociaciones = cargar_asociaciones()
    except APIException as error:
        print(f"\nError al obtener los datos de la API: {error}")
        print("El programa no puede continuar sin datos. Intente más tarde.")
        return
    except Exception as error:
        print(f"\nOcurrió un error inesperado: {error}")
        return

    print(f"\nSe cargaron {len(asociaciones)} asociaciones desde la API.")

    while True:
        campo = elegir_campo()
        if campo is None:
            break
        algoritmo = elegir_algoritmo()
        if algoritmo is None:
            continue
        if algoritmo == "COMPARAR":
            comparar_algoritmos(asociaciones, campo)
        else:
            ordenar_y_mostrar(asociaciones, campo, algoritmo)
        if input("\n¿Otro ordenamiento? (s/n): ").strip().lower() != "s":
            break

    print("\nPrograma finalizado. ¡Hasta pronto!")


if __name__ == "__main__":
    main()
