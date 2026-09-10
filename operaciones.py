"""
operaciones.py

Contiene todas las clases del proyecto, agrupadas por responsabilidad
en tres secciones:

  1. CONEXIÓN A LA API       -> APIException, ClienteAPI
  2. MODELO DE DATOS         -> Asociacion
  3. ALGORITMOS DE ORDENAMIENTO -> AlgoritmoOrdenamiento (clase abstracta)
                                   y sus 9 subclases concretas
     + FabricaAlgoritmos (registro central de los algoritmos)

`main.py` solo importa de aquí y arma el menú; ninguna lógica de
negocio vive en `main.py`.
"""

from abc import ABC, abstractmethod
import re
import struct

import requests


# =====================================================================
# 1. CONEXIÓN A LA API
# =====================================================================

URL_API = "https://www.datos.gov.co/resource/cuec-zf9t.json"


class APIException(Exception):
    """Excepción propia para cualquier fallo al consultar la API externa."""
    pass


class ClienteAPI:
    """Encapsula la conexión HTTP a la API SODA2 y el manejo de sus errores."""

    def __init__(self, url: str, limite: int = 1000):
        self.url = url
        self.limite = limite
        self._headers = {"User-Agent": "Mozilla/5.0 (compatible; ProyectoOrdenamiento/1.0)"}

    def obtener_datos(self) -> list:
        """Consulta la API y retorna la lista de registros (dict). Lanza APIException si falla."""
        try:
            respuesta = requests.get(
                self.url, params={"$limit": self.limite}, headers=self._headers, timeout=15
            )
            respuesta.raise_for_status()
        except requests.exceptions.ConnectionError:
            raise APIException("No fue posible conectarse a la API. Verifique su conexión.")
        except requests.exceptions.Timeout:
            raise APIException("La API tardó demasiado en responder (timeout).")
        except requests.exceptions.HTTPError as e:
            raise APIException(f"La API respondió con un error HTTP: {e}")
        except requests.exceptions.RequestException as e:
            raise APIException(f"Error inesperado al consultar la API: {e}")

        try:
            datos = respuesta.json()
        except ValueError:
            raise APIException("La respuesta de la API no es un JSON válido.")

        if not datos:
            raise APIException("La API no devolvió registros.")

        return datos


# =====================================================================
# 2. MODELO DE DATOS
# =====================================================================

# Campos numéricos que el usuario puede elegir para ordenar:
# codigo -> (etiqueta visible, nombre del atributo en Asociacion)
CAMPOS_ORDENABLES = {
    "1": ("Número total de asociados", "numero_total_de_asociados"),
    "2": ("Número de asociados activos", "numero_de_asociados_activos"),
    "3": ("Socias activas (mujeres)", "socios_activos_mujeres"),
    "4": ("Socios activos (hombres)", "socios_activos_hombres"),
    "5": ("Total de beneficiarios", "total_beneficiarios"),
    "6": ("Área total sembrada (ha)", "total_sembrada_en_ha"),
    "7": ("Rendimiento reportado", "cual_es_el_rendimiento"),
    "8": ("Área disponible (ha)", "area_disponible_en_ha"),
}


