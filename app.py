from functools import wraps
from datetime import datetime, date
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from config import Config
from models import (
    db, get_peru_time, ClienteEmpresa, UsuarioUni, EspecialistaUni, 
    PacienteUni, DisponibilidadUni, CitaUni, ReprogramacionUni, 
    HistoriaClinica, SesionEvolucion
)

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

# --- CREACIÓN AUTOMÁTICA DEL SUPERADMIN / ADMIN PRINCIPAL ---
with app.app_context():
    db.create_all()
    admin_email = "kbarrientosq.2604@gmail.com"
    admin_user = UsuarioUni.query.filter_by(correo=admin_email).first()
    
    if not admin_user:
        nuevo_admin = UsuarioUni(
            nombres_apellidos="Karen Paola Barrientos",
            correo=admin_email,
            rol="Superadmin",
            id_cliente=None # Superadmin global sin clínica fija inicial
        )
        nuevo_admin.set_password("admin123")
        db.session.add(nuevo_admin)
        db.session.commit()
        print("¡Cuenta Superadmin creada exitosamente en la BD activa!")
    else:
        admin_user.rol = "Superadmin"
        admin_user.set_password("admin123")
        db.session.commit()
        print("¡Cuenta Superadmin verificada y actualizada!")

# --- Decoradores de Seguridad y Autenticación ---
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
            if 'user_id' not in session:
                flash('Sesión no iniciada.', 'danger')
                return redirect(url_for('login'))
            if session.get('user_role') not in roles:
                flash('No cuenta con los permisos necesarios para acceder a esta función.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Context Processor para disponibilizar variables globales en plantillas
@app.context_processor
def inject_globals():
    return {
        'current_user_name': session.get('user_name'),
        'current_user_role': session.get('user_role'),
        'current_user_id': session.get('user_id'),
        'current_cliente_id': session.get('id_cliente')
    }

# --- 1. Sistema de Autenticación y Redirección Multi-Tenant ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form.get('correo', '').strip()
        password = request.form.get('password', '')

        usuario = UsuarioUni.query.filter_by(correo=correo).first()
        if usuario and usuario.check_password(password):
            session['user_id'] = usuario.id_usuario
            session['user_name'] = usuario.nombres_apellidos
            session['user_role'] = usuario.rol
            session['user_email'] = usuario.correo
            session['id_cliente'] = usuario.id_cliente  # Clave maestra multi-tenant
            
            flash(f'¡Bienvenido(a), {usuario.nombres_apellidos} ({usuario.rol})!', 'success')

            # Redirección personalizada según rol
            if usuario.rol in ['Superadmin', 'Director', 'Administrador']:
                return redirect(url_for('dashboard'))
            elif usuario.rol == 'Recepcionista':
                return redirect(url_for('citas'))
            elif usuario.rol == 'Especialista':
                return redirect(url_for('historias'))
            else:
                return redirect(url_for('dashboard'))
        else:
            flash('Credenciales inválidas. Por favor verifique su correo y contraseña.', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Ha cerrado sesión correctamente.', 'info')
    return redirect(url_for('login'))

# --- Dashboard Principal (Aislado por id_cliente) ---
@app.route('/')
@login_required
def dashboard():
    rol = session.get('user_role')
    cliente_id = session.get('id_cliente')

    # Filtrado multi-tenant según el rol y la empresa
    if rol == 'Superadmin':
        total_pacientes = PacienteUni.query.count()
        total_usuarios = UsuarioUni.query.count()
        total_especialistas = EspecialistaUni.query.count()
        citas = CitaUni.query.order_by(CitaUni.fecha_hora_inicio.asc()).all()
        total_historias = HistoriaClinica.query.count()
    else:
        total_pacientes = PacienteUni.query.filter_by(id_cliente=cliente_id).count()
        total_usuarios = UsuarioUni.query.filter_by(id_cliente=cliente_id).count()
        total_especialistas = EspecialistaUni.query.filter_by(id_cliente=cliente_id).count()
        citas = CitaUni.query.filter_by(id_cliente=cliente_id).order_by(CitaUni.fecha_hora_inicio.asc()).all()
        
        # Conteo de historias clínicas ligadas a los pacientes del cliente actual
        total_historias = HistoriaClinica.query.join(PacienteUni).filter(PacienteUni.id_cliente == cliente_id).count()

    citas_programadas = sum(1 for c in citas if c.estado_cita == 'Programada')
    citas_completadas = sum(1 for c in citas if c.estado_cita == 'Completada')

    return render_template(
        'dashboard.html',
        citas=citas[:10],
        citas_programadas=citas_programadas,
        citas_completadas=citas_completadas,
        total_pacientes=total_pacientes,
        total_especialistas=total_especialistas,
        total_historias=total_historias,
        total_usuarios=total_usuarios
    )

# --- Módulo Avanzado de Gestión de Usuarios (Superadmin / Administrador) ---
@app.route('/usuarios', methods=['GET', 'POST'])
@login_required
@role_required('Superadmin', 'Director', 'Administrador')
def usuarios():
    cliente_id_sesion = session.get('id_cliente')
    rol_sesion = session.get('user_role')

    # Capturar parámetros de búsqueda y filtros desde la URL (GET)
    busqueda = request.args.get('q', '').strip()
    filtro_rol = request.args.get('rol', '').strip()
    filtro_cliente = request.args.get('id_cliente', '').strip()

    if request.method == 'POST':
        # Registro de nuevo usuario desde el panel
        nombres = request.form.get('nombres_apellidos', '').strip()
        correo = request.form.get('correo', '').strip()
        dni = request.form.get('dni', '').strip()
        rol = request.form.get('rol', 'Recepcionista')
        
        # Si es Superadmin puede asignar el cliente que elija; si es Admin, usa su propia clínica
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
            nuevo_usuario.set_password('clave123') # Contraseña inicial por defecto
            db.session.add(nuevo_usuario)
            db.session.commit()
            flash(f'Usuario "{nombres}" registrado exitosamente con clave temporal "clave123".', 'success')

        return redirect(url_for('usuarios'))

    # Construcción de consulta dinámica con filtros
    query = UsuarioUni.query

    # Restricción multi-tenant si no es Superadmin
    if rol_sesion != 'Superadmin':
        query = query.filter_by(id_cliente=cliente_id_sesion)
    elif filtro_cliente:
        query = query.filter_by(id_cliente=filtro_cliente)

    # Aplicar filtro por Rol
    if filtro_rol:
        query = query.filter_by(rol=filtro_rol)

    # Aplicar búsqueda por texto (nombre o correo)
    if busqueda:
        termino = f"%{busqueda}%"
        query = query.filter(
            db.or_(
                UsuarioUni.nombres_apellidos.ilike(termino),
                UsuarioUni.correo.ilike(termino),
                UsuarioUni.dni.ilike(termino)
            )
        )

    lista_usuarios = query.order_by(UsuarioUni.id_usuario.desc()).all()
    
    # Obtener lista de clientes para los selectores de filtrado (útil para el Superadmin)
    lista_clientes = ClienteEmpresa.query.all() if rol_sesion == 'Superadmin' else []

    return render_template(
        'usuarios.html',
        usuarios=lista_usuarios,
        clientes=lista_clientes,
        busqueda=busqueda,
        filtro_rol=filtro_rol,
        filtro_cliente=filtro_cliente
    )

# --- Editar Usuario ---
@app.route('/usuarios/editar/<int:id_usuario>', methods=['GET', 'POST'])
@login_required
@role_required('Superadmin', 'Director', 'Administrador')
def editar_usuario(id_usuario):
    usuario = UsuarioUni.query.get_or_404(id_usuario)
    rol_sesion = session.get('user_role')

    # Control de aislamiento multi-tenant
    if rol_sesion != 'Superadmin' and usuario.id_cliente != session.get('id_cliente'):
        flash('No tiene autorización para modificar este usuario.', 'danger')
        return redirect(url_for('usuarios'))

    if request.method == 'POST':
        usuario.nombres_apellidos = request.form.get('nombres_apellidos', '').strip()
        usuario.correo = request.form.get('correo', '').strip()
        usuario.dni = request.form.get('dni', '').strip()
        usuario.rol = request.form.get('rol', usuario.rol)
        
        if rol_sesion == 'Superadmin':
            id_cli = request.form.get('id_cliente')
            usuario.id_cliente = id_cli if id_cli else None

        db.session.commit()
        flash(f'Datos del usuario "{usuario.nombres_apellidos}" actualizados correctamente.', 'success')
        return redirect(url_for('usuarios'))

    lista_clientes = ClienteEmpresa.query.all() if rol_sesion == 'Superadmin' else []
    return render_template('usuario_editar.html', usuario=usuario, clientes=lista_clientes)

# --- Generar Contraseña Temporal (Recuperación por Olvido) ---
@app.route('/usuarios/reset-password/<int:id_usuario>', methods=['POST'])
@login_required
@role_required('Superadmin', 'Director', 'Administrador')
def reset_password(id_usuario):
    usuario = UsuarioUni.query.get_or_404(id_usuario)
    rol_sesion = session.get('user_role')

    if rol_sesion != 'Superadmin' and usuario.id_cliente != session.get('id_cliente'):
        flash('No autorizado.', 'danger')
        return redirect(url_for('usuarios'))

    # Generar clave temporal estándar
    clave_temporal = "Temp2026*"
    usuario.set_password(clave_temporal)
    db.session.commit()

    flash(f'Contraseña restablecida con éxito para {usuario.nombres_apellidos}. La nueva clave temporal es: {clave_temporal}', 'warning')
    return redirect(url_for('usuarios'))

# --- Eliminar Usuario ---
@app.route('/usuarios/eliminar/<int:id_usuario>', methods=['POST'])
@login_required
@role_required('Superadmin', 'Director', 'Administrador')
def eliminar_usuario(id_usuario):
    usuario = UsuarioUni.query.get_or_404(id_usuario)

    # Prevenir que un administrador elimine su propia cuenta activa
    if usuario.id_usuario == session.get('user_id'):
        flash('Por seguridad, no puedes eliminar tu propia cuenta activa.', 'danger')
        return redirect(url_for('usuarios'))

    rol_sesion = session.get('user_role')
    if rol_sesion != 'Superadmin' and usuario.id_cliente != session.get('id_cliente'):
        flash('No autorizado para eliminar este usuario.', 'danger')
        return redirect(url_for('usuarios'))

    nombre_borrado = usuario.nombres_apellidos
    db.session.delete(usuario)
    db.session.commit()
    
    flash(f'Usuario "{nombre_borrado}" eliminado correctamente.', 'info')
    return redirect(url_for('usuarios'))

# --- Módulo de Historias Clínicas (Psicología: psi_) ---
@app.route('/historias')
@login_required
@role_required('Superadmin', 'Director', 'Administrador', 'Especialista', 'Recepcionista')
def historias():
    cliente_id = session.get('id_cliente')
    rol = session.get('user_role')

    if rol == 'Superadmin':
        lista_historias = HistoriaClinica.query.all()
    else:
        # Filtrar historias clínicas cuyos pacientes pertenezcan al cliente actual
        lista_historias = HistoriaClinica.query.join(PacienteUni).filter(PacienteUni.id_cliente == cliente_id).all()

    return render_template('historias.html', historias=lista_historias)

@app.route('/historias/nueva', methods=['GET', 'POST'])
@login_required
@role_required('Superadmin', 'Director', 'Administrador', 'Especialista')
def crear_historia():
    cliente_id = session.get('id_cliente')

    if request.method == 'POST':
        id_paciente = request.form.get('id_paciente')
        
        historia_existente = HistoriaClinica.query.filter_by(id_paciente=id_paciente).first()
        if historia_existente:
            flash('Este paciente ya tiene una historia clínica aperturada.', 'warning')
            return redirect(url_for('ver_historia', id_historia=historia_existente.id_historia))

        fecha_nac_str = request.form.get('fecha_nacimiento')
        fecha_nac = datetime.strptime(fecha_nac_str, '%Y-%m-%d').date() if fecha_nac_str else None

        nueva_historia = HistoriaClinica(
            id_paciente=id_paciente,
            fecha_nacimento=fecha_nac,
            edad=int(request.form.get('edad', 0)) if request.form.get('edad') else None,
            procedencia=request.form.get('procedencia'),
            grado_instruccion=request.form.get('grado_instruccion'),
            institucion=request.form.get('institucion'),
            nombres_padres=request.form.get('nombres_padres'),
            telefono=request.form.get('telefono'),
            motivo_consulta=request.form.get('motivo_consulta'),
            problema_actual=request.form.get('problema_actual'),
            historia_desarrollo=request.form.get('historia_desarrollo'),
            historia_escolar_social=request.form.get('historia_escolar_social'),
            dinamica_familiar=request.form.get('dinamica_familiar'),
            codigo_cie11_dsm5=request.form.get('codigo_cie11_dsm5'),
            objetivos_menor=request.form.get('objetivos_menor'),
            objetivos_padres=request.form.get('objetivos_padres'),
            coordinacion_externa=request.form.get('coordinacion_externa'),
            psicologo_responsable=request.form.get('psicologo_responsable', session.get('user_name')),
            colegiatura_csp=request.form.get('colegiatura_csp')
        )
        db.session.add(nueva_historia)
        db.session.commit()
        flash('Ficha e Historia Clínica creada exitosamente.', 'success')
        return redirect(url_for('ver_historia', id_historia=nueva_historia.id_historia))

    # Pacientes del consultorio actual que aún no tienen historia clínica
    pacientes_sin_historia = PacienteUni.query.filter_by(id_cliente=cliente_id).outerjoin(HistoriaClinica).filter(HistoriaClinica.id_historia == None).all()
    return render_template('historia_nueva.html', pacientes_sin_historia=pacientes_sin_historia)

@app.route('/historias/<int:id_historia>')
@login_required
def ver_historia(id_historia):
    historia = HistoriaClinica.query.get_or_404(id_historia)
    return render_template('historia_detalle.html', historia=historia)

# --- Módulo de Citas y Agendamiento (uni_citas) ---
@app.route('/citas', methods=['GET', 'POST'])
@login_required
def citas():
    cliente_id = session.get('id_cliente')
    
    if request.method == 'POST':
        id_paciente = request.form.get('id_paciente')
        id_especialista = request.form.get('id_especialista')
        fecha_hora_str = request.form.get('fecha_hora_inicio')
        motivo = request.form.get('motivo_reserva', '')

        try:
            fecha_hora_inicio = datetime.strptime(fecha_hora_str, '%Y-%m-%dT%H:%M')
            # Por defecto asumimos una duración estándar de 45 minutos
            from datetime import timedelta
            fecha_hora_fin = fecha_hora_inicio + timedelta(minutes=45)

            nueva_cita = CitaUni(
                id_cliente=cliente_id,
                id_paciente=id_paciente,
                id_especialista=id_especialista,
                fecha_hora_inicio=fecha_hora_inicio,
                fecha_hora_fin=fecha_hora_fin,
                estado_cita='Programada',
                motivo_reserva=motivo
            )
            db.session.add(nueva_cita)
            db.session.commit()
            flash('Cita programada con éxito.', 'success')
        except Exception as e:
            flash(f'Error al agendar cita: {str(e)}', 'danger')

        return redirect(url_for('citas'))

    rol = session.get('user_role')
    if rol == 'Superadmin':
        lista_citas = CitaUni.query.order_by(CitaUni.fecha_hora_inicio.desc()).all()
    else:
        lista_citas = CitaUni.query.filter_by(id_cliente=cliente_id).order_by(CitaUni.fecha_hora_inicio.desc()).all()

    pacientes = PacienteUni.query.filter_by(id_cliente=cliente_id).all()
    especialistas = EspecialistaUni.query.filter_by(id_cliente=cliente_id).all()

    return render_template('citas.html', citas=lista_citas, pacientes=pacientes, especialistas=especialistas)

# --- Módulo de Sesiones de Evolución (psi_sesiones_evolucion) ---
@app.route('/citas/<int:id_cita>/atender', methods=['POST'])
@login_required
@role_required('Superadmin', 'Director', 'Administrador', 'Especialista')
def atender_cita(id_cita):
    cita = CitaUni.query.get_or_404(id_cita)
    evolucion = request.form.get('evolucion_clinica')
    observaciones = request.form.get('observaciones_conductuales')

    historia = HistoriaClinica.query.filter_by(id_paciente=cita.id_paciente).first()
    if not historia:
        flash('El paciente no tiene una historia clínica aperturada. Por favor aperture la historia primero.', 'warning')
        return redirect(url_for('crear_historia'))

    nueva_sesion = SesionEvolucion(
        id_historia=historia.id_historia,
        fecha_sesion=get_peru_time(),
        evolucion_clinica=evolucion,
        observaciones_conductuales=observaciones
    )
    db.session.add(nueva_sesion)
    
    cita.estado_cita = 'Completada'
    db.session.commit()

    flash(f'Cita #{cita.id_cita} completada y nota de evolución registrada exitosamente.', 'success')
    return redirect(url_for('ver_historia', id_historia=historia.id_historia))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
