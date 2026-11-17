"""Valores válidos del dominio. Deben coincidir con los CHECK de db/01_schema.sql."""

TIPOS_ASAMBLEA = ("ordinaria", "extraordinaria")
TIPOS_MAYORIA = ("simple", "calificada_70")
TIPOS_ASISTENCIA = ("presencial", "virtual", "poder")
# Modalidad de la reunión: la virtual y la mixta usan la sala web (art. 42, Ley 675).
MODALIDADES = ("presencial", "virtual", "mixta")
DECISIONES_VOTO = ("a_favor", "en_contra", "abstencion")

# Roles que firman el acta; con ambas firmas el acta queda aprobada.
ROLES_FIRMA_ACTA = ("presidente", "secretario")

# Roles que pueden ver actas en borrador.
ROLES_GESTION_ACTA = ("administrador", "presidente", "secretario")