class Asociacion:
    """Representa un registro (fila) del dataset, con sus campos ya convertidos a número."""

    def __init__(self, registro: dict):
        self.nombre = registro.get("nombre_de_la_asociacion", "Sin nombre").strip().title()
        self.municipio = registro.get("municipio", "Sin municipio")

        self.numero_total_de_asociados = self._a_numero(registro.get("numero_total_de_asociados"))
        self.numero_de_asociados_activos = self._a_numero(registro.get("n_mero_de_asociados_activos"))
        self.socios_activos_mujeres = self._a_numero(registro.get("socios_activos_mujeres"))
        self.socios_activos_hombres = self._a_numero(registro.get("socios_activos_hombres"))
        self.total_beneficiarios = self._a_numero(registro.get("total_beneficiarios"))
        self.total_sembrada_en_ha = self._a_hectareas(registro.get("total_sembrada_en_ha"))
        self.cual_es_el_rendimiento = self._a_numero(registro.get("cual_es_el_rendimiento"))
        self.area_disponible_en_ha = self._a_hectareas(registro.get("area_disponible_en_ha"))

    _PATRON_NUMERO = re.compile(r"[-+]?\d+(?:[\d.,]*\d)?")
    _PATRON_FECHA = re.compile(
        r"^\d{1,2}\s*[-/]\s*(?:\d{1,2}\s*[-/]\s*\d{2,4}|[a-záéíóú]{3,})",
        re.IGNORECASE,
    )
    _PATRON_FRACCION = re.compile(r"^\d+\s*/\s*\d+\b")
    _PATRON_METROS_CUADRADOS = re.compile(
        r"(metros\s*cuadrados|cuadrados|\bm2\b|m\s*[²2]\b|mts\s*[²2]|mtr\s*[²2]|\bmetros\b)",
        re.IGNORECASE,
    )
    _PATRON_NO_AREA = re.compile(
        r"(litros?|toneladas?|huevos?|gallinas?|pollos?|vacas?|cabezas?|"
        r"estanques?|pocetas?|posetas?|pesetas?|colmenas?|unidades?\s+de|[%])",
        re.IGNORECASE,
    )

    @staticmethod
    def _a_numero(valor) -> float:
        """Convierte texto libre de la API a float de forma fiel al valor numérico
        del dataset. Maneja comas (decimal o miles), fracciones ("1/4"), texto con
        el número en cualquier posición ("Disponibles 80 Ha") y descarta fechas
        ("1-Feb"). Si no contiene un número válido, retorna 0.0."""
        if valor is None:
            return 0.0
        texto = str(valor).strip()
        if not texto:
            return 0.0
        if texto[:2].lower() == "o.":  # tipeo frecuente: "o.5" en vez de "0.5"
            texto = "0." + texto[2:]
        if Asociacion._PATRON_FECHA.match(texto):
            return 0.0
        if Asociacion._PATRON_FRACCION.match(texto):
            numerador, resto = texto.split("/", 1)
            try:
                return float(numerador.strip()) / float(resto.split()[0].strip())
            except (ValueError, ZeroDivisionError):
                return 0.0
        coincidencia = Asociacion._PATRON_NUMERO.search(texto)
        if not coincidencia:
            return 0.0
        numero = coincidencia.group(0)
        if "," in numero:
            if "." in numero and re.search(r",\d{3}(?:\.|$)", numero):
                numero = numero.replace(",", "")
            else:
                numero = numero.replace(",", ".")
        try:
            return float(numero)
        except (ValueError, TypeError):
            return 0.0

    def _a_hectareas(self, valor) -> float:
        """Igual que `_a_numero` pero para los campos de área del dataset:
        convierte a hectáreas los valores en metros cuadrados (m²), descarta los
        que expresan cantidades que NO son área (litros, huevos, estanques, ...)."""
        numero = self._a_numero(valor)
        if numero == 0.0 or valor is None:
            return numero
        texto = str(valor)
        if self._PATRON_NO_AREA.search(texto):
            return 0.0
        if self._PATRON_METROS_CUADRADOS.search(texto):
            numero /= 10000.0
        return numero

    def obtener_atributo(self, nombre: str) -> float:
        return getattr(self, nombre, 0.0)

    def __repr__(self):
        return f"Asociacion({self.nombre}, {self.municipio})"


# =====================================================================
# 3. ALGORITMOS DE ORDENAMIENTO
# =====================================================================

class AlgoritmoOrdenamiento(ABC):
    """
    Clase base abstracta. Todo algoritmo concreto debe implementar
    `ordenar(datos, clave)`, donde `clave` es una función que extrae
    el valor numérico de comparación de cada objeto. Gracias a este
    contrato común, la aplicación usa cualquier algoritmo de forma
    POLIMÓRFICA, sin importar cuál fue elegido en tiempo de ejecución.
    """

    nombre = "Algoritmo base"

    @abstractmethod
    def ordenar(self, datos: list, clave) -> list:
        raise NotImplementedError


class OrdenamientoBurbuja(AlgoritmoOrdenamiento):
    """Burbuja - O(n²): intercambia elementos adyacentes fuera de orden."""
    nombre = "Burbuja"

    def ordenar(self, datos, clave):
        lista = list(datos)
        n = len(lista)
        for i in range(n - 1):
            intercambio = False
            for j in range(n - 1 - i):
                if clave(lista[j]) > clave(lista[j + 1]):
                    lista[j], lista[j + 1] = lista[j + 1], lista[j]
                    intercambio = True
            if not intercambio:
                break
        return lista


