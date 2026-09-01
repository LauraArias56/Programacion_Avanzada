import random

class Matrix:

    def __init__(self, matrix1, matrix2):
        self.matrix1 = matrix1
        self.matrix2 = matrix2

    # ------------------------------------------------
    # CREAR MATRIZ
    # ------------------------------------------------

    def create_matrix(self):

        print("\n¿Cómo desea llenar la matriz?")
        print("1. Manual (ingresar valor por valor)")
        print("2. Aleatoria (números al azar)")

        while True:

            choice = input("Seleccione una opción: ")

            if choice == "1":
                return self._create_manual_matrix()

            if choice == "2":
                return self._create_random_matrix()

            print("Error: opción no válida. Intente nuevamente.")

    def _get_dimensions(self):

        while True:

            try:
                rows = int(input("Ingrese el número de filas: "))
                columns = int(input("Ingrese el número de columnas: "))

                if rows <= 0 or columns <= 0:
                    print(
                        "Error: las filas y columnas "
                        "deben ser mayores que 0."
                    )
                    continue

                return rows, columns

            except ValueError:
                print("Error: debe ingresar números enteros.")

    def _get_random_range(self):

        while True:

            try:
                minimum = int(input("Ingrese el valor mínimo: "))
                maximum = int(input("Ingrese el valor máximo: "))

                if minimum > maximum:
                    print(
                        "Error: el mínimo no puede ser "
                        "mayor que el máximo."
                    )
                    continue

                return minimum, maximum

            except ValueError:
                print("Error: debe ingresar números enteros.")

    def _create_manual_matrix(self):

        rows, columns = self._get_dimensions()
        matrix = []

        for i in range(rows):

            row = []

            for j in range(columns):

                while True:

                    try:

                        value = float(
                            input(f"Ingrese el valor [{i}][{j}]: ")
                        )

                        row.append(value)
                        break

                    except ValueError:

                        print(
                            "Error: debe ingresar un número válido."
                        )

            matrix.append(row)

        return matrix

    def _create_random_matrix(self):

        rows, columns = self._get_dimensions()
        minimum, maximum = self._get_random_range()

        matrix = [
            [
                random.randint(minimum, maximum)
                for _ in range(columns)
            ]
            for _ in range(rows)
        ]

        print("\nMatriz generada:")
        self.display(matrix)

        return matrix

    # ------------------------------------------------
    # OBTENER DIMENSIONES DE UNA MATRIZ
    # ------------------------------------------------

    def get_dimensions(self, matrix):

        if not matrix:
            return 0, 0

        rows = len(matrix)
        columns = len(matrix[0])

        return rows, columns

    # ------------------------------------------------
    # MOSTRAR MATRIZ
    # ------------------------------------------------

    def display(self, matrix):

        for row in matrix:
            print([format_number(value) for value in row])

    # ------------------------------------------------
    # VALIDAR MATRICES
    # ------------------------------------------------

    def valid_matrices(self):

        return bool(self.matrix1 and self.matrix2)

    # ------------------------------------------------
    # VALIDAR MISMO TAMAÑO
    # ------------------------------------------------

    def same_size(self):

        rows1, columns1 = self.get_dimensions(self.matrix1)
        rows2, columns2 = self.get_dimensions(self.matrix2)

        return rows1 == rows2 and columns1 == columns2

    # ------------------------------------------------
    # VALIDAR MULTIPLICACIÓN MATRICIAL
    # ------------------------------------------------

    def can_multiply(self):

        _, columns1 = self.get_dimensions(self.matrix1)
        rows2, _ = self.get_dimensions(self.matrix2)

        return columns1 == rows2

    # ------------------------------------------------
    # VALIDAR MATRIZ CUADRADA
    # ------------------------------------------------

    def is_square(self, matrix):

        rows, columns = self.get_dimensions(matrix)

        return rows == columns and rows > 0

    # ------------------------------------------------
    # HELPERS INTERNOS
    # ------------------------------------------------

    def _check_size(self):

        if not self.same_size():

            print(
                "Error: las matrices deben tener "
                "el mismo tamaño."
            )

            return False

        return True

    def _check_square(self, matrix):

        if not self.is_square(matrix):

            print(
                "Error: la matriz debe ser cuadrada "
                "para esta operación."
            )

            return False

        return True

    def _apply_elementwise(self, op):

        return [
            [op(a, b) for a, b in zip(row1, row2)]
            for row1, row2 in zip(self.matrix1, self.matrix2)
        ]

    def _scalar_multiply(self, matrix, number):

        return [[value * number for value in row] for row in matrix]

    def _determinant(self, matrix):

        size = len(matrix)

        if size == 1:
            return matrix[0][0]

        if size == 2:
            return (
                matrix[0][0] * matrix[1][1]
                - matrix[0][1] * matrix[1][0]
            )

        determinant = 0

        for column in range(size):

            minor = [
                row[:column] + row[column + 1:]
                for row in matrix[1:]
            ]

            determinant += (
                ((-1) ** column)
                * matrix[0][column]
                * self._determinant(minor)
            )

        return determinant

    # ------------------------------------------------
    # SUMA
    # ------------------------------------------------

    def add(self):

        if not self._check_size():
            return None

        return self._apply_elementwise(lambda a, b: a + b)

    # ------------------------------------------------
    # RESTA
    # ------------------------------------------------

    def subtract(self):

        if not self._check_size():
            return None

        return self._apply_elementwise(lambda a, b: a - b)

    # ------------------------------------------------
    # DIVISIÓN ELEMENTO POR ELEMENTO
    # ------------------------------------------------

    def divide(self):

        if not self._check_size():
            return None

        for row in self.matrix2:

            if any(value == 0 for value in row):

                print(
                    "Error: no se puede dividir "
                    "entre cero."
                )

                return None

        return self._apply_elementwise(lambda a, b: a / b)

    # ------------------------------------------------
    # MULTIPLICACIÓN ELEMENTO POR ELEMENTO
    # ------------------------------------------------

    def element_wise_multiplication(self):

        if not self._check_size():
            return None

        return self._apply_elementwise(lambda a, b: a * b)

    # ------------------------------------------------
    # MULTIPLICACIÓN POR ESCALAR
    # ------------------------------------------------

    def scalar_multiplication(self, matrix, number):

        return self._scalar_multiply(matrix, number)

    # ------------------------------------------------
    # MULTIPLICACIÓN MATRICIAL
    # ------------------------------------------------

    def matrix_multiplication(self):

        if not self.can_multiply():

            print(
                "Error: no se pueden multiplicar "
                "las matrices."
            )

            print(
                "Las columnas de la primera matriz "
                "deben ser iguales a las filas "
                "de la segunda."
            )

            return None

        result = []

        rows1, columns1 = self.get_dimensions(
            self.matrix1
        )

        _, columns2 = self.get_dimensions(
            self.matrix2
        )

        for i in range(rows1):

            row = []

            for j in range(columns2):

                total = 0

                for k in range(columns1):

                    total += (
                        self.matrix1[i][k]
                        * self.matrix2[k][j]
                    )

                row.append(total)

            result.append(row)

        return result

    # ------------------------------------------------
    # TRANSPUESTA
    # ------------------------------------------------

    def transpose(self, matrix):

        rows, columns = self.get_dimensions(matrix)

        return [
            [matrix[row][column] for row in range(rows)]
            for column in range(columns)
        ]

    # ------------------------------------------------
    # DETERMINANTE
    # ------------------------------------------------

    def determinant(self, matrix):

        if not self._check_square(matrix):
            return None

        return self._determinant(matrix)

    # ------------------------------------------------
    # INVERSA
    # ------------------------------------------------

    def inverse(self, matrix):

        if not self._check_square(matrix):
            return None

        size = len(matrix)

        augmented = [
            row[:] + [1.0 if i == j else 0.0 for j in range(size)]
            for i, row in enumerate(matrix)
        ]

        for i in range(size):

            pivot_row = i

            for k in range(i + 1, size):

                if abs(augmented[k][i]) > abs(augmented[pivot_row][i]):
                    pivot_row = k

            if abs(augmented[pivot_row][i]) < 1e-10:

                print(
                    "Error: la matriz no es invertible "
                    "(determinante = 0)."
                )

                return None

            augmented[i], augmented[pivot_row] = (
                augmented[pivot_row],
                augmented[i],
            )

            pivot = augmented[i][i]
            augmented[i] = [value / pivot for value in augmented[i]]

            for k in range(size):

                if k == i:
                    continue

                factor = augmented[k][i]
                augmented[k] = [
                    augmented[k][col] - factor * augmented[i][col]
                    for col in range(2 * size)
                ]

        return [row[size:] for row in augmented]


