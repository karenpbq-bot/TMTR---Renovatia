from functools import wraps
from datetime import datetime, date
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from config import Config
from models import db, Usuario, Cita, HistoriaClinica, SesionEvolucion, ROLES_PERMITIDOS, ESTADOS_CITA

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

# --- CREACIÓN AUTOMÁTICA DEL ADMINISTRADOR PERSONAL ---
with app.app_context():
    db.create_all()
    # Forzamos tu correo personal como el administrador principal del sistema
    admin_email = "kbarrientosq.2604@gmail.com"
    admin_user = Usuario.query.filter_by(correo=admin_email).first()
    
    if not admin_user:
        nuevo_admin = Usuario(
            nombres_apellidos="Karen Paola Barrientos",
            correo=admin_email,
            rol="Administrador"
        )
        nuevo_admin.set_password("admin123")
        db.session.add(nuevo_admin)
        db.session.commit()
        print("¡Cuenta Administrador personal creada exitosamente!")
    else:
        # Asegurar que si ya existía, tenga la clave correcta y rol de Admin
        admin_user.rol = "Administrador"
        admin_user.set_password("admin123")
        db.session.commit()
        print("¡Cuenta Administrador verificada y actualizada!")

# --- CREACIÓN AUTOMÁTICA DEL ADMINISTRADOR AL ARRANCAR ---
with app.app_context():
    db.create_all()
    admin_email = "kbarrientosq.2604@gmail.com"
    admin_user = Usuario.query.filter_by(correo=admin_email).first()
    if not admin_user:
        nuevo_admin = Usuario(
            nombres_apellidos="Karen Paola Barrientos",
            correo=admin_email,
            rol="Administrador"
        )
        nuevo_admin.set_password("admin123")
        db.session.add(nuevo_admin)
        db.session.commit()
        print("¡Cuenta Administrador creada exitosamente en la BD activa!")

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

# Context Processor para disponibilizar variables en todas las plantillas
@app.context_processor
def inject_globals():
    return {
        'roles_permitidos': ROLES_PERMITIDOS,
        'estados_cita': ESTADOS_CITA,
        'current_user_name': session.get('user_name'),
        'current_user_role': session.get('user_role'),
        'current_user_id': session.get('user_id')
    }

# --- 1. Sistema de Autenticación y Redirección por Roles ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form.get('correo', '').strip()
        password = request.form.get('password', '')

        usuario = Usuario.query.filter_by(correo=correo).first()
        if usuario and usuario.check_password(password):
            session['user_id'] = usuario.id_usuario
            session['user_name'] = usuario.nombres_apellidos
            session['user_role'] = usuario.rol
            session['user_email'] = usuario.correo
            
            flash(f'¡Bienvenido(a), {usuario.nombres_apellidos} ({usuario.rol})!', 'success')

            # Redirección personalizada según el rol del usuario
            if usuario.rol == 'Administrador':
                return redirect(url_for('dashboard'))
            elif usuario.rol == 'Recepcionista':
                return redirect(url_for('citas'))
            elif usuario.rol == 'Especialista':
                return redirect(url_for('historias'))
            elif usuario.rol == 'Cliente':
                return redirect(url_for('dashboard'))
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

# --- Dashboard Principal ---
@app.route('/')
@login_required
def dashboard():
    rol = session.get('user_role')
    user_id = session.get('user_id')

    # Métricas generales
    total_usuarios = Usuario.query.count() if rol in ['Administrador', 'Recepcionista'] else 0
    total_clientes = Usuario.query.filter_by(rol='Cliente').count()
    total_especialistas = Usuario.query.filter_by(rol='Especialista').count()
    
    # Citas según el rol autenticado
    if rol == 'Cliente':
        citas = Cita.query.filter_by(id_cliente=user_id).order_by(Cita.fecha_hora.asc()).all()
    elif rol == 'Especialista':
        citas = Cita.query.filter_by(id_especialista=user_id).order_by(Cita.fecha_hora.asc()).all()
    else:
        citas = Cita.query.order_by(Cita.fecha_hora.asc()).all()

    citas_programadas = sum(1 for c in citas if c.estado == 'Programada')
    citas_completadas = sum(1 for c in citas if c.estado == 'Completada')
    
    # Historias clínicas
    total_historias = HistoriaClinica.query.count()

    return render_template(
        'dashboard.html',
        citas=citas[:10],
        citas_programadas=citas_programadas,
        citas_completadas=citas_completadas,
        total_clientes=total_clientes,
        total_especialistas=total_especialistas,
        total_historias=total_historias,
        total_usuarios=total_usuarios
    )