class OrdenamientoSeleccion(AlgoritmoOrdenamiento):
    """Selección - O(n²): busca el mínimo restante y lo coloca en su posición."""
    nombre = "Selección"

    def ordenar(self, datos, clave):
        lista = list(datos)
        n = len(lista)
        for i in range(n - 1):
            menor = i
            for j in range(i + 1, n):
                if clave(lista[j]) < clave(lista[menor]):
                    menor = j
            if menor != i:
                lista[i], lista[menor] = lista[menor], lista[i]
        return lista


class OrdenamientoInsercion(AlgoritmoOrdenamiento):
    """Inserción - O(n²): inserta cada elemento en la posición correcta de la parte ya ordenada."""
    nombre = "Inserción"

    def ordenar(self, datos, clave):
        lista = list(datos)
        for i in range(1, len(lista)):
            actual = lista[i]
            valor = clave(actual)
            j = i - 1
            while j >= 0 and clave(lista[j]) > valor:
                lista[j + 1] = lista[j]
                j -= 1
            lista[j + 1] = actual
        return lista


class OrdenamientoMerge(AlgoritmoOrdenamiento):
    """Merge Sort - O(n log n): divide la lista y mezcla las mitades ya ordenadas."""
    nombre = "Merge (mezcla)"

    def ordenar(self, datos, clave):
        lista = list(datos)
        if len(lista) <= 1:
            return lista
        medio = len(lista) // 2
        izquierda = self.ordenar(lista[:medio], clave)
        derecha = self.ordenar(lista[medio:], clave)
        return self._mezclar(izquierda, derecha, clave)

    @staticmethod
    def _mezclar(izquierda, derecha, clave):
        resultado, i, j = [], 0, 0
        while i < len(izquierda) and j < len(derecha):
            if clave(izquierda[i]) <= clave(derecha[j]):
                resultado.append(izquierda[i]); i += 1
            else:
                resultado.append(derecha[j]); j += 1
        resultado.extend(izquierda[i:])
        resultado.extend(derecha[j:])
        return resultado


class OrdenamientoQuick(AlgoritmoOrdenamiento):
    """Quick Sort - O(n log n) promedio: particiona la lista alrededor de un pivote."""
    nombre = "Quick (rápido)"

    def ordenar(self, datos, clave):
        lista = list(datos)
        self._quick(lista, 0, len(lista) - 1, clave)
        return lista

    def _quick(self, lista, inicio, fin, clave):
        if inicio < fin:
            p = self._particionar(lista, inicio, fin, clave)
            self._quick(lista, inicio, p - 1, clave)
            self._quick(lista, p + 1, fin, clave)

    @staticmethod
    def _particionar(lista, inicio, fin, clave):
        pivote = clave(lista[fin])
        i = inicio - 1
        for j in range(inicio, fin):
            if clave(lista[j]) <= pivote:
                i += 1
                lista[i], lista[j] = lista[j], lista[i]
        lista[i + 1], lista[fin] = lista[fin], lista[i + 1]
        return i + 1


