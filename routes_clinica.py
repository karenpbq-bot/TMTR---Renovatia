from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, get_peru_time, HistoriaClinicaPsi, SeguimientoPsi, PacienteUni, CitaUni, EspecialistaUni
from routes_auth import login_required, role_required
from datetime import datetime

clinica_bp = Blueprint('clinica', __name__)

@clinica_bp.route('/historias')
@login_required
@role_required('Superadmin', 'Director', 'Administrador', 'Especialista', 'Recepcionista')
def listar_historias():
    """Lista las historias clínicas filtrando según el rol del usuario"""
    cliente_id = session.get('id_cliente')
    rol = session.get('user_role')
    user_id = session.get('user_id')

    if rol == 'Superadmin':
        lista_historias = HistoriaClinicaPsi.query.all()
    elif rol == 'Especialista':
        # CORRECCIÓN: Buscar el id_especialista vinculado a este id_usuario
        especialista = EspecialistaUni.query.filter_by(id_usuario=user_id).first()
        
        if especialista:
            # Ahora filtramos por especialista.id_especialista, NO por user_id
            subquery_pacientes_esp = db.session.query(CitaUni.id_paciente).filter(CitaUni.id_especialista == especialista.id_especialista).subquery()
            lista_historias = HistoriaClinicaPsi.query.join(PacienteUni).filter(
                PacienteUni.id_cliente == cliente_id,
                HistoriaClinicaPsi.id_paciente.in_(subquery_pacientes_esp)
            ).all()
        else:
            lista_historias = [] # Si por algún error no tiene perfil de especialista, no ve nada
    else:
        # Administradores, Directores y Recepcionistas ven todas las de la empresa cliente
        lista_historias = HistoriaClinicaPsi.query.join(PacienteUni).filter(PacienteUni.id_cliente == cliente_id).all()

    return render_template('historias.html', historias=lista_historias)


@clinica_bp.route('/historias/nueva', methods=['GET', 'POST'])
@login_required
@role_required('Superadmin', 'Director', 'Administrador', 'Especialista')
def crear_historia():
    """Apertura una nueva historia clínica vinculada a un paciente de la organización"""
    cliente_id = session.get('id_cliente')

    if request.method == 'POST':
        id_paciente = request.form.get('id_paciente')
        
        historia_existente = HistoriaClinicaPsi.query.filter_by(id_paciente=id_paciente).first()
        if historia_existente:
            flash('Este paciente ya tiene una historia clínica aperturada.', 'warning')
            return redirect(url_for('clinica.ver_historia', id_historia=historia_existente.id_historia))

        # Estructurar los datos para los campos JSONB
        json_examen_mental = {"descripcion": request.form.get('examen_mental_estado_actual')}
        json_diagnostico = {
            "codigo": request.form.get('codigo_diagnostico'),
            "descripcion": request.form.get('descripcion_diagnostico')
        }

        nueva_historia = HistoriaClinicaPsi(
            id_cliente=cliente_id,
            id_paciente=id_paciente,
            nro_historia=request.form.get('nro_historia'),
            grado_instruccion=request.form.get('grado_instruccion'),
            ocupacion_actual=request.form.get('ocupacion_actual'),
            estado_civil=request.form.get('estado_civil'),
            religion=request.form.get('religion'),
            nombre_acompanante=request.form.get('nombre_acompanante'),
            parentesco_acompanante=request.form.get('parentesco_acompanante'),
            
            motivo_consulta=request.form.get('motivo_consulta'),
            tiempo_enfermedad=request.form.get('tiempo_enfermedad'),
            sintomatologia_principal=request.form.get('sintomatologia_principal'),
            
            antecedentes_personales_psicologicos=request.form.get('antecedentes_personales_psicologicos'),
            antecedentes_medicos_relevantes=request.form.get('antecedentes_medicos_relevantes'),
            antecedentes_familiares=request.form.get('antecedentes_familiares'),
            historia_desarrollo_social=request.form.get('historia_desarrollo_social'),
            
            examen_mental_estado_actual=json_examen_mental,
            diagnostico_cie10_dsm5=json_diagnostico,
            tipo_diagnostico=request.form.get('tipo_diagnostico'),
            
            objetivos_terapeuticos=request.form.get('objetivos_terapeuticos'),
            tipo_intervencion=request.form.get('tipo_intervencion'),
            pronostico=request.form.get('pronostico')
        )
        db.session.add(nueva_historia)
        db.session.commit()
        flash('Ficha e Historia Clínica creada exitosamente.', 'success')
        return redirect(url_for('clinica.ver_historia', id_historia=nueva_historia.id_historia))

    pacientes_sin_historia = PacienteUni.query.filter_by(id_cliente=cliente_id).outerjoin(HistoriaClinicaPsi).filter(HistoriaClinicaPsi.id_historia == None).all()
    return render_template('historia_nueva.html', pacientes_sin_historia=pacientes_sin_historia)