# --- Módulo de Usuarios (Administrador / Recepcionista) ---
@app.route('/usuarios', methods=['GET', 'POST'])
@login_required
@role_required('Administrador', 'Recepcionista')
def usuarios():
    if request.method == 'POST':
        nombres = request.form.get('nombres_apellidos', '').strip()
        correo = request.form.get('correo', '').strip()
        password = request.form.get('password', '')
        rol = request.form.get('rol', 'Cliente')

        if rol not in ROLES_PERMITIDOS:
            flash('Rol no válido.', 'danger')
            return redirect(url_for('usuarios'))

        if Usuario.query.filter_by(correo=correo).first():
            flash('El correo ingresado ya se encuentra registrado.', 'warning')
        else:
            nuevo_usuario = Usuario(
                nombres_apellidos=nombres,
                correo=correo,
                rol=rol
            )
            nuevo_usuario.set_password(password if password else 'clave123')
            db.session.add(nuevo_usuario)
            db.session.commit()
            flash(f'Usuario "{nombres}" registrado con el rol "{rol}".', 'success')

        return redirect(url_for('usuarios'))

    lista_usuarios = Usuario.query.order_by(Usuario.id_usuario.desc()).all()
    return render_template('usuarios.html', usuarios=lista_usuarios)

# --- Editar Usuario ---
@app.route('/usuarios/editar/<int:id_usuario>', methods=['GET', 'POST'])
@login_required
@role_required('Administrador')
def editar_usuario(id_usuario):
    usuario = Usuario.query.get_or_404(id_usuario)
    
    if request.method == 'POST':
        nombres = request.form.get('nombres_apellidos', '').strip()
        correo = request.form.get('correo', '').strip()
        rol = request.form.get('rol')
        password = request.form.get('password', '').strip()

        if rol not in ROLES_PERMITIDOS:
            flash('Rol no válido.', 'danger')
            return redirect(url_for('editar_usuario', id_usuario=id_usuario))

        # Verificar si el correo ya pertenece a otro usuario
        usuario_existente = Usuario.query.filter_by(correo=correo).first()
        if usuario_existente and usuario_existente.id_usuario != usuario.id_usuario:
            flash('El correo ingresado ya está en uso por otro usuario.', 'warning')
            return redirect(url_for('editar_usuario', id_usuario=id_usuario))

        usuario.nombres_apellidos = nombres
        usuario.correo = correo
        usuario.rol = rol

        if password:
            usuario.set_password(password)

        db.session.commit()
        flash(f'Usuario "{nombres}" actualizado exitosamente.', 'success')
        return redirect(url_for('usuarios'))

    return render_template('usuario_editar.html', usuario=usuario)


# --- Eliminar Usuario ---
@app.route('/usuarios/eliminar/<int:id_usuario>', methods=['POST'])
@login_required
@role_required('Administrador')
def eliminar_usuario(id_usuario):
    usuario = Usuario.query.get_or_404(id_usuario)

    # Prevenir que un administrador elimine su propia cuenta activa por seguridad
    if usuario.id_usuario == session.get('user_id'):
        flash('No puedes eliminar tu propia cuenta de administrador.', 'danger')
        return redirect(url_for('usuarios'))

    nombre_borrado = usuario.nombres_apellidos
    db.session.delete(usuario)
    db.session.commit()
    
    flash(f'Usuario "{nombre_borrado}" eliminado correctamente.', 'info')
    return redirect(url_for('usuarios'))


# --- 2. Módulo de Historias Clínicas (Especialistas / Admisión) ---
@app.route('/historias')
@login_required
@role_required('Administrador', 'Especialista', 'Recepcionista', 'Cliente')
def historias():
    rol = session.get('user_role')
    user_id = session.get('user_id')

    if rol == 'Cliente':
        lista_historias = HistoriaClinica.query.filter_by(id_cliente=user_id).all()
    else:
        lista_historias = HistoriaClinica.query.order_by(HistoriaClinica.id_historia.desc()).all()

    return render_template('historias.html', historias=lista_historias)

