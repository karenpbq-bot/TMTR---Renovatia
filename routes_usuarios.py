from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, UsuarioUni, ClienteEmpresa
from functools import wraps

usuarios_bp = Blueprint('usuarios', __name__, template_folder='templates')

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor inicie sesión para acceder al sistema.', 'warning')
            return redirect(url_for('auth.login'))
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

@usuarios_bp.route('/usuarios', methods=['GET'])
@login_required
@role_required('Superadmin', 'Director', 'Administrador')
def gestionar_usuarios():
    rol = session.get('user_role')
    cliente_id = session.get('id_cliente')
    
    busqueda = request.args.get('q', '').strip()
    filtro_rol = request.args.get('rol', '').strip()
    filtro_cliente = request.args.get('id_cliente', '').strip()

    if rol == 'Superadmin':
        query = UsuarioUni.query
        if filtro_cliente:
            query = query.filter_by(id_cliente=filtro_cliente)
    else:
        query = UsuarioUni.query.filter_by(id_cliente=cliente_id)

    if filtro_rol:
        query = query.filter_by(rol=filtro_rol)

    if busqueda:
        termino = f"%{busqueda}%"
        query = query.filter(
            (UsuarioUni.nombres_apellidos.ilike(termino)) | 
            (UsuarioUni.correo.ilike(termino)) | 
            (UsuarioUni.dni.ilike(termino))
        )

    usuarios = query.order_by(UsuarioUni.id_usuario.desc()).all()
    clientes = ClienteEmpresa.query.all() if rol == 'Superadmin' else []

    return render_template(
        'usuarios.html', 
        usuarios=usuarios, 
        clientes=clientes, 
        busqueda=busqueda, 
        filtro_rol=filtro_rol, 
        filtro_cliente=filtro_cliente
    )
