from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, PacienteUni
from routes_auth import login_required, role_required
import random
import string

pacientes_bp = Blueprint('pacientes', __name__)

def generar_codigo_7d():
    """Genera un código único de 7 caracteres alfanuméricos para el paciente"""
    while True:
        codigo = ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))
        existe = PacienteUni.query.filter_by(codigo_invitacion_7d=codigo).first()
        if not existe:
            return codigo

@pacientes_bp.route('/pacientes', methods=['GET', 'POST'])
@login_required
@role_required('Superadmin', 'Director', 'Administrador', 'Recepcionista', 'Especialista')
def gestionar_pacientes():
    """Gestiona el listado y registro de pacientes asegurando el aislamiento multi-tenant"""
    cliente_id = session.get('id_cliente')
    rol = session.get('user_role')

    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        apellido = request.form.get('apellido', '').strip()
        email = request.form.get('email', '').strip().lower()
        telefono = request.form.get('telefono', '').strip()
        dni = request.form.get('dni', '').strip()
        password = request.form.get('password', 'paciente123') # Contraseña inicial por defecto

        if not nombre or not apellido or not email:
            flash('El nombre, apellido y correo electrónico del paciente son obligatorios.', 'warning')
        else:
            email_existente = PacienteUni.query.filter_by(email=email).first()
            if email_existente:
                flash('Ya existe un paciente registrado con ese correo electrónico en el sistema.', 'danger')
            else:
                codigo_7d = generar_codigo_7d()
                
                nuevo_paciente = PacienteUni(
                    id_cliente=cliente_id,
                    nombre=nombre,
                    apellido=apellido,
                    email=email,
                    telefono=telefono if telefono else None,
                    dni=dni if dni else None,
                    codigo_invitacion_7d=codigo_7d
                )
                nuevo_paciente.set_password(password)
                
                db.session.add(nuevo_paciente)
                db.session.commit()
                flash(f'Paciente {nombre} {apellido} registrado exitosamente. Código de Acceso 7D: {codigo_7d}', 'success')
        
        return redirect(url_for('pacientes.gestionar_pacientes'))

    # Filtrado Multi-Tenant estricto
    if rol == 'Superadmin':
        lista_pacientes = PacienteUni.query.all()
    else:
        lista_pacientes = PacienteUni.query.filter_by(id_cliente=cliente_id).all()

    return render_template('pacientes.html', pacientes=lista_pacientes)
