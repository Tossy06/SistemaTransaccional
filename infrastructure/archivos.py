"""Lectura de archivos de carga masiva (Excel .xlsx o CSV) y plantilla de ejemplo."""
import csv
import io
import unicodedata

from openpyxl import Workbook, load_workbook

from domain.excepciones import ReglaNegocioError

TAMANO_MAXIMO = 2 * 1024 * 1024  # 2 MB
MAXIMO_FILAS = 2000

# Columnas de la plantilla: encabezado visible -> clave interna.
COLUMNAS = {
    "identificador": "identificador",
    "propietario": "propietario_nombre",
    "documento": "propietario_documento",
    "correo": "propietario_email",
    "telefono": "propietario_telefono",
    "coeficiente": "coeficiente",
}
OBLIGATORIAS = ("identificador", "propietario", "documento", "coeficiente")


def _normalizar(texto) -> str:
    """'Teléfono ' -> 'telefono' (sin tildes, minúsculas, sin espacios extremos)."""
    texto = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode()
    return texto.strip().lower()


def _celda(valor) -> str:
    """Texto de una celda; 1005.0 de Excel se lee como '1005'."""
    if valor is None:
        return ""
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    return str(valor).strip()


def _filas_xlsx(contenido: bytes) -> list[list]:
    try:
        libro = load_workbook(io.BytesIO(contenido), read_only=True, data_only=True)
    except Exception as e:
        raise ReglaNegocioError("No se pudo leer el archivo de Excel. Use la plantilla .xlsx.") from e
    return [list(f) for f in libro.worksheets[0].iter_rows(values_only=True)]


def _filas_csv(contenido: bytes) -> list[list]:
    for codificacion in ("utf-8-sig", "latin-1"):
        try:
            texto = contenido.decode(codificacion)
            break
        except UnicodeDecodeError:
            continue
    separador = ";" if texto.splitlines()[0].count(";") > texto.splitlines()[0].count(",") else ","
    return list(csv.reader(io.StringIO(texto), delimiter=separador))


def leer_unidades(nombre_archivo: str, contenido: bytes) -> list[dict]:
    """Devuelve una lista de filas {clave: texto, '_fila': n} lista para validar."""
    if not contenido:
        raise ReglaNegocioError("Seleccione un archivo.")
    if len(contenido) > TAMANO_MAXIMO:
        raise ReglaNegocioError("El archivo supera 2 MB.")
    nombre = (nombre_archivo or "").lower()
    if nombre.endswith(".xlsx"):
        filas = _filas_xlsx(contenido)
    elif nombre.endswith(".csv"):
        filas = _filas_csv(contenido)
    else:
        raise ReglaNegocioError("Formato no admitido. Use un archivo .xlsx o .csv.")

    filas = [f for f in filas if any(_celda(c) for c in f)]
    if len(filas) < 2:
        raise ReglaNegocioError("El archivo no tiene filas de datos debajo de los encabezados.")
    encabezados = [_normalizar(c) for c in filas[0]]
    faltan = [c for c in OBLIGATORIAS if c not in encabezados]
    if faltan:
        raise ReglaNegocioError("Faltan columnas en el archivo: " + ", ".join(faltan) + ".")
    if len(filas) - 1 > MAXIMO_FILAS:
        raise ReglaNegocioError(f"El archivo supera el máximo de {MAXIMO_FILAS} filas.")

    resultado = []
    for numero, fila in enumerate(filas[1:], start=2):
        registro = {"_fila": numero}
        for posicion, encabezado in enumerate(encabezados):
            if encabezado in COLUMNAS:
                registro[COLUMNAS[encabezado]] = _celda(fila[posicion] if posicion < len(fila) else "")
        resultado.append(registro)
    return resultado


def plantilla_unidades() -> bytes:
    """Libro de Excel con los encabezados y dos filas de ejemplo."""
    libro = Workbook()
    hoja = libro.active
    hoja.title = "Unidades"
    hoja.append(list(COLUMNAS))
    hoja.append(["Apto 101", "Nombre del propietario", "1234567", "propietario@correo.co", "3000000000", 1.25])
    hoja.append(["Casa 7", "Otro propietario", "7654321", "", "", 0.98])
    for columna, ancho in zip("ABCDEF", (16, 32, 16, 30, 16, 14)):
        hoja.column_dimensions[columna].width = ancho
    salida = io.BytesIO()
    libro.save(salida)
    return salida.getvalue()
