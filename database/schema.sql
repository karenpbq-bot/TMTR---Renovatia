-- ============================================================================
-- SCRIPT SQL: BASE DE DATOS PARA CONSULTORIO PSICOLÓGICO
-- Compatible con SQLite, PostgreSQL y MySQL (con ajustes menores)
-- ============================================================================

-- 1. TABLA: usuarios
CREATE TABLE IF NOT EXISTS usuarios (
    id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
    nombres_apellidos VARCHAR(150) NOT NULL,
    correo VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(256) NOT NULL,
    rol VARCHAR(50) NOT NULL CHECK (rol IN ('Administrador', 'Recepcionista', 'Especialista', 'Cliente')),
    fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Index para agilizar búsquedas por correo
CREATE INDEX IF NOT EXISTS idx_usuarios_correo ON usuarios(correo);


-- 2. TABLA: citas
CREATE TABLE IF NOT EXISTS citas (
    id_cita INTEGER PRIMARY KEY AUTOINCREMENT,
    id_cliente INTEGER NOT NULL,
    id_especialista INTEGER NOT NULL,
    fecha_hora DATETIME NOT NULL,
    estado VARCHAR(30) NOT NULL DEFAULT 'Programada' CHECK (estado IN ('Programada', 'Completada', 'Cancelada')),
    motivo VARCHAR(255),
    FOREIGN KEY (id_cliente) REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
    FOREIGN KEY (id_especialista) REFERENCES usuarios(id_usuario) ON DELETE RESTRICT
);


-- 3. TABLA: historias_clinicas
CREATE TABLE IF NOT EXISTS historias_clinicas (
    id_historia INTEGER PRIMARY KEY AUTOINCREMENT,
    id_cliente INTEGER NOT NULL UNIQUE,
    
    -- Ficha de Identificación
    fecha_nacimiento DATE,
    edad INTEGER,
    procedencia VARCHAR(100),
    grado_instruccion VARCHAR(100),
    institucion VARCHAR(150),
    nombres_padres VARCHAR(200),
    telefono VARCHAR(20),
    
    -- Antecedentes
    motivo_consulta TEXT,
    problema_actual TEXT,
    historia_desarrollo TEXT,
    historia_escolar_social TEXT,
    dinamica_familiar TEXT,
    
    -- Diagnóstico
    codigo_cie11_dsm5 TEXT,
    
    -- Plan de Intervención
    objetivos_menor TEXT,
    objetivos_padres TEXT,
    coordinacion_externa TEXT,
    
    -- Profesional Responsable
    psicologo_responsable VARCHAR(150),
    colegiatura_csp VARCHAR(50),
    fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (id_cliente) REFERENCES usuarios(id_usuario) ON DELETE CASCADE
);


-- 4. TABLA: sesiones_evolucion
CREATE TABLE IF NOT EXISTS sesiones_evolucion (
    id_sesion INTEGER PRIMARY KEY AUTOINCREMENT,
    id_historia INTEGER NOT NULL,
    fecha_sesion DATETIME DEFAULT CURRENT_TIMESTAMP,
    evolucion_clinica TEXT NOT NULL,
    observaciones_conductuales TEXT,
    
    FOREIGN KEY (id_historia) REFERENCES historias_clinicas(id_historia) ON DELETE CASCADE
);


-- ============================================================================
-- INSERCIÓN DEL USUARIO ADMINISTRADOR POR DEFECTO
-- Contraseña en claro recomendada: admin123
-- Hash pbkdf2:sha256 por defecto de Werkzeug
-- ============================================================================

INSERT OR IGNORE INTO usuarios (id_usuario, nombres_apellidos, correo, password_hash, rol)
VALUES (
    1,
    'Administrador General',
    'admin@consultorio.com',
    'scrypt:32768:8:1$uH3d5t7E0mY$3a8c66e2c91fa02ab72a39281a8b11140026f8664188b8f2db6cd388d7ae19ee6ff3d2a76f2d53952d76f0d3674ed0a4a8cbdfd2bcbb3d9ae1d06371f4561234',
    'Administrador'
);