# ====================================================
# MOSTRAR RESULTADO
# ====================================================

def format_number(value):

    return f"{value:.1f}"


def show_result(result):

    if result is not None:

        print("Resultado:")

        for row in result:
            print([format_number(value) for value in row])


def show_scalar_result(result):

    if result is not None:

        print(f"Resultado: {format_number(result)}")


# ====================================================
# HELPERS DEL MENÚ
# ====================================================

def require_matrices(calculator):

    if not calculator.valid_matrices():

        print(
            "Error: primero debe crear las matrices."
        )

        return False

    return True


def select_matrix(calculator):

    while True:

        choice = input("Seleccione la matriz (1 o 2): ")

        if choice == "1":

            if not calculator.matrix1:

                print("Error: la matriz 1 no ha sido creada.")
                return None

            return calculator.matrix1

        if choice == "2":

            if not calculator.matrix2:

                print("Error: la matriz 2 no ha sido creada.")
                return None

            return calculator.matrix2

        print("Error: debe ingresar 1 o 2.")


def get_scalar():

    while True:

        try:

            number = float(
                input("Ingrese el escalar: ")
            )

            return number

        except ValueError:

            print(
                "Error: debe ingresar un número válido."
            )


# ====================================================
# OPERACIONES DEL MENÚ
# ====================================================

