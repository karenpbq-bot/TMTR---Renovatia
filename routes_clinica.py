from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, get_peru_time, HistoriaClinica, SesionEvolucion, PacienteUni, CitaUni
from routes_auth import login_required, role_required
from datetime import datetime

clinica_bp = Blueprint('clinica', __name__)

@clinica_bp.route('/historias')
@login_required
@role_required('Superadmin', 'Director', 'Administrador', 'Especialista', 'Recepcionista')
def listar_historias():
    """Lista las historias clínicas aplicando el aislamiento multi-tenant"""
    cliente_id = session.get('id_cliente')
    rol = session.get('user_role')

    if rol == 'Superadmin':
        lista_historias = HistoriaClinica.query.all()
    else:
        lista_historias = HistoriaClinica.query.join(PacienteUni).filter(PacienteUni.id_cliente == cliente_id).all()

    return render_template('historias.html', historias=lista_historias)


@clinica_bp.route('/historias/nueva', methods=['GET', 'POST'])
@login_required
@role_required('Superadmin', 'Director', 'Administrador', 'Especialista')
def crear_historia():
    """Apertura una nueva historia clínica vinculada a un paciente de la organización"""
    cliente_id = session.get('id_cliente')

    if request.method == 'POST':
        id_paciente = request.form.get('id_paciente')
        
        historia_existente = HistoriaClinica.query.filter_by(id_paciente=id_paciente).first()
        if historia_existente:
            flash('Este paciente ya tiene una historia clínica aperturada.', 'warning')
            return redirect(url_for('clinica.ver_historia', id_historia=historia_existente.id_historia))

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
        return redirect(url_for('clinica.ver_historia', id_historia=nueva_historia.id_historia))

    pacientes_sin_historia = PacienteUni.query.filter_by(id_cliente=cliente_id).outerjoin(HistoriaClinica).filter(HistoriaClinica.id_historia == None).all()
    return render_template('historia_nueva.html', pacientes_sin_historia=pacientes_sin_historia)


@clinica_bp.route('/historias/<int:id_historia>')
@login_required
def ver_historia(id_historia):
    """Muestra el detalle completo de la historia clínica y sus notas de evolución"""
    historia = HistoriaClinica.query.get_or_404(id_historia)
    return render_template('historia_detalle.html', historia=historia)


@clinica_bp.route('/sesiones')
@login_required
@role_required('Superadmin', 'Director', 'Administrador', 'Especialista')
def listar_sesiones():
    """Muestra el listado de sesiones de evolución registradas"""
    cliente_id = session.get('id_cliente')
    rol = session.get('user_role')
    
    if rol == 'Superadmin':
        lista_sesiones = SesionEvolucion.query.all()
    else:
        lista_sesiones = SesionEvolucion.query.join(HistoriaClinica).join(PacienteUni).filter(PacienteUni.id_cliente == cliente_id).all()

    return render_template('sesiones.html', sesiones=lista_sesiones)


@clinica_bp.route('/citas/<int:id_cita>/atender', methods=['POST'])
@login_required
@role_required('Superadmin', 'Director', 'Administrador', 'Especialista')
def atender_cita(id_cita):
    """Completa una cita médica/psicológica y registra su nota de sesión evolutiva"""
    cita = CitaUni.query.get_or_404(id_cita)
    evolucion = request.form.get('evolucion_clinica')
    observaciones = request.form.get('observaciones_conductuales')

    historia = HistoriaClinica.query.filter_by(id_paciente=cita.id_paciente).first()
    if not historia:
        flash('El paciente no tiene una historia clínica aperturada. Por favor aperture la historia primero.', 'warning')
        return redirect(url_for('clinica.crear_historia'))

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
    return redirect(url_for('clinica.ver_historia', id_historia=historia.id_historia))
