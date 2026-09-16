from functools import wraps
from datetime import datetime, date
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from config import Config
from models import (
    db, get_peru_time, ClienteEmpresa, UsuarioUni, EspecialistaUni, 
    PacienteUni, DisponibilidadUni, CitaUni, ReprogramacionUni, 
    HistoriaClinica, SesionEvolucion
)

# 1. ÚNICA CREACIÓN DE LA INSTANCIA DE APP
app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

# --- REGISTRO DE BLUEPRINTS (MÓDULOS MODULARES) ---
from routes_clientes import clientes_bp
from routes_usuarios import usuarios_bp

app.register_blueprint(clientes_bp)
app.register_blueprint(usuarios_bp)

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

# --- Context Processor blindado para evitar errores 500 ---
@app.context_processor
def inject_globals():
    cliente_nombre = "Psicolapp / Tamtara"
    cliente_id = session.get('id_cliente')
    
    try:
        if cliente_id:
            from models import ClienteEmpresa
            cliente_obj = ClienteEmpresa.query.get(cliente_id)
            if cliente_obj:
                cliente_nombre = cliente_obj.nombre_marca
        elif session.get('user_role') == 'Superadmin':
            cliente_nombre = "TAMTARA (Superadmin)"
    except Exception as e:
        print(f"Error en context_processor: {e}")

    return {
        'current_user_name': session.get('user_name'),
        'current_user_role': session.get('user_role'),
        'current_user_id': session.get('user_id'),
        'current_cliente_id': cliente_id,
        'current_cliente_nombre': cliente_nombre
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

# --- Módulo de Sesiones de Evolución ---
@app.route('/sesiones')
@login_required
@role_required('Superadmin', 'Director', 'Administrador', 'Especialista')
def sesiones():
    cliente_id = session.get('id_cliente')
    rol = session.get('user_role')
    
    if rol == 'Superadmin':
        lista_sesiones = SesionEvolucion.query.all()
    else:
        lista_sesiones = SesionEvolucion.query.join(HistoriaClinica).join(PacienteUni).filter(PacienteUni.id_cliente == cliente_id).all()

    return render_template('sesiones.html', sesiones=lista_sesiones)

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
