from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, UsuarioUni, PacienteUni, EspecialistaUni
from functools import wraps

auth_bp = Blueprint('auth', __name__)

# ===========================================================================
# DECORADORES DE SEGURIDAD Y ROLES (RBAC)
# ===========================================================================

def login_required(f):
    """Verifica que el usuario haya iniciado sesión"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor inicie sesión para acceder al sistema.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles):
    """Verifica que el usuario tenga uno de los roles permitidos"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Por favor inicie sesión para continuar.', 'warning')
                return redirect(url_for('auth.login'))
            
            user_role = session.get('user_role')
            if user_role not in roles:
                flash('No cuenta con los permisos necesarios para acceder a esta sección.', 'danger')
                return redirect(url_for('dashboard')) # Redirige al dashboard general si no tiene permiso
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ===========================================================================
# RUTAS DE AUTENTICACIÓN
# ===========================================================================

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Gestiona el inicio de sesión unificado para el ecosistema"""
    if request.method == 'POST':
        correo = request.form.get('correo', '').strip().lower()
        password = request.form.get('password', '')

        if not correo or not password:
            flash('Por favor ingrese su correo y contraseña.', 'warning')
            return render_template('login.html')

        # 1. Buscar en Usuarios Universales (Superadmin, Administrador, Director, Recepcionista)
        usuario = UsuarioUni.query.filter_by(correo=correo).first()
        if usuario and usuario.check_password(password):
            if not usuario.estado:
                flash('Su cuenta se encuentra suspendida. Contacte al administrador.', 'danger')
                return render_template('login.html')
            
            # Registrar datos clave en la sesión
            session['user_id'] = usuario.id_usuario
            session['user_name'] = usuario.nombres_apellidos
            session['user_role'] = usuario.rol
            session['id_cliente'] = usuario.id_cliente # Llave multi-tenant (código de 5 dígitos de la organización)
            
            flash(f'Bienvenido al sistema, {usuario.nombres_apellidos}', 'success')
            return redirect(url_for('dashboard'))

        # 2. Buscar en Especialistas (Rol Asistencial)
        especialista = EspecialistaUni.query.filter_by(email=correo).first()
        if especialista and especialista.check_password(password):
            if not especialista.estado:
                flash('Su cuenta de especialista se encuentra inactiva.', 'danger')
                return render_template('login.html')
            
            session['user_id'] = especialista.id_especialista
            session['user_name'] = f"{especialista.nombre} {especialista.apellido}"
            session['user_role'] = 'Especialista'
            session['id_cliente'] = especialista.id_cliente
            
            flash(f'Bienvenido especialista, {especialista.nombre}', 'success')
            return redirect(url_for('dashboard'))

        # 3. Buscar en Pacientes (Rol Cliente Final - Acceso por código de 7 dígitos)
        paciente = PacienteUni.query.filter_by(email=correo).first()
        if paciente and paciente.check_password(password):
            session['user_id'] = paciente.id_paciente
            session['user_name'] = f"{paciente.nombre} {paciente.apellido}"
            session['user_role'] = 'Paciente'
            session['id_cliente'] = paciente.id_cliente
            session['codigo_7d'] = paciente.codigo_invitacion_7d
            
            flash(f'Bienvenido a su portal, {paciente.nombre}', 'success')
            return redirect(url_for('portal_paciente')) # Ruta exclusiva para pacientes

        flash('Credenciales incorrectas. Verifique su correo y contraseña.', 'danger')

    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    """Cierra la sesión del usuario actual limpiando el almacenamiento temporal"""
    session.clear()
    flash('Has cerrado sesión correctamente.', 'info')
    return redirect(url_for('auth.login'))
