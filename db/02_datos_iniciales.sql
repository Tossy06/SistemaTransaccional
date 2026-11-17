-- =====================================================================
-- Datos iniciales y de demostración
-- Contraseña de todos los usuarios de prueba: Asamblea2026*
-- (almacenada como hash bcrypt, costo 12)
-- =====================================================================
BEGIN;

INSERT INTO rol (nombre, descripcion) VALUES
  ('administrador', 'Configura conjuntos, asambleas, usuarios y conduce las votaciones'),
  ('recepcionista', 'Registra asistencia y poderes de representación'),
  ('copropietario', 'Propietario de una unidad: vota y consulta el histórico'),
  ('apoderado',     'Representa a un copropietario mediante poder y vota en su nombre'),
  ('presidente',    'Preside la asamblea y aprueba el acta'),
  ('secretario',    'Acompaña la asamblea y aprueba el acta');

INSERT INTO usuario (nombre, email, password_hash, documento, telefono) VALUES
  ('Administración Los Cerezos', 'admin@cerezos.co',      '$2b$12$DV2WNB5lg43XBKm8QqKuVeI8RxRTakUExAjtLouXaeQfdor0rpORq', '900000001', '3000000001'),
  ('Laura Recepción',            'recepcion@cerezos.co',  '$2b$12$DV2WNB5lg43XBKm8QqKuVeI8RxRTakUExAjtLouXaeQfdor0rpORq', '900000002', '3000000002'),
  ('Carlos Presidente',          'presidente@cerezos.co', '$2b$12$DV2WNB5lg43XBKm8QqKuVeI8RxRTakUExAjtLouXaeQfdor0rpORq', '1001',      '3000001001'),
  ('María Secretaria',           'secretaria@cerezos.co', '$2b$12$DV2WNB5lg43XBKm8QqKuVeI8RxRTakUExAjtLouXaeQfdor0rpORq', '1002',      '3000001002'),
  ('Andrés Pérez',               'andres@correo.co',      '$2b$12$DV2WNB5lg43XBKm8QqKuVeI8RxRTakUExAjtLouXaeQfdor0rpORq', '1003',      '3000001003'),
  ('Sofía Ramírez',              'sofia@correo.co',       '$2b$12$DV2WNB5lg43XBKm8QqKuVeI8RxRTakUExAjtLouXaeQfdor0rpORq', '1004',      '3000001004'),
  ('Jorge Apoderado',            'jorge@correo.co',       '$2b$12$DV2WNB5lg43XBKm8QqKuVeI8RxRTakUExAjtLouXaeQfdor0rpORq', '2001',      '3000002001'),
  ('Luis Martínez',              'luis@correo.co',        '$2b$12$DV2WNB5lg43XBKm8QqKuVeI8RxRTakUExAjtLouXaeQfdor0rpORq', '1007',      '3000001007'),
  ('Felipe Castro',              'felipe@correo.co',      '$2b$12$DV2WNB5lg43XBKm8QqKuVeI8RxRTakUExAjtLouXaeQfdor0rpORq', '1009',      '3000001009'),
  ('Camila Herrera',             'camila@correo.co',      '$2b$12$DV2WNB5lg43XBKm8QqKuVeI8RxRTakUExAjtLouXaeQfdor0rpORq', '1010',      '3000001010');

INSERT INTO usuario_rol (usuario_id, rol_id)
SELECT u.id, r.id FROM usuario u JOIN rol r ON
     (u.email = 'admin@cerezos.co'      AND r.nombre = 'administrador')
  OR (u.email = 'recepcion@cerezos.co'  AND r.nombre = 'recepcionista')
  OR (u.email = 'presidente@cerezos.co' AND r.nombre IN ('copropietario', 'presidente'))
  OR (u.email = 'secretaria@cerezos.co' AND r.nombre IN ('copropietario', 'secretario'))
  OR (u.email IN ('andres@correo.co', 'sofia@correo.co', 'luis@correo.co', 'felipe@correo.co',
                  'camila@correo.co') AND r.nombre = 'copropietario')
  OR (u.email = 'jorge@correo.co'       AND r.nombre = 'apoderado');

INSERT INTO conjunto (nombre, nit, direccion, ciudad, numero_unidades, coeficiente_total)
VALUES ('Conjunto Residencial Los Cerezos', '900123456-1', 'Calle 140 # 12-30', 'Bogotá', 10, 100);

INSERT INTO unidad (conjunto_id, identificador, propietario_nombre, propietario_documento,
                    propietario_email, propietario_telefono, coeficiente_copropiedad)
SELECT c.id, v.ident, v.nombre, v.doc, v.email, v.tel, v.coef
FROM conjunto c CROSS JOIN (VALUES
  ('Apto 101', 'Carlos Presidente', '1001', 'presidente@cerezos.co', '3000001001', 12.0),
  ('Apto 102', 'María Secretaria',  '1002', 'secretaria@cerezos.co', '3000001002', 11.0),
  ('Apto 201', 'Andrés Pérez',      '1003', 'andres@correo.co',      '3000001003', 10.0),
  ('Apto 202', 'Sofía Ramírez',     '1004', 'sofia@correo.co',       '3000001004', 10.0),
  ('Apto 301', 'Pedro Gómez',       '1005', 'pedro@correo.co',       '3000001005', 10.0),
  ('Apto 302', 'Ana Torres',        '1006', NULL,                    '3000001006', 10.0),
  ('Apto 401', 'Luis Martínez',     '1007', 'luis@correo.co',        '3000001007', 10.0),
  ('Apto 402', 'Diana Rojas',       '1008', NULL,                    '3000001008',  9.0),
  ('Apto 501', 'Felipe Castro',     '1009', 'felipe@correo.co',      '3000001009',  9.0),
  ('Apto 502', 'Camila Herrera',    '1010', 'camila@correo.co',      '3000001010',  9.0)
) AS v(ident, nombre, doc, email, tel, coef)
WHERE c.nit = '900123456-1';

INSERT INTO asamblea (conjunto_id, tipo, fecha, hora, lugar_modalidad, modalidad, estado)
SELECT id, 'ordinaria', DATE '2026-12-05', TIME '09:00', 'Salón comunal', 'mixta', 'programada'
FROM conjunto WHERE nit = '900123456-1';

INSERT INTO punto_orden_dia (asamblea_id, orden, descripcion, tipo_mayoria, estado)
SELECT a.id, v.orden, v.descr, v.mayoria, 'pendiente'
FROM asamblea a CROSS JOIN (VALUES
  (1, 'Aprobación del presupuesto de gastos 2027',                    'simple'),
  (2, 'Elección del consejo de administración',                       'simple'),
  (3, 'Reforma del reglamento: cambio de destinación de zona común',  'calificada_70')
) AS v(orden, descr, mayoria)
WHERE a.fecha = DATE '2026-12-05';

COMMIT;