@clinica_bp.route('/historias/<int:id_historia>')
@login_required
def ver_historia(id_historia):
    """Muestra el detalle completo de la historia clínica y sus notas de evolución"""
    historia = HistoriaClinicaPsi.query.get_or_404(id_historia)
    return render_template('historia_detalle.html', historia=historia)

@clinica_bp.route('/historias/<int:id_historia>/editar', methods=['POST'])
@login_required
@role_required('Superadmin', 'Director', 'Administrador', 'Especialista')
def editar_historia(id_historia):
    """Permite actualizar los datos demográficos y antecedentes de la historia clínica."""
    historia = HistoriaClinicaPsi.query.get_or_404(id_historia)
    
    # 1. Actualizar datos básicos
    historia.nro_historia = request.form.get('nro_historia')
    historia.grado_instruccion = request.form.get('grado_instruccion')
    historia.ocupacion_actual = request.form.get('ocupacion_actual')
    historia.estado_civil = request.form.get('estado_civil')
    historia.religion = request.form.get('religion')
    historia.nombre_acompanante = request.form.get('nombre_acompanante')
    historia.parentesco_acompanante = request.form.get('parentesco_acompanante')
    
    # 2. Actualizar antecedentes y motivo
    historia.motivo_consulta = request.form.get('motivo_consulta')
    historia.tiempo_enfermedad = request.form.get('tiempo_enfermedad')
    historia.sintomatologia_principal = request.form.get('sintomatologia_principal')
    historia.historia_desarrollo_social = request.form.get('historia_desarrollo_social')
    historia.antecedentes_medicos_relevantes = request.form.get('antecedentes_medicos_relevantes')
    historia.antecedentes_personales_psicologicos = request.form.get('antecedentes_personales_psicologicos')
    historia.antecedentes_familiares = request.form.get('antecedentes_familiares')
    
    # 3. Estructurar y actualizar los campos JSON y plan (Diagnóstico)
    examen_mental_desc = request.form.get('examen_mental_estado_actual')
    if examen_mental_desc is not None:
        historia.examen_mental_estado_actual = {"descripcion": examen_mental_desc}

    codigo_diag = request.form.get('codigo_diagnostico')
    desc_diag = request.form.get('descripcion_diagnostico')
    
    if codigo_diag or desc_diag:
        json_diagnostico = {
            "codigo": codigo_diag,
            "descripcion": desc_diag
        }
        historia.diagnostico_cie10_dsm5 = json_diagnostico

    historia.tipo_diagnostico = request.form.get('tipo_diagnostico')
    historia.objetivos_terapeuticos = request.form.get('objetivos_terapeuticos')
    historia.tipo_intervencion = request.form.get('tipo_intervencion')
    historia.pronostico = request.form.get('pronostico')

    # Guardar en base de datos
    db.session.commit()
    flash('La Historia Clínica ha sido actualizada exitosamente.', 'success')
    
    return redirect(url_for('clinica.ver_historia', id_historia=historia.id_historia))

@clinica_bp.route('/historias/<int:id_historia>/sesion/nueva', methods=['POST'])
@login_required
@role_required('Superadmin', 'Director', 'Administrador', 'Especialista')
def guardar_sesion_desde_historia(id_historia):
    """Guarda una nueva sesión desde la vista de detalle de la historia y redirige allí mismo."""
    user_id = session.get('user_id')
    evolucion = request.form.get('evolucion_clinica')
    observaciones = request.form.get('observaciones_conductuales')

    # BUSCAMOS EL ID REAL DEL ESPECIALISTA
    especialista = EspecialistaUni.query.filter_by(id_usuario=user_id).first()

    if not evolucion:
        flash('Debe redactar la evolución clínica.', 'warning')
        return redirect(url_for('clinica.ver_historia', id_historia=id_historia))
        
    if not especialista:
        flash('Error: Su perfil no está configurado como especialista.', 'danger')
        return redirect(url_for('clinica.ver_historia', id_historia=id_historia))

    nueva_sesion = SeguimientoPsi(
        id_historia=id_historia,
        id_especialista=especialista.id_especialista, # <--- ID CORRECTO
        nota_subjetiva=evolucion,      
        nota_objetiva=observaciones    
    )
    db.session.add(nueva_sesion)
    db.session.commit()
    
    flash('Sesión de evolución registrada exitosamente.', 'success')
    return redirect(url_for('clinica.ver_historia', id_historia=id_historia))

