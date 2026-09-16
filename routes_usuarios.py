from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, UsuarioUni, ClienteEmpresa, get_peru_time
from functools import wraps
import secrets

usuarios_bp = Blueprint('usuarios', __name__, template_folder='templates')

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor inicie sesión para acceder al sistema.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if session.get('user_role') not in roles:
                flash('No cuenta con los permisos necesarios para acceder a esta función.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@usuarios_bp.route('/usuarios', methods=['GET', 'POST'])
@login_required
@role_required('Superadmin', 'Director', 'Administrador')
def gestionar_usuarios():
    cliente_id_sesion = session.get('id_cliente')
    rol_sesion = session.get('user_role')

    if request.method == 'POST':
        nombres = request.form.get('nombres_apellidos', '').strip()
        correo = request.form.get('correo', '').strip()
        dni = request.form.get('dni', '').strip()
        rol = request.form.get('rol', 'Recepcionista')
        
        # Superadmin asigna el cliente que elija; el Administrador usa su propia clínica fija
        id_cliente_form = request.form.get('id_cliente') if rol_sesion == 'Superadmin' else cliente_id_sesion

        if UsuarioUni.query.filter_by(correo=correo).first():
            flash('El correo ingresado ya se encuentra registrado en el sistema.', 'warning')
        else:
            nuevo_usuario = UsuarioUni(
                id_cliente=id_cliente_form if id_cliente_form else None,
                nombres_apellidos=nombres,
                dni=dni,
                correo=correo,
                rol=rol
            )
            # Generar contraseña temporal inicial segura
            clave_temporal = "Temp2026*"
            nuevo_usuario.set_password(clave_temporal)
            
            db.session.add(nuevo_usuario)
            db.session.commit()
            flash(f'Usuario "{nombres}" ({rol}) registrado con éxito. Clave temporal: {clave_temporal}', 'success')

        return redirect(url_for('usuarios.gestionar_usuarios'))

    # Consultas filtradas por multi-tenant
    query = UsuarioUni.query
    if rol_sesion != 'Superadmin':
        query = query.filter_by(id_cliente=cliente_id_sesion)

    lista_usuarios = query.order_by(UsuarioUni.id_usuario.desc()).all()
    lista_clientes = ClienteEmpresa.query.all() if rol_sesion == 'Superadmin' else []

    return render_template('usuarios.html', usuarios=lista_usuarios, clientes=lista_clientes)