@app.route('/historias/nueva', methods=['GET', 'POST'])
@login_required
@role_required('Administrador', 'Especialista')
def crear_historia():
    if request.method == 'POST':
        id_cliente = request.form.get('id_cliente')
        
        historia_existente = HistoriaClinica.query.filter_by(id_cliente=id_cliente).first()
        if historia_existente:
            flash('Este paciente ya tiene una historia clínica aperturada.', 'warning')
            return redirect(url_for('ver_historia', id_historia=historia_existente.id_historia))

        fecha_nac_str = request.form.get('fecha_nacimiento')
        fecha_nac = datetime.strptime(fecha_nac_str, '%Y-%m-%d').date() if fecha_nac_str else None

        nueva_historia = HistoriaClinica(
            id_cliente=id_cliente,
            fecha_nacimiento=fecha_nac,
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
        flash('Ficha e Historia Clínica de Admisión creada exitosamente.', 'success')
        return redirect(url_for('ver_historia', id_historia=nueva_historia.id_historia))

    clientes_sin_historia = Usuario.query.filter_by(rol='Cliente').outerjoin(HistoriaClinica).filter(HistoriaClinica.id_historia == None).all()
    return render_template('historia_nueva.html', clientes_sin_historia=clientes_sin_historia)

@app.route('/historias/<int:id_historia>')
@login_required
def ver_historia(id_historia):
    historia = HistoriaClinica.query.get_or_404(id_historia)
    if session.get('user_role') == 'Cliente' and historia.id_cliente != session.get('user_id'):
        flash('No tiene autorización para visualizar esta historia clínica.', 'danger')
        return redirect(url_for('dashboard'))

    return render_template('historia_detalle.html', historia=historia)

# --- 3. Módulo de Citas y Sesiones de Evolución ---
@app.route('/citas', methods=['GET', 'POST'])
@login_required
def citas():
    if request.method == 'POST':
        id_cliente = request.form.get('id_cliente')
        id_especialista = request.form.get('id_especialista')
        fecha_hora_str = request.form.get('fecha_hora')
        motivo = request.form.get('motivo', '')

        try:
            fecha_hora = datetime.strptime(fecha_hora_str, '%Y-%m-%dT%H:%M')
            nueva_cita = Cita(
                id_cliente=id_cliente,
                id_especialista=id_especialista,
                fecha_hora=fecha_hora,
                estado='Programada',
                motivo=motivo
            )
            db.session.add(nueva_cita)
            db.session.commit()
            flash('Cita programada con éxito.', 'success')
        except Exception as e:
            flash(f'Error al agendar cita: {str(e)}', 'danger')

        return redirect(url_for('citas'))

    rol = session.get('user_role')
    user_id = session.get('user_id')

    if rol == 'Cliente':
        lista_citas = Cita.query.filter_by(id_cliente=user_id).order_by(Cita.fecha_hora.desc()).all()
    elif rol == 'Especialista':
        lista_citas = Cita.query.filter_by(id_especialista=user_id).order_by(Cita.fecha_hora.desc()).all()
    else:
        lista_citas = Cita.query.order_by(Cita.fecha_hora.desc()).all()

    clientes = Usuario.query.filter_by(rol='Cliente').all()
    especialistas = Usuario.query.filter_by(rol='Especialista').all()

    return render_template('citas.html', citas=lista_citas, clientes=clientes, especialistas=especialistas)

@app.route('/citas/<int:id_cita>/estado', methods=['POST'])
@login_required
def cambiar_estado_cita(id_cita):
    cita = Cita.query.get_or_404(id_cita)
    nuevo_estado = request.form.get('estado')
    if nuevo_estado in ESTADOS_CITA:
        cita.estado = nuevo_estado
        db.session.commit()
        flash(f'Estado de la cita #{id_cita} actualizado a "{nuevo_estado}".', 'info')
    return redirect(url_for('citas'))

@app.route('/citas/<int:id_cita>/atender', methods=['POST'])
@login_required
@role_required('Administrador', 'Especialista')
def atender_cita(id_cita):
    cita = Cita.query.get_or_404(id_cita)
    evolucion = request.form.get('evolucion_clinica')
    observaciones = request.form.get('observaciones_conductuales')

    historia = HistoriaClinica.query.filter_by(id_cliente=cita.id_cliente).first()
    if not historia:
        flash('El cliente no tiene una historia clínica aperturada. Por favor aperture la historia primero.', 'warning')
        return redirect(url_for('crear_historia'))

    # Crear la sesión de evolución
    nueva_sesion = SesionEvolucion(
        id_historia=historia.id_historia,
        fecha_sesion=datetime.now(),
        evolucion_clinica=evolucion,
        observaciones_conductuales=observaciones
    )
    db.session.add(nueva_sesion)
    
    # Marcar la cita como completada
    cita.estado = 'Completada'
    db.session.commit()

    flash(f'Cita #{cita.id_cita} completada y nota de evolución registrada en la historia HC-{"%04d"|format(historia.id_historia)}.', 'success')
    return redirect(url_for('ver_historia', id_historia=historia.id_historia))

# --- Módulo independiente de Sesiones de Evolución ---
@app.route('/sesiones', methods=['GET', 'POST'])
@login_required
@role_required('Administrador', 'Especialista')
def sesiones():
    if request.method == 'POST':
        id_historia = request.form.get('id_historia')
        evolucion = request.form.get('evolucion_clinica')
        observaciones = request.form.get('observaciones_conductuales')

        if not id_historia or not evolucion:
            flash('Seleccione una Historia Clínica e ingrese la evolución.', 'danger')
            return redirect(url_for('sesiones'))

        nueva_sesion = SesionEvolucion(
            id_historia=id_historia,
            evolucion_clinica=evolucion,
            observaciones_conductuales=observaciones
        )
        db.session.add(nueva_sesion)
        db.session.commit()
        flash('Sesión de evolución guardada correctamente.', 'success')
        return redirect(url_for('ver_historia', id_historia=id_historia))

    historias = HistoriaClinica.query.all()
    lista_sesiones = SesionEvolucion.query.order_by(SesionEvolucion.fecha_sesion.desc()).all()
    return render_template('sesiones.html', sesiones=lista_sesiones, historias=historias)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
