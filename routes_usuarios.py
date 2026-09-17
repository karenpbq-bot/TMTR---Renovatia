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

@usuarios_bp.route('/usuarios/editar/<int:id_usuario>', methods=['GET', 'POST'])
@login_required
@role_required('Superadmin', 'Director', 'Administrador')
def editar_usuario(id_usuario):
    usuario = UsuarioUni.query.get_or_404(id_usuario)
    
    if request.method == 'POST':
        usuario.nombres_apellidos = request.form.get('nombres_apellidos', '').strip()
        usuario.dni = request.form.get('dni', '').strip() or None
        usuario.correo = request.form.get('correo', '').strip()
        usuario.rol = request.form.get('rol', '').strip()
        
        if session.get('user_role') == 'Superadmin':
            id_cli = request.form.get('id_cliente')
            usuario.id_cliente = int(id_cli) if id_cli else None

        db.session.commit()
        flash('Usuario actualizado correctamente.', 'success')
        return redirect(url_for('usuarios.gestionar_usuarios'))

    clientes = ClienteEmpresa.query.all() if session.get('user_role') == 'Superadmin' else []
    return render_template('usuario_editar.html', usuario=usuario, clientes=clientes)

@usuarios_bp.route('/usuarios/reset/<int:id_usuario>', methods=['POST'])
@login_required
@role_required('Superadmin', 'Director', 'Administrador')
def reset_password(id_usuario):
    usuario = UsuarioUni.query.get_or_404(id_usuario)
    usuario.set_password('Temp2026*')
    db.session.commit()
    flash(f'Contraseña de {usuario.nombres_apellidos} restablecida a temporal (Temp2026*).', 'success')
    return redirect(url_for('usuarios.gestionar_usuarios'))

@usuarios_bp.route('/usuarios/eliminar/<int:id_usuario>', methods=['POST'])
@login_required
@role_required('Superadmin', 'Director', 'Administrador')
def eliminar_usuario(id_usuario):
    usuario = UsuarioUni.query.get_or_404(id_usuario)
    if usuario.id_usuario == session.get('user_id'):
        flash('No puede eliminar su propia cuenta activa.', 'danger')
    else:
        db.session.delete(usuario)
        db.session.commit()
        flash('Usuario eliminado correctamente.', 'success')
    return redirect(url_for('usuarios.gestionar_usuarios'))
