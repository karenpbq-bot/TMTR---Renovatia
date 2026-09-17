from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, CitaUni, PacienteUni, EspecialistaUni, get_peru_time
from datetime import datetime, timedelta
from routes_auth import login_required, role_required

agenda_bp = Blueprint('agenda', __name__)

@agenda_bp.route('/citas', methods=['GET', 'POST'])
@login_required
def gestionar_citas():
    """Gestiona el listado y la creación de citas filtradas por la organización del usuario"""
    cliente_id = session.get('id_cliente')
    rol = session.get('user_role')
    
    if request.method == 'POST':
        id_paciente = request.form.get('id_paciente')
        id_especialista = request.form.get('id_especialista')
        fecha_hora_str = request.form.get('fecha_hora_inicio')
        motivo = request.form.get('motivo_reserva', '')

        try:
            # Parsear la fecha y hora enviada desde el formulario de la agenda
            fecha_hora_inicio = datetime.strptime(fecha_hora_str, '%Y-%m-%dT%H:%M')
            fecha_hora_fin = fecha_hora_inicio + timedelta(minutes=45) # Estándar de sesión clínica

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

        return redirect(url_for('agenda.gestionar_citas'))

    # Filtrado Multi-Tenant para el listado de citas
    if rol == 'Superadmin':
        lista_citas = CitaUni.query.order_by(CitaUni.fecha_hora_inicio.desc()).all()
    elif rol == 'Especialista':
        # Si es especialista, opcionalmente puede ver solo sus citas asignadas
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
    """Permite actualizar el estado de una cita (Programada, Cancelada, etc.)"""
    cita = CitaUni.query.get_or_404(id_cita)
    nuevo_estado = request.form.get('estado_cita')
    
    if nuevo_estado in ['Programada', 'Completada', 'Cancelada', 'No asistió']:
        cita.estado_cita = nuevo_estado
        db.session.commit()
        flash(f'El estado de la cita #{cita.id_cita} ha sido actualizado a: {nuevo_estado}', 'success')
    else:
        flash('Estado no válido.', 'warning')
        
    return redirect(url_for('agenda.gestionar_citas'))