@clinica_bp.route('/sesiones', methods=['GET', 'POST'])
@login_required
@role_required('Superadmin', 'Director', 'Administrador', 'Especialista')
def listar_sesiones():
    """Muestra el listado de sesiones de evolución y registra nuevas notas"""
    cliente_id = session.get('id_cliente')
    rol = session.get('user_role')
    user_id = session.get('user_id')
    
    # BUSCAMOS EL ID REAL DEL ESPECIALISTA (si es que el usuario tiene perfil de especialista)
    especialista = EspecialistaUni.query.filter_by(id_usuario=user_id).first()

    # --- 1. Lógica POST (Guardar Evolución) ---
    if request.method == 'POST':
        id_historia = request.form.get('id_historia')
        evolucion = request.form.get('evolucion_clinica')
        observaciones = request.form.get('observaciones_conductuales')

        if not id_historia or not evolucion:
            flash('Debe seleccionar una historia y redactar la evolución.', 'warning')
            return redirect(url_for('clinica.listar_sesiones'))
            
        if not especialista:
            flash('Solo los usuarios con perfil de Especialista pueden firmar sesiones.', 'danger')
            return redirect(url_for('clinica.listar_sesiones'))

        nueva_sesion = SeguimientoPsi(
            id_historia=id_historia,
            id_especialista=especialista.id_especialista, # <--- AQUÍ SE USA EL ID CORRECTO
            nota_subjetiva=evolucion,
            nota_objetiva=observaciones
        )
        db.session.add(nueva_sesion)
        db.session.commit()
        flash('Sesión de evolución registrada exitosamente.', 'success')
        return redirect(url_for('clinica.listar_sesiones'))
    
    # --- 2. Lógica GET (Listar según el rol) ---
    if rol == 'Superadmin':
        lista_sesiones = SeguimientoPsi.query.all()
        lista_historias = HistoriaClinicaPsi.query.all()
    elif rol == 'Especialista' and especialista:
        # AQUÍ SE FILTRA USANDO EL ID CORRECTO
        subquery_pacientes_esp = db.session.query(CitaUni.id_paciente).filter(CitaUni.id_especialista == especialista.id_especialista).subquery()
        lista_sesiones = SeguimientoPsi.query.join(HistoriaClinicaPsi).join(PacienteUni).filter(
            PacienteUni.id_cliente == cliente_id
        ).all()
        lista_historias = HistoriaClinicaPsi.query.join(PacienteUni).filter(
            PacienteUni.id_cliente == cliente_id,
            HistoriaClinicaPsi.id_paciente.in_(subquery_pacientes_esp)
        ).all()
    else:
        # Administradores y Directores
        lista_sesiones = SeguimientoPsi.query.join(HistoriaClinicaPsi).join(PacienteUni).filter(PacienteUni.id_cliente == cliente_id).all()
        lista_historias = HistoriaClinicaPsi.query.join(PacienteUni).filter(PacienteUni.id_cliente == cliente_id).all()

    return render_template('sesiones.html', sesiones=lista_sesiones, historias=lista_historias)

@clinica_bp.route('/citas/<int:id_cita>/atender', methods=['POST'])
@login_required
@role_required('Superadmin', 'Director', 'Administrador', 'Especialista')
def atender_cita(id_cita):
    """Completa una cita psicológica y registra la evolución en formato S.O.A.P."""
    cita = CitaUni.query.get_or_404(id_cita)
    historia = HistoriaClinicaPsi.query.filter_by(id_paciente=cita.id_paciente).first()
    
    if not historia:
        flash('El paciente no tiene una historia clínica aperturada. Por favor aperture la historia primero.', 'warning')
        return redirect(url_for('clinica.crear_historia'))

    # Buscamos al especialista real
    especialista = EspecialistaUni.query.filter_by(id_usuario=session.get('user_id')).first()
    id_esp_real = especialista.id_especialista if especialista else None

    nueva_sesion = SeguimientoPsi(
        id_historia=historia.id_historia,
        id_cita=cita.id_cita,
        id_especialista=id_esp_real, # <--- AHORA SÍ GUARDARÁ EL ID CORRECTO
        nota_subjetiva=request.form.get('nota_subjetiva'),
        nota_objetiva=request.form.get('nota_objetiva'),
        apreciacion_clinica=request.form.get('apreciacion_clinica'),
        plan_tareas=request.form.get('plan_tareas'),
        pruebas_aplicadas=request.form.get('pruebas_aplicadas'),
        evaluacion_riesgo=request.form.get('evaluacion_riesgo')
    )
    db.session.add(nueva_sesion)
    
    cita.estado_cita = 'Completada'
    db.session.commit()

    flash(f'Cita #{cita.id_cita} completada y nota S.O.A.P. registrada exitosamente.', 'success')
    return redirect(url_for('clinica.ver_historia', id_historia=historia.id_historia))