class OrdenamientoHeap(AlgoritmoOrdenamiento):
    """Heap Sort - O(n log n): construye un montículo máximo y extrae repetidamente la raíz."""
    nombre = "Heap (montículo)"

    def ordenar(self, datos, clave):
        lista = list(datos)
        n = len(lista)
        for i in range(n // 2 - 1, -1, -1):
            self._heapify(lista, n, i, clave)
        for i in range(n - 1, 0, -1):
            lista[0], lista[i] = lista[i], lista[0]
            self._heapify(lista, i, 0, clave)
        return lista

    def _heapify(self, lista, n, i, clave):
        mayor = i
        izq, der = 2 * i + 1, 2 * i + 2
        if izq < n and clave(lista[izq]) > clave(lista[mayor]):
            mayor = izq
        if der < n and clave(lista[der]) > clave(lista[mayor]):
            mayor = der
        if mayor != i:
            lista[i], lista[mayor] = lista[mayor], lista[i]
            self._heapify(lista, n, mayor, clave)


class OrdenamientoCounting(AlgoritmoOrdenamiento):
    """Counting Sort - O(n+u): cuenta ocurrencias de cada valor distinto y calcula posiciones."""
    nombre = "Counting (conteo)"

    def ordenar(self, datos, clave):
        lista = list(datos)
        if not lista:
            return lista
        valores = [clave(x) for x in lista]
        unicos = sorted(set(valores))  # valores exactos, sin redondear
        frecuencias = {v: 0 for v in unicos}
        for v in valores:
            frecuencias[v] += 1

        posiciones = {}
        acumulado = 0
        for v in unicos:
            posiciones[v] = acumulado
            acumulado += frecuencias[v]

        salida = [None] * len(lista)
        for item, v in zip(lista, valores):
            salida[posiciones[v]] = item
            posiciones[v] += 1
        return salida


class OrdenamientoRadix(AlgoritmoOrdenamiento):
    """Radix Sort (LSD) - O(d·n): ordena por dígitos usando los bits de cada valor como clave entera."""
    nombre = "Radix (dígitos)"

    _MASCARA_BITS = (1 << 64) - 1

    @staticmethod
    def _clave_entera(valor: float) -> int:
        """Convierte un float a un entero que preserva su orden exacto (incluye negativos)."""
        bits = struct.unpack("<Q", struct.pack("<d", valor))[0]
        if bits >> 63:
            return bits ^ OrdenamientoRadix._MASCARA_BITS
        return bits | (1 << 63)

    def ordenar(self, datos, clave):
        lista = list(datos)
        if not lista:
            return lista
        claves = [self._clave_entera(clave(x)) for x in lista]
        pares = list(zip(claves, lista))

        maximo = max(claves)
        exp = 1
        while maximo // exp > 0:
            pares = self._por_digito(pares, exp)
            exp *= 10
        return [item for _, item in pares]

    @staticmethod
    def _por_digito(pares, exp):
        n = len(pares)
        salida = [None] * n
        conteo = [0] * 10
        for v, _ in pares:
            conteo[(v // exp) % 10] += 1
        for i in range(1, 10):
            conteo[i] += conteo[i - 1]
        for i in range(n - 1, -1, -1):
            v, item = pares[i]
            d = (v // exp) % 10
            salida[conteo[d] - 1] = (v, item)
            conteo[d] -= 1
        return salida


class OrdenamientoBucket(AlgoritmoOrdenamiento):
    """Bucket Sort - O(n+k) promedio: distribuye en cubetas y ordena cada una por inserción."""
    nombre = "Bucket (cubetas)"

    def ordenar(self, datos, clave):
        lista = list(datos)
        n = len(lista)
        if n == 0:
            return lista
        valores = [clave(x) for x in lista]
        minimo, maximo = min(valores), max(valores)
        rango = (maximo - minimo) or 1.0

        num_cubetas = max(1, int(n ** 0.5))
        cubetas = [[] for _ in range(num_cubetas)]
        for item, v in zip(lista, valores):
            idx = int((v - minimo) / rango * (num_cubetas - 1)) if num_cubetas > 1 else 0
            idx = min(max(idx, 0), num_cubetas - 1)
            cubetas[idx].append(item)

        insercion = OrdenamientoInsercion()
        resultado = []
        for cubeta in cubetas:
            resultado.extend(insercion.ordenar(cubeta, clave))
        return resultado


class FabricaAlgoritmos:
    """Registro centralizado de los 9 algoritmos disponibles (patrón Factory)."""

    _algoritmos = {
        "1": OrdenamientoBurbuja(),
        "2": OrdenamientoSeleccion(),
        "3": OrdenamientoInsercion(),
        "4": OrdenamientoMerge(),
        "5": OrdenamientoQuick(),
        "6": OrdenamientoHeap(),
        "7": OrdenamientoCounting(),
        "8": OrdenamientoRadix(),
        "9": OrdenamientoBucket(),
    }

    @classmethod
    def opciones(cls) -> dict:
        return {c: a.nombre for c, a in cls._algoritmos.items()}

    @classmethod
    def obtener(cls, codigo: str):
        return cls._algoritmos.get(codigo)

    @classmethod
    def todos(cls) -> list:
        return list(cls._algoritmos.values())
