# 🧠 Sistema de Gestión de Consultorio Psicológico

Aplicación Web Full Stack desarrollada en Python con **Flask**, **Flask-SQLAlchemy** y **SQLite** para la administración integral de un consultorio psicológico.

## 📋 Características Principales

- **Control de Acceso por Roles (RBAC)** con 4 tipos de usuarios permitidos:
  - `Administrador`: Acceso total al sistema, creación de usuarios y roles.
  - `Recepcionista`: Programación de citas y consulta de historias clínicas.
  - `Especialista`: Gestión completa de historias clínicas y registro de sesiones de evolución.
  - `Cliente`: Visualización de sus propias citas e historial clínico.

- **Base de Datos Relacional con 4 Tablas Principales**:
  1. `usuarios`: Nombres, correo único, contraseña encriptada (hash) y rol.
  2. `citas`: Vinculación Cliente - Especialista, fecha/hora y estados (`Programada`, `Completada`, `Cancelada`).
  3. `historias_clinicas`: Ficha de Identificación, Antecedentes, Diagnóstico CIE-11/DSM-5 y Plan de Intervención.
  4. `sesiones_evolucion`: Bitácora continua de evoluciones clínicas y observaciones conductuales.

---

## 🐳 Despliegue con Docker y Docker Compose (Recomendado)

### 1. Construir y Levantar el Contenedor
```bash
docker-compose up --build -d
```

### 2. Verificar Estado del Servicio
```bash
docker-compose ps
```

### 3. Acceder a la Aplicación
Abra su navegador en `http://localhost:5000`.

> **Datos de Acceso Administrador por Defecto**:
> - **Correo**: `admin@consultorio.com`
> - **Contraseña**: `admin123`

---

## 💻 Despliegue Local Tradicional (Sin Docker)

### 1. Instalar Dependencias
```bash
pip install -r requirements.txt
```

### 2. Inicializar Base de Datos
```bash
python init_db.py
```

### 3. Iniciar Servidor
```bash
python app.py
```