def op_crear(calculator):

    print("\n--- Crear primera matriz ---")

    calculator.matrix1 = calculator.create_matrix()

    print("\n--- Crear segunda matriz ---")

    calculator.matrix2 = calculator.create_matrix()

    print("\nMatrices creadas correctamente.")


def op_mostrar(calculator):

    if not require_matrices(calculator):
        return

    print("\n--- Matriz 1 ---")
    calculator.display(calculator.matrix1)

    print("\n--- Matriz 2 ---")
    calculator.display(calculator.matrix2)


def op_sumar(calculator):

    if not require_matrices(calculator):
        return

    show_result(calculator.add())


def op_restar(calculator):

    if not require_matrices(calculator):
        return

    show_result(calculator.subtract())


def op_dividir(calculator):

    if not require_matrices(calculator):
        return

    show_result(calculator.divide())


def op_elemento(calculator):

    if not require_matrices(calculator):
        return

    show_result(calculator.element_wise_multiplication())


def op_escalar1(calculator):

    if not require_matrices(calculator):
        return

    number = get_scalar()

    result = calculator.scalar_multiplication(
        calculator.matrix1, number
    )

    show_result(result)


def op_escalar2(calculator):

    if not require_matrices(calculator):
        return

    number = get_scalar()

    result = calculator.scalar_multiplication(
        calculator.matrix2, number
    )

    show_result(result)


def op_matricial(calculator):

    if not require_matrices(calculator):
        return

    show_result(calculator.matrix_multiplication())


def op_transpuesta(calculator):

    matrix = select_matrix(calculator)

    if matrix is None:
        return

    show_result(calculator.transpose(matrix))


def op_determinante(calculator):

    matrix = select_matrix(calculator)

    if matrix is None:
        return

    show_scalar_result(calculator.determinant(matrix))


def op_inversa(calculator):

    matrix = select_matrix(calculator)

    if matrix is None:
        return

    show_result(calculator.inverse(matrix))


def op_salir(a):

    print("\n¡Hasta luego!")


# ====================================================
# TABLA DE DESPACHO
# ====================================================

MENU = {
    "1": op_crear,
    "2": op_mostrar,
    "3": op_sumar,
    "4": op_restar,
    "5": op_dividir,
    "6": op_elemento,
    "7": op_escalar1,
    "8": op_escalar2,
    "9": op_matricial,
    "10": op_transpuesta,
    "11": op_determinante,
    "12": op_inversa,
    "0": op_salir,
}


matrix_calculator = Matrix([], [])


while True:

    print("\n==============================")
    print("       CALCULADORA MATRIZ")
    print("==============================")

    print("1. Crear matrices")
    print("2. Mostrar matrices")
    print("3. Suma")
    print("4. Resta")
    print("5. División")
    print("6. Multiplicación elemento por elemento")
    print("7. Multiplicación por escalar matriz 1")
    print("8. Multiplicación por escalar matriz 2")
    print("9. Multiplicación matricial")
    print("10. Transpuesta")
    print("11. Determinante")
    print("12. Inversa")
    print("0. Salir")

    option = input("\nSeleccione una opción: ")

    action = MENU.get(option)

    if action:

        action(matrix_calculator)

        if option == "0":
            break

    else:

        print(
            "Error: opción no válida. "
            "Intente nuevamente."
        )