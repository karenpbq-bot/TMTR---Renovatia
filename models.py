from datetime import datetime, timezone, timedelta
import random
import string

def get_peru_time():
    peru_tz = timezone(timedelta(hours=-5))
    return datetime.now(peru_tz)

def generar_codigo(longitud=5):
    """Genera un código aleatorio alfanumérico (letras mayúsculas y números)"""
    caracteres = string.ascii_uppercase + string.digits
    return ''.join(random.choice(caracteres) for _ in range(longitud))

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# ===========================================================================
# 1. TABLAS UNIVERSALES O GENERALES (SaaS Multi-Tenant: prefijo uni_)
# ===========================================================================

class ClienteEmpresa(db.Model):
    """Control centralizado de cada consultorio o clínica cliente (Psicología, Odontología, Medicina)"""
    __tablename__ = 'uni_clientes'

    id_cliente = db.Column(db.Integer, primary_key=True, autoincrement=True)
    codigo_invitacion_5d = db.Column(db.String(5), unique=True, nullable=False, index=True, default=lambda: generar_codigo(5))
    tipo_especialidad = db.Column(db.String(50), nullable=False, default='Psicología')
    estado = db.Column(db.Boolean, default=True)

    # Información Comercial y de Marca
    nombre_empresa = db.Column(db.String(150), nullable=False)
    nombre_marca = db.Column(db.String(100), nullable=False)
    ruc = db.Column(db.String(20), unique=True, nullable=False)
    logo_url = db.Column(db.String(255), nullable=True) # Supabase Storage

    # Datos de Contacto
    representante = db.Column(db.String(150), nullable=False)
    contacto_correo = db.Column(db.String(120), nullable=False)
    contacto_telefono = db.Column(db.String(20), nullable=True)

    # Gestión de Planes y Facturación
    tipo_plan = db.Column(db.String(50), nullable=True)
    vigencia_plan = db.Column(db.Date, nullable=True)
    costo_plan = db.Column(db.Numeric(10, 2), nullable=True)
    modo_pago = db.Column(db.String(50), nullable=True)
    fecha_creacion = db.Column(db.DateTime(timezone=True), default=get_peru_time)

    # Relaciones Multi-Tenant
    usuarios = db.relationship('UsuarioUni', backref='empresa', lazy=True, cascade="all, delete-orphan")
    pacientes = db.relationship('PacienteUni', backref='empresa', lazy=True, cascade="all, delete-orphan")
    especialistas = db.relationship('EspecialistaUni', backref='empresa', lazy=True, cascade="all, delete-orphan")
    disponibilidades = db.relationship('DisponibilidadUni', backref='empresa', lazy=True, cascade="all, delete-orphan")
    citas = db.relationship('CitaUni', backref='empresa', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ClienteEmpresa {self.nombre_marca} ({self.codigo_invitacion_5d})>"


class UsuarioUni(db.Model):
    """Personal administrativo, directivo y de recepción (Superadmin, Director, Administrador, Recepcionista)"""
    __tablename__ = 'uni_usuarios'

    id_usuario = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_cliente = db.Column(db.Integer, db.ForeignKey('uni_clientes.id_cliente'), nullable=True) # Null solo para Superadmin global
    
    rol = db.Column(db.String(50), nullable=False) # 'Superadmin', 'Director', 'Administrador', 'Recepcionista'
    estado = db.Column(db.Boolean, default=True)

    # Datos Personales
    nombres_apellidos = db.Column(db.String(150), nullable=False)
    dni = db.Column(db.String(20), nullable=True)

    # Credenciales y Seguridad
    correo = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    recordar_sesion = db.Column(db.Boolean, default=False)

    # Auditoría
    fecha_registro = db.Column(db.DateTime(timezone=True), default=get_peru_time)
    ultimo_acceso = db.Column(db.DateTime(timezone=True), nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<UsuarioUni {self.nombres_apellidos} ({self.rol})>"


class EspecialistaUni(db.Model):
    """Profesionales de la salud vinculados al consultorio"""
    __tablename__ = 'uni_especialistas'

    id_especialista = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_cliente = db.Column(db.Integer, db.ForeignKey('uni_clientes.id_cliente'), nullable=False)
    estado = db.Column(db.Boolean, default=True)

    # Datos Personales y Profesionales
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    matricula = db.Column(db.String(50), nullable=True) # Colegiatura profesional
    especialidades = db.Column(db.JSON, nullable=True)

    # Contacto y Acceso
    telefono = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=True)

    # Relaciones de Agendamiento
    disponibilidades = db.relationship('DisponibilidadUni', backref='especialista', lazy=True, cascade="all, delete-orphan")
    citas = db.relationship('CitaUni', backref='especialista', lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password) if self.password_hash else False

    def __repr__(self):
        return f"<EspecialistaUni {self.nombre} {self.apellido}>"


class PacienteUni(db.Model):
    """Directorio unificado de pacientes con código de invitación de 7 dígitos"""
    __tablename__ = 'uni_pacientes'

    id_paciente = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_cliente = db.Column(db.Integer, db.ForeignKey('uni_clientes.id_cliente'), nullable=False)
    codigo_invitacion_7d = db.Column(db.String(7), unique=True, nullable=False, index=True, default=lambda: generar_codigo(7))

    # Datos Personales y Demográficos
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    dni = db.Column(db.String(20), unique=True, nullable=False)
    fecha_nac = db.Column(db.Date, nullable=True)
    telefono = db.Column(db.String(20), nullable=True)
    direccion = db.Column(db.String(255), nullable=True)

    # Información Médica de Base
    grupo_sangre = db.Column(db.String(10), nullable=True)
    obra_social = db.Column(db.String(100), nullable=True)
    nro_afiliado = db.Column(db.String(50), nullable=True)
    alergias = db.Column(db.Text, nullable=True)
    antecedentes = db.Column(db.JSON, nullable=True)

    # Credenciales y Seguridad
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    recordar_sesion = db.Column(db.Boolean, default=False)
    creado_en = db.Column(db.DateTime(timezone=True), default=get_peru_time)

    # Relaciones
    historias_clinicas = db.relationship('HistoriaClinica', backref='paciente_rel', lazy=True, cascade="all, delete-orphan")
    citas = db.relationship('CitaUni', backref='paciente', lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<PacienteUni {self.nombre} {self.apellido}>"


# ===========================================================================
# 2. MÓDULO DE AGENDAMIENTO Y CALENDARIO (Prefijo uni_)
# ===========================================================================

class DisponibilidadUni(db.Model):
    """Bloques horarios y días disponibles de los especialistas"""
    __tablename__ = 'uni_disponibilidad'

    id_disponibilidad = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_cliente = db.Column(db.Integer, db.ForeignKey('uni_clientes.id_cliente'), nullable=False)
    id_especialista = db.Column(db.Integer, db.ForeignKey('uni_especialistas.id_especialista'), nullable=False)
    
    dia_semana = db.Column(db.String(20), nullable=False) # 'Lunes', 'Martes', etc.
    hora_inicio = db.Column(db.Time, nullable=False)
    hora_fin = db.Column(db.Time, nullable=False)
    intervalo_minutos = db.Column(db.Integer, default=45)
    estado = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f"<Disponibilidad {self.dia_semana} {self.hora_inicio}-{self.hora_fin}>"


class CitaUni(db.Model):
    """Registro central de citas reservadas"""
    __tablename__ = 'uni_citas'

    id_cita = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_cliente = db.Column(db.Integer, db.ForeignKey('uni_clientes.id_cliente'), nullable=False)
    id_paciente = db.Column(db.Integer, db.ForeignKey('uni_pacientes.id_paciente'), nullable=False)
    id_especialista = db.Column(db.Integer, db.ForeignKey('uni_especialistas.id_especialista'), nullable=False)
    
    fecha_hora_inicio = db.Column(db.DateTime(timezone=True), nullable=False)
    fecha_hora_fin = db.Column(db.DateTime(timezone=True), nullable=False)
    estado_cita = db.Column(db.String(50), nullable=False, default='Programada')
    motivo_reserva = db.Column(db.Text, nullable=True)
    creado_en = db.Column(db.DateTime(timezone=True), default=get_peru_time)

    reprogramaciones = db.relationship('ReprogramacionUni', backref='cita', lazy=True, cascade="all, delete-orphan")

    # --- Propiedad puente para compatibilidad con el template antiguo ---
    @property
    def cliente(self):
        """Permite que cita.cliente apunte al paciente en las plantillas antiguas"""
        return self.paciente

    @property
    def fecha_hora(self):
        return self.fecha_hora_inicio

    @property
    def estado(self):
        return self.estado_cita

    @property
    def motivo(self):
        return self.motivo_reserva

    def __repr__(self):
        return f"<CitaUni #{self.id_cita} Estado:{self.estado_cita}>"


class ReprogramacionUni(db.Model):
    """Historial y auditoría de cambios en las citas"""
    __tablename__ = 'uni_reprogramaciones'

    id_reprogramacion = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_cita = db.Column(db.Integer, db.ForeignKey('uni_citas.id_cita'), nullable=False)
    id_cliente = db.Column(db.Integer, db.ForeignKey('uni_clientes.id_cliente'), nullable=False)
    
    fecha_hora_anterior = db.Column(db.DateTime(timezone=True), nullable=False)
    fecha_hora_nueva = db.Column(db.DateTime(timezone=True), nullable=False)
    motivo_reprogramacion = db.Column(db.Text, nullable=True)
    realizado_por = db.Column(db.String(150), nullable=True)
    fecha_cambio = db.Column(db.DateTime(timezone=True), default=get_peru_time)

    def __repr__(self):
        return f"<ReprogramacionUni Cita:{self.id_cita}>"


# ===========================================================================
# 3. TABLAS ESPECÍFICAS DE PSICOLOGÍA (Prefijo psi_)
# ===========================================================================

class HistoriaClinica(db.Model):
    __tablename__ = 'psi_historias_clinicas'

    id_historia = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_paciente = db.Column(db.Integer, db.ForeignKey('uni_pacientes.id_paciente'), nullable=False, unique=True)
    
    # Ficha de Identificación
    fecha_nacimento = db.Column(db.Date, nullable=True)
    edad = db.Column(db.Integer, nullable=True)
    procedencia = db.Column(db.String(100), nullable=True)
    grado_instruccion = db.Column(db.String(100), nullable=True)
    institucion = db.Column(db.String(150), nullable=True)
    nombres_padres = db.Column(db.String(200), nullable=True)
    telefono = db.Column(db.String(20), nullable=True)

    # Antecedentes y Clínica
    motivo_consulta = db.Column(db.Text, nullable=True)
    problema_actual = db.Column(db.Text, nullable=True)
    historia_desarrollo = db.Column(db.Text, nullable=True)
    historia_escolar_social = db.Column(db.Text, nullable=True)
    dinamica_familiar = db.Column(db.Text, nullable=True)
    codigo_cie11_dsm5 = db.Column(db.Text, nullable=True)

    # Plan de Intervención
    objetivos_menor = db.Column(db.Text, nullable=True)
    objetivos_padres = db.Column(db.Text, nullable=True)
    coordinacion_externa = db.Column(db.Text, nullable=True)

    # Psicólogo Responsable
    psicologo_responsable = db.Column(db.String(150), nullable=True)
    colegiatura_csp = db.Column(db.String(50), nullable=True)
    fecha_creacion = db.Column(db.DateTime(timezone=True), default=get_peru_time)

    sesiones_evolucion = db.relationship('SesionEvolucion', backref='historia_clinica', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<HistoriaClinica #{self.id_historia} PacienteID:{self.id_paciente}>"


class SesionEvolucion(db.Model):
    __tablename__ = 'psi_sesiones_evolucion'

    id_sesion = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_historia = db.Column(db.Integer, db.ForeignKey('psi_historias_clinicas.id_historia'), nullable=False) 
    fecha_sesion = db.Column(db.DateTime(timezone=True), default=get_peru_time)
    evolucion_clinica = db.Column(db.Text, nullable=False)
    observaciones_conductuales = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<SesionEvolucion #{self.id_sesion} Historia:{self.id_historia}>"
