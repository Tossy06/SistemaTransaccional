# Sistema de Gestión Transaccional de Asambleas de Propiedad Horizontal

Proyecto final — Sistemas Transaccionales, Universidad Manuela Beltrán.
Autores: Juan Stiven Castro y David Santiago Gómez Palacios.

Aplicación web (FastAPI + PostgreSQL) para gestionar asambleas de conjuntos
residenciales según la Ley 675 de 2001: convocatoria, asistencia y poderes,
quórum en tiempo real, votación ponderada por coeficiente, segunda
convocatoria y acta con verificación de integridad (SHA-256).

## Requisitos
- Python 3.11+
- PostgreSQL 14+

## Instalación
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

createdb asambleas
psql -d asambleas -f db/01_schema.sql
psql -d asambleas -f db/02_datos_iniciales.sql

cp .env.example .env        # ajuste DATABASE_URL y SECRET_KEY
export $(cat .env | xargs)  # Windows: defina las variables manualmente
uvicorn main:app --reload
```
Abra http://127.0.0.1:8000

## Usuarios de prueba (contraseña `Asamblea2026*`)
| Correo | Roles |
|---|---|
| admin@cerezos.co | administrador |
| recepcion@cerezos.co | recepcionista |
| presidente@cerezos.co | copropietario, presidente (Apto 101) |
| secretaria@cerezos.co | copropietario, secretario (Apto 102) |
| andres@correo.co / sofia@correo.co | copropietario (Apto 201 / 202) |
| jorge@correo.co | apoderado (documento 2001) |
| luis@correo.co / felipe@correo.co / camila@correo.co | copropietario (Apto 401 / 501 / 502) |

## Cuentas de usuario
No existe registro abierto: el voto se asocia al documento de identidad.
- **Censo de propietarios**: en *Conjuntos y unidades* la administración registra las unidades una a una
  o sube un archivo Excel/CSV (botón *Descargar plantilla*). La carga es atómica: si una fila falla, no se
  registra ninguna.
- **Formulario público**: en el conjunto, *Abrir formulario* genera un enlace para compartir por WhatsApp o
  correo. Cada propietario envía unidad, nombre, documento y correo; la administración aprueba o rechaza
  cada solicitud en *Revisar solicitudes*. Una unidad tiene un solo representante y admite una sola
  solicitud pendiente; nada cuenta para votar hasta que se aprueba.
- **Primer ingreso** (`/activar`): el propietario activa su cuenta con el documento y el correo de su
  unidad; el apoderado, con el documento del poder vigente que registró la recepción.
- La administración también crea usuarios y restablece contraseñas en *Usuarios*; cada usuario cambia la
  suya en *Mi cuenta*.

## Asambleas virtuales (art. 42, Ley 675)
Cada asamblea es **presencial**, **virtual** o **mixta**. En virtual y mixta:
- Al generar la convocatoria, cada unidad recibe un **enlace único** (`/sala/<hash>`, 192 bits
  aleatorios), como en nuvoll_asambleas. Se ve y se copia en la pestaña **Participantes y enlaces**
  de la asamblea, o se descargan todos en un CSV.
- **El enlace es la credencial:** quien lo abre entra a la sala de esa unidad sin contraseña,
  **confirma su ingreso** y la unidad cuenta para el quórum. Un enlace inventado no abre nada.
- En la sala ve el punto abierto y vota; la página se actualiza sola. Cada voto queda con unidad,
  hora y, si el representante tiene cuenta, su usuario: la prueba que exige el art. 42.
- Al registrar un poder en *Poderes y asistencia*, el enlace de la unidad se **renueva** para el
  apoderado y el del propietario deja de servir.
- Mientras nadie haya ingresado, el panel permite **reabrir el orden del día**, **anular la
  convocatoria** (los enlaces dejan de servir) o **eliminar la asamblea**.
- La administración sigue la sesión en **Pantalla en vivo** y puede agregar un enlace de videollamada.

## Flujo de demostración
1. **admin**: Asambleas → asamblea #1 → *Cerrar orden del día* → *Generar convocatoria*.
2. **recepcion**: registrar asistencia (presencial o por poder; para el poder use el documento 2001).
3. **admin**: *Verificar quórum e iniciar* → *Abrir votación* en un punto.
4. **copropietarios / apoderado**: menú *Votar*.
5. **admin**: *Cerrar y contar* cada punto → *Finalizar asamblea* → *Generar acta*.
6. **presidente** y **secretaria**: aprobar el acta. Todos pueden verla en *Histórico*.

Si en el paso 3 el quórum es ≤ 50 %, la asamblea queda *sin quórum* y se habilita
*Programar segunda convocatoria* (tercer día hábil, 8:00 p. m., mismo orden del día).

## Estructura (arquitectura por capas)
Cada capa solo depende de las que están debajo: presentación → aplicación → dominio / infraestructura.
```
main.py                 punto de entrada (uvicorn main:app)
presentation/           capa de presentación (HTTP)
  app.py                creación de la app, middlewares y manejo de errores
  dependencias.py       sesión, control de roles y CSRF
  vistas.py             render de plantillas, mensajes flash y redirecciones
  routers/              controladores HTTP por módulo (RF-01 a RF-07)
  templates/ static/    formularios Jinja2 y estilos
application/            capa de aplicación (casos de uso)
  services/             un servicio por módulo; abre la transacción y orquesta los DAO
  excepciones.py        NoAutenticado, NoAutorizado
domain/                 capa de dominio (sin dependencias externas)
  reglas.py             quórum, mayorías y plazos (Ley 675)
  acta.py               redacción del acta y hash SHA-256
  catalogos.py          valores válidos (tipos, decisiones, roles de firma)
  validaciones.py       política de contraseñas y números
  excepciones.py        ReglaNegocioError
infrastructure/         capa de infraestructura
  config.py             variables de entorno
  db.py                 gestor de transacciones (COMMIT / ROLLBACK)
  errores_bd.py         traducción de errores de PostgreSQL
  seguridad.py          bcrypt y bloqueo por intentos
  dao/                  un DAO por tabla del modelo relacional
db/                     01_schema.sql (modelo, restricciones, triggers), 02_datos_iniciales.sql
tests/                  pruebas funcionales y de concurrencia (pytest)
```

## Pruebas
Las pruebas **borran y recrean** la base indicada en `DATABASE_URL`; use una base de pruebas.
```bash
createdb asambleas_test
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/asambleas_test pytest -q
```

## Diagramas del documento
La carpeta `docs/diagramas` solo contiene los diagramas en **PDF vectorial** (no pierden calidad).
Se regeneran a partir del código con `python docs/fuentes_diagramas/generar_diagramas.py` (cronograma,
arquitectura, modelo relacional y clases DAO) y `cd docs/fuentes_diagramas/fuentes && python cu.py`
(casos de uso).
