from matrix import Matrix, format_number


class Menu:

    OPTS = [
        ("1",  "Crear matrices",                        "crear"),
        ("2",  "Mostrar matrices",                      "mostrar"),
        ("3",  "Suma",                                  "ambas", "add"),
        ("4",  "Resta",                                 "ambas", "subtract"),
        ("5",  "División",                              "ambas", "divide"),
        ("6",  "Multiplicación elemento por elemento",  "ambas", "element_wise_multiplication"),
        ("7",  "Multiplicación por escalar matriz",     "elegir", "scalar_multiplication"),
        ("8",  "Multiplicación matricial",              "ambas", "matrix_multiplication"),
        ("9",  "Transpuesta",                           "elegir", "transpose"),
        ("10", "Determinante",                          "elegir", "determinant"),
        ("11", "Inversa",                               "elegir", "inverse"),
        ("0",  "Salir",                                 "salir"),
    ]

    def __init__(self):
        self.c = Matrix([], [])

    def _res(self, r):

        if r is None:
            return

        if isinstance(r, list):

            print("Resultado:")

            for row in r:
                print([format_number(v) for v in row])

        else:

            print(f"Resultado: {format_number(r)}")

    def _ejecutar(self, spec):

        key, _, tipo = spec[:3]
        c = self.c

        if tipo in ("mostrar", "ambas") and not c.valid_matrices():
            print("Error: primero debe crear las matrices.")
            return

        if tipo == "crear":

            print("\n--- Crear primera matriz ---")
            c.matrix1 = c.create_matrix()
            print("\n--- Crear segunda matriz ---")
            c.matrix2 = c.create_matrix()
            print("\nMatrices creadas correctamente.")

        elif tipo == "mostrar":

            print("\n--- Matriz 1 ---")
            c.display(c.matrix1)
            print("\n--- Matriz 2 ---")
            c.display(c.matrix2)

        elif tipo == "ambas":

            self._res(getattr(c, spec[3])())

        elif tipo == "elegir":

            n = input("Seleccione la matriz (1 o 2): ")

            while n not in ("1", "2"):

                print("Error: debe ingresar 1 o 2.")
                n = input("Seleccione la matriz (1 o 2): ")

            m = c.matrix1 if n == "1" else c.matrix2

            if not m:
                print(f"Error: la matriz {n} no ha sido creada.")
                return

            if spec[3] == "scalar_multiplication":

                while True:

                    try:
                        number = float(input("Ingrese el escalar: "))
                        break
                    except ValueError:
                        print("Error: debe ingresar un número válido.")

                self._res(c.scalar_multiplication(m, number))

            else:

                self._res(getattr(c, spec[3])(m))

        else:

            print("\n¡Hasta luego!")

    def run(self):

        while True:

            print("\n==============================")
            print("       CALCULADORA MATRIZ")
            print("==============================")

            for key, label, *_ in self.OPTS:
                print(f"{key}. {label}")

            option = input("\nSeleccione una opción: ")

            spec = next(
                (o for o in self.OPTS if o[0] == option),
                None,
            )

            if spec is None:

                print(
                    "Error: opción no válida. "
                    "Intente nuevamente."
                )

                continue

            self._ejecutar(spec)

            if option == "0":
                break


if __name__ == "__main__":
    Menu().run()