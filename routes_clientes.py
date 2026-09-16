from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, ClienteEmpresa
from functools import wraps

clientes_bp = Blueprint('clientes', __name__, template_folder='templates')

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

@clientes_bp.route('/clientes', methods=['GET', 'POST'])
@login_required
@role_required('Superadmin')
def gestionar_clientes():
    if request.method == 'POST':
        nombre_marca = request.form.get('nombre_marca', '').strip()
        ruc = request.form.get('ruc', '').strip()
        direccion = request.form.get('direccion', '').strip()
        telefono = request.form.get('telefono', '').strip()
        correo_contacto = request.form.get('correo_contacto', '').strip()

        if not nombre_marca:
            flash('El nombre de la marca o clínica es obligatorio.', 'warning')
        else:
            nuevo_cliente = ClienteEmpresa(
                nombre_marca=nombre_marca,
                ruc=ruc if ruc else None,
                direccion=direccion if direccion else None,
                telefono=telefono if telefono else None,
                correo_contacto=correo_contacto if correo_contacto else None,
                estado_suscripcion='Activo'
            )
            db.session.add(nuevo_cliente)
            db.session.commit()
            flash(f'Empresa cliente "{nombre_marca}" registrada exitosamente en Supabase.', 'success')
        
        return redirect(url_for('clientes.gestionar_clientes'))

    clientes = ClienteEmpresa.query.order_by(ClienteEmpresa.id_cliente.desc()).all()
    return render_template('clientes.html', clientes=clientes)

@clientes_bp.route('/clientes/editar/<int:id_cliente>', methods=['POST'])
@login_required
@role_required('Superadmin')
def editar_cliente(id_cliente):
    cliente = ClienteEmpresa.query.get_or_404(id_cliente)
    
    cliente.nombre_marca = request.form.get('nombre_marca', '').strip()
    cliente.ruc = request.form.get('ruc', '').strip()
    cliente.direccion = request.form.get('direccion', '').strip()
    cliente.telefono = request.form.get('telefono', '').strip()
    cliente.correo_contacto = request.form.get('correo_contacto', '').strip()
    cliente.estado_suscripcion = request.form.get('estado_suscripcion', 'Activo')

    db.session.commit()
    flash(f'Datos de la empresa "{cliente.nombre_marca}" actualizados correctamente.', 'success')
    return redirect(url_for('clientes.gestionar_clientes'))
