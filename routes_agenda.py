from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, CitaUni, PacienteUni, EspecialistaUni, ReprogramacionUni, DisponibilidadUni, get_peru_time
from datetime import datetime, timedelta
from routes_auth import login_required, role_required

agenda_bp = Blueprint('agenda', __name__)

@agenda_bp.route('/citas', methods=['GET', 'POST'])
@login_required
def gestionar_citas():
    """Gestiona el listado y la creación de citas filtradas por la organización del usuario con validación de solapes"""
    cliente_id = session.get('id_cliente')
    rol = session.get('user_role')
    
    if request.method == 'POST':
        id_paciente = request.form.get('id_paciente')
        id_especialista = request.form.get('id_especialista')
        fecha_hora_str = request.form.get('fecha_hora_inicio')
        motivo = request.form.get('motivo_reserva', '')

        try:
            # Parsear la fecha y hora enviada desde el formulario
            fecha_hora_inicio = datetime.strptime(fecha_hora_str, '%Y-%m-%dT%H:%M')
            fecha_hora_fin = fecha_hora_inicio + timedelta(minutes=45) # Estándar de sesión clínica

            # VALIDACIÓN DE SOLAPES: Verificar si el especialista ya tiene una cita activa en ese rango
            solapada = CitaUni.query.filter(
                CitaUni.id_especialista == int(id_especialista),
                CitaUni.estado_cita != 'Cancelada',
                CitaUni.fecha_hora_inicio < fecha_hora_fin,
                CitaUni.fecha_hora_fin > fecha_hora_inicio
            ).first()

            if solapada:
                flash('⚠️ Conflicto de horario: El especialista ya cuenta con una cita activa en este rango de tiempo.', 'danger')
                return redirect(url_for('agenda.gestionar_citas'))

            nueva_cita = CitaUni(
                id_cliente=cliente_id,
                id_paciente=int(id_paciente),
                id_especialista=int(id_especialista),
                fecha_hora_inicio=fecha_hora_inicio,
                fecha_hora_fin=fecha_hora_fin,
                estado_cita='Programada',
                motivo_reserva=motivo
            )
            db.session.add(nueva_cita)
            db.session.commit()
            flash('Cita programada con éxito.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al agendar cita: {str(e)}', 'danger')

        return redirect(url_for('agenda.gestionar_citas'))

    # Filtrado Multi-Tenant para el listado de citas
    if rol == 'Superadmin':
        lista_citas = CitaUni.query.order_by(CitaUni.fecha_hora_inicio.desc()).all()
    elif rol == 'Especialista':
        id_especialista = session.get('user_id')
        lista_citas = CitaUni.query.filter_by(id_cliente=cliente_id, id_especialista=id_especialista).order_by(CitaUni.fecha_hora_inicio.desc()).all()
    else:
        lista_citas = CitaUni.query.filter_by(id_cliente=cliente_id).order_by(CitaUni.fecha_hora_inicio.desc()).all()

    pacientes = PacienteUni.query.filter_by(id_cliente=cliente_id).all()
    especialistas = EspecialistaUni.query.filter_by(id_cliente=cliente_id).all()

    return render_template('citas.html', citas=lista_citas, pacientes=pacientes, especialistas=especialistas)


@agenda_bp.route('/citas/<int:id_cita>/estado', methods=['POST'])
@login_required
@role_required('Superadmin', 'Director', 'Administrador', 'Recepcionista', 'Especialista')
def cambiar_estado_cita(id_cita):
    """Permite actualizar el estado de una cita (Programada, Cancelada, etc.) liberando horario si se cancela"""
    cita = CitaUni.query.get_or_404(id_cita)
    nuevo_estado = request.form.get('estado_cita')
    
    if nuevo_estado in ['Programada', 'Completada', 'Cancelada', 'No asistió']:
        cita.estado_cita = nuevo_estado
        db.session.commit()
        flash(f'El estado de la cita #{cita.id_cita} ha sido actualizado a: {nuevo_estado}', 'success')
    else:
        flash('Estado no válido.', 'warning')
        
    return redirect(url_for('agenda.gestionar_citas'))


