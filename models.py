from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

ROLES_PERMITIDOS = ['Administrador', 'Recepcionista', 'Especialista', 'Cliente']
ESTADOS_CITA = ['Programada', 'Completada', 'Cancelada']

class Usuario(db.Model):
    __tablename__ = 'ren_usuarios'

    id_usuario = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombres_apellidos = db.Column(db.String(150), nullable=False)
    correo = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    rol = db.Column(db.String(50), nullable=False, default='Cliente')
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

    # Relaciones
    citas_como_cliente = db.relationship(
        'Cita', 
        foreign_keys='Cita.id_cliente', 
        backref='cliente', 
        lazy=True, 
        cascade="all, delete-orphan"
    )
    citas_como_especialista = db.relationship(
        'Cita', 
        foreign_keys='Cita.id_especialista', 
        backref='especialista', 
        lazy=True
    )
    historias_clinicas = db.relationship(
        'HistoriaClinica', 
        backref='cliente', 
        lazy=True, 
        cascade="all, delete-orphan"
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<Usuario {self.nombres_apellidos} ({self.rol})>"


class Cita(db.Model):
    __tablename__ = 'ren_citas'

    id_cita = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_cliente = db.Column(db.Integer, db.ForeignKey('ren_usuarios.id_usuario'), nullable=False)
    id_especialista = db.Column(db.Integer, db.ForeignKey('ren_usuarios.id_usuario'), nullable=False)
    fecha_hora = db.Column(db.DateTime, nullable=False)
    estado = db.Column(db.String(30), nullable=False, default='Programada')
    motivo = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f"<Cita #{self.id_cita} Cliente:{self.id_cliente} Estado:{self.estado}>"


class HistoriaClinica(db.Model):
    __tablename__ = 'ren_historias_clinicas'

    id_historia = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_cliente = db.Column(db.Integer, db.ForeignKey('ren_usuarios.id_usuario'), nullable=False, unique=True)
    
    # Datos de Ficha de Identificación
    fecha_nacimiento = db.Column(db.Date, nullable=True)
    edad = db.Column(db.Integer, nullable=True)
    procedencia = db.Column(db.String(100), nullable=True)
    grado_instruccion = db.Column(db.String(100), nullable=True)
    institucion = db.Column(db.String(150), nullable=True)
    nombres_padres = db.Column(db.String(200), nullable=True)
    telefono = db.Column(db.String(20), nullable=True)

    # Antecedentes
    motivo_consulta = db.Column(db.Text, nullable=True)
    problema_actual = db.Column(db.Text, nullable=True)
    historia_desarrollo = db.Column(db.Text, nullable=True)
    historia_escolar_social = db.Column(db.Text, nullable=True)
    dinamica_familiar = db.Column(db.Text, nullable=True)

    # Diagnóstico
    codigo_cie11_dsm5 = db.Column(db.Text, nullable=True)

    # Plan de Intervención
    objetivos_menor = db.Column(db.Text, nullable=True)
    objetivos_padres = db.Column(db.Text, nullable=True)
    coordinacion_externa = db.Column(db.Text, nullable=True)

    # Psicólogo Responsable
    psicologo_responsable = db.Column(db.String(150), nullable=True)
    colegiatura_csp = db.Column(db.String(50), nullable=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    # Relación con sesiones de evolución
    sesiones_evolucion = db.relationship('SesionEvolucion', backref='historia_clinica', cascade='all, delete-orphan'))

    def __repr__(self):
        return f"<HistoriaClinica #{self.id_historia} Cliente:{self.id_cliente}>"


class SesionEvolucion(db.Model):
    __tablename__ = 'ren_sesiones_evolucion'

    id_sesion = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_historia = db.Column(db.Integer, db.ForeignKey('ren_historias_clinicas.id_historia'), nullable=False) 
    fecha_sesion = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    evolucion_clinica = db.Column(db.Text, nullable=False)
    observaciones_conductuales = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<SesionEvolucion #{self.id_sesion} Historia:{self.id_historia} Fecha:{self.fecha_sesion}>"