@agenda_bp.route('/citas/<int:id_cita>/reprogramar', methods=['POST'])
@login_required
@role_required('Superadmin', 'Director', 'Administrador', 'Recepcionista', 'Especialista')
def reprogramar_cita(id_cita):
    """Permite cambiar la fecha/hora de una cita existente registrando auditoría en uni_reprogramaciones"""
    cita = CitaUni.query.get_or_404(id_cita)
    nueva_fecha_str = request.form.get('nueva_fecha_hora')
    motivo = request.form.get('motivo_reprogramacion', 'Reprogramación de cita')

    try:
        nueva_inicio = datetime.strptime(nueva_fecha_str, '%Y-%m-%dT%H:%M')
        duracion = cita.fecha_hora_fin - cita.fecha_hora_inicio
        nueva_fin = nueva_inicio + duracion

        # Validar solapes excluyendo la propia cita actual
        solapada = CitaUni.query.filter(
            CitaUni.id_especialista == cita.id_especialista,
            CitaUni.id_cita != cita.id_cita,
            CitaUni.estado_cita != 'Cancelada',
            CitaUni.fecha_hora_inicio < nueva_fin,
            CitaUni.fecha_hora_fin > nueva_inicio
        ).first()

        if solapada:
            flash('⚠️ No se puede reprogramar: El nuevo horario presenta un cruce con otra cita activa.', 'danger')
            return redirect(url_for('agenda.gestionar_citas'))

        # Registrar auditoría en la tabla uni_reprogramaciones
        reprogramacion = ReprogramacionUni(
            id_cita=cita.id_cita,
            id_cliente=cita.id_cliente,
            fecha_hora_anterior=cita.fecha_hora_inicio,
            fecha_hora_nueva=nueva_inicio,
            motivo_reprogramacion=motivo,
            realizado_por=session.get('user_name', session.get('user_role', 'Sistema'))
        )

        # Actualizar tiempos de la cita
        cita.fecha_hora_inicio = nueva_inicio
        cita.fecha_hora_fin = nueva_fin
        cita.estado_cita = 'Programada'

        db.session.add(reprogramacion)
        db.session.commit()
        flash(f'Cita #{cita.id_cita} reprogramada con éxito.', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Error al reprogramar la cita: {str(e)}', 'danger')

    return redirect(url_for('agenda.gestionar_citas'))


# ===========================================================================
# GESTIÓN DE DISPONIBILIDAD HORARIA DEL ESPECIALISTA
# ===========================================================================

@agenda_bp.route('/disponibilidad', methods=['GET', 'POST'])
@login_required
def gestionar_disponibilidad():
    """Permite configurar los bloques de disponibilidad horaria por especialista"""
    cliente_id = session.get('id_cliente')
    rol = session.get('user_role')
    user_id = session.get('user_id')

    if rol == 'Especialista':
        especialista_id = user_id
    else:
        especialista_id = request.args.get('id_especialista', type=int)

    if request.method == 'POST':
        if not especialista_id:
            flash('Debe seleccionar un especialista.', 'warning')
            return redirect(url_for('agenda.gestionar_disponibilidad'))

        dia_semana = request.form.get('dia_semana')
        hora_inicio = request.form.get('hora_inicio')
        hora_fin = request.form.get('hora_fin')
        intervalo = request.form.get('intervalo_minutos', 45)

        try:
            dispo_existente = DisponibilidadUni.query.filter_by(
                id_especialista=especialista_id,
                dia_semana=dia_semana
            ).first()

            if dispo_existente:
                dispo_existente.hora_inicio = hora_inicio
                dispo_existente.hora_fin = hora_fin
                dispo_existente.intervalo_minutos = int(intervalo)
                dispo_existente.estado = True
            else:
                nueva_dispo = DisponibilidadUni(
                    id_cliente=cliente_id,
                    id_especialista=especialista_id,
                    dia_semana=dia_semana,
                    hora_inicio=hora_inicio,
                    hora_fin=hora_fin,
                    intervalo_minutos=int(intervalo),
                    estado=True
                )
                db.session.add(nueva_dispo)

            db.session.commit()
            flash('¡Horario de disponibilidad guardado con éxito!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al guardar disponibilidad: {str(e)}', 'danger')

        return redirect(url_for('agenda.gestionar_disponibilidad', id_especialista=especialista_id))

    especialistas = EspecialistaUni.query.filter_by(id_cliente=cliente_id).all()
    disponibilidades = []
    if especialista_id:
        disponibilidades = DisponibilidadUni.query.filter_by(id_especialista=especialista_id).all()

    return render_template(
        'disponibilidad.html',
        especialistas=especialistas,
        disponibilidades=disponibilidades,
        especialista_activo=especialista_id
    )
