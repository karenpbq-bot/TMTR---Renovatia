from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, CitaUni, PacienteUni, EspecialistaUni, UsuarioUni, ReprogramacionUni, DisponibilidadUni, get_peru_time, PermisoHistoriaPsi, HistoriaClinicaPsi
from datetime import datetime, timedelta
from routes_auth import login_required, role_required

agenda_bp = Blueprint('agenda', __name__)

@agenda_bp.route('/citas', methods=['GET', 'POST'])
@login_required
def gestionar_citas():
    """Gestiona el listado y la creación de citas unificando pacientes y especialistas de ambas tablas"""
    cliente_id = session.get('id_cliente')
    rol = session.get('user_role')
    user_id = session.get('user_id') # <-- Asegurarnos de capturar el user_id
    
    if request.method == 'POST':
        # BLINDAJE DE SEGURIDAD: Un paciente jamás puede crear citas por esta vía
        if rol == 'Paciente':
            flash('Acceso denegado: Los pacientes no tienen permisos para agendar citas desde este panel.', 'danger')
            return redirect(url_for('agenda.gestionar_citas'))

        id_paciente = request.form.get('id_paciente')
        id_especialista = request.form.get('id_especialista')
        
        # BLINDAJE ESTRUCTURAL: Si es Especialista, resolvemos su ID usando la relación directa
        if rol == 'Especialista':
            esp_query = EspecialistaUni.query.filter_by(
                id_cliente=cliente_id, 
                id_usuario=user_id
            ).first()
            
            if esp_query:
                id_especialista = esp_query.id_especialista
            else:
                flash('Error crítico: Su perfil clínico no está vinculado a su usuario de acceso.', 'danger')
                return redirect(url_for('agenda.gestionar_citas'))
        elif not id_especialista:
            id_especialista = request.form.get('id_especialista')

        fecha_hora_str = request.form.get('fecha_hora_inicio')
        motivo = request.form.get('motivo_reserva', '')

        try:
            duracion = request.form.get('duracion_minutos', type=int) or 50
            fecha_hora_inicio = datetime.strptime(fecha_hora_str, '%Y-%m-%dT%H:%M')
            fecha_hora_fin = fecha_hora_inicio + timedelta(minutes=duracion)

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
            
            # --- LÓGICA AUTOMÁTICA: OTORGAR ACCESO A LA HISTORIA ---
            historia = HistoriaClinicaPsi.query.filter_by(id_paciente=int(id_paciente)).first()
            if historia:
                permiso_existente = PermisoHistoriaPsi.query.filter_by(
                    id_historia=historia.id_historia,
                    id_especialista=int(id_especialista)
                ).first()

                if not permiso_existente:
                    nuevo_permiso = PermisoHistoriaPsi(
                        id_historia=historia.id_historia,
                        id_especialista=int(id_especialista),
                        estado_acceso=True,
                        origen_permiso=f"Generado automáticamente por Cita #{nueva_cita.id_cita}",
                        fecha_otorgamiento=get_peru_time()
                    )
                    db.session.add(nuevo_permiso)
                    db.session.commit()
            
            flash('Cita programada con éxito.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al agendar cita: {str(e)}', 'danger')

        return redirect(url_for('agenda.gestionar_citas'))

    # ==========================================
    # FILTRADO ESTRICTO DE CITAS SEGÚN EL ROL
    # ==========================================
    if rol == 'Superadmin':
        lista_citas = CitaUni.query.order_by(CitaUni.fecha_hora_inicio.desc()).all()
    elif rol == 'Especialista':
        esp_actual = EspecialistaUni.query.filter_by(id_cliente=cliente_id, id_usuario=user_id).first()
        id_real_esp = esp_actual.id_especialista if esp_actual else 0
        lista_citas = CitaUni.query.filter_by(id_cliente=cliente_id, id_especialista=id_real_esp).order_by(CitaUni.fecha_hora_inicio.desc()).all()
    elif rol == 'Paciente':
        # BLINDAJE DE PRIVACIDAD MULTI-TENANT: Buscamos al paciente por id_usuario y id_cliente
        paciente_obj = PacienteUni.query.filter_by(
            id_cliente=cliente_id, 
            id_usuario=user_id
        ).first()
        
        # Respaldo por correo si fuera necesario
        if not paciente_obj:
            paciente_obj = PacienteUni.query.filter_by(
                id_cliente=cliente_id, 
                email=session.get('user_correo')
            ).first()

        id_real_paciente = paciente_obj.id_paciente if paciente_obj else 0

        # El paciente SOLAMENTE ve las citas que le pertenecen en esta clínica
        lista_citas = CitaUni.query.filter_by(
            id_cliente=cliente_id, 
            id_paciente=id_real_paciente
        ).order_by(CitaUni.fecha_hora_inicio.desc()).all()
    else:
        # Administrador, Director, Recepcionista
        lista_citas = CitaUni.query.filter_by(id_cliente=cliente_id).order_by(CitaUni.fecha_hora_inicio.desc()).all()

    # Cargar listas auxiliares para formularios administrativos
    pacientes = PacienteUni.query.filter_by(id_cliente=cliente_id).all()
    
    if rol == 'Especialista':
        especialistas = EspecialistaUni.query.filter_by(id_cliente=cliente_id, id_usuario=user_id).all()
    else:
        especialistas = EspecialistaUni.query.filter_by(id_cliente=cliente_id).all()

    return render_template('citas.html', citas=lista_citas, pacientes=pacientes, especialistas=especialistas)


@agenda_bp.route('/citas/<int:id_cita>/estado', methods=['POST'])
@login_required
@role_required('Superadmin', 'Director', 'Administrador', 'Recepcionista')
def cambiar_estado_cita(id_cita):
    """Permite actualizar el estado de una cita. La cancelación y gestión recae exclusivamente en Recepción/Admin"""
    cita = CitaUni.query.get_or_404(id_cita)
    nuevo_estado = request.form.get('estado_cita')
    
    if nuevo_estado in ['Programada', 'Completada', 'Cancelada', 'No asistió']:
        cita.estado_cita = nuevo_estado
        db.session.commit()

        # --- LÓGICA AUTOMÁTICA: REVOCACIÓN DE ACCESO POR CANCELACIÓN ---
        if nuevo_estado == 'Cancelada':
            otras_citas = CitaUni.query.filter(
                CitaUni.id_paciente == cita.id_paciente,
                CitaUni.id_especialista == cita.id_especialista,
                CitaUni.id_cita != cita.id_cita,
                CitaUni.estado_cita.in_(['Programada', 'Completada', 'No asistió'])
            ).first()

            if not otras_citas:
                historia = HistoriaClinicaPsi.query.filter_by(id_paciente=cita.id_paciente).first()
                if historia:
                    permiso = PermisoHistoriaPsi.query.filter_by(
                        id_historia=historia.id_historia,
                        id_especialista=cita.id_especialista
                    ).first()
                    if permiso:
                        db.session.delete(permiso)
                        db.session.commit()

        flash(f'El estado de la cita #{cita.id_cita} ha sido actualizado a: {nuevo_estado}', 'success')
    else:
        flash('Estado no válido.', 'warning')
        
    return redirect(url_for('agenda.gestionar_citas'))


@agenda_bp.route('/citas/<int:id_cita>/reprogramar', methods=['POST'])
@login_required
@role_required('Superadmin', 'Director', 'Administrador', 'Recepcionista')
def reprogramar_cita(id_cita):
    """Permite al recepcionista reprogramar una cita: marca la anterior como Cancelada y Reprogramada y crea la nueva"""
    cita_antigua = CitaUni.query.get_or_404(id_cita)
    nueva_fecha_str = request.form.get('nueva_fecha_hora')
    motivo = request.form.get('motivo_reprogramacion', cita_antigua.motivo_reserva or 'Reprogramación de cita')

    try:
        nueva_inicio = datetime.strptime(nueva_fecha_str, '%Y-%m-%dT%H:%M')
        duracion = cita_antigua.fecha_hora_fin - cita_antigua.fecha_hora_inicio
        nueva_fin = nueva_inicio + duracion

        # Validar solapamiento u horario cruzado para el especialista
        solapada = CitaUni.query.filter(
            CitaUni.id_especialista == cita_antigua.id_especialista,
            CitaUni.estado_cita.in_(['Programada', 'Confirmada']),
            CitaUni.fecha_hora_inicio < nueva_fin,
            CitaUni.fecha_hora_fin > nueva_inicio
        ).first()

        if solapada:
            flash('⚠️ No se puede reprogramar: El especialista ya cuenta con una cita activa en este nuevo rango horario.', 'danger')
            return redirect(url_for('agenda.gestionar_citas'))

        # 1. Marcar la cita anterior como Cancelada y Reprogramada
        cita_antigua.estado_cita = 'Cancelada y Reprogramada'

        # 2. Registrar el evento en la tabla de trazabilidad/reprogramaciones
        reprogramacion = ReprogramacionUni(
            id_cita=cita_antigua.id_cita,
            id_cliente=cita_antigua.id_cliente,
            fecha_hora_anterior=cita_antigua.fecha_hora_inicio,
            fecha_hora_nueva=nueva_inicio,
            motivo_reprogramacion=motivo,
            realizado_por=session.get('user_name', session.get('user_role', 'Recepcionista'))
        )
        db.session.add(reprogramacion)

        # 3. Crear la NUEVA cita oficial
        nueva_cita = CitaUni(
            id_cliente=cita_antigua.id_cliente,
            id_paciente=cita_antigua.id_paciente,
            id_especialista=cita_antigua.id_especialista,
            fecha_hora_inicio=nueva_inicio,
            fecha_hora_fin=nueva_fin,
            estado_cita='Programada',
            motivo_reserva=motivo
        )
        db.session.add(nueva_cita)
        db.session.commit()

        flash(f'Cita #{cita_antigua.id_cita} marcada como Cancelada y Reprogramada. Nueva cita creada con éxito.', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Error al procesar la reprogramación: {str(e)}', 'danger')

    return redirect(url_for('agenda.gestionar_citas'))


@agenda_bp.route('/disponibilidad', methods=['GET', 'POST'])
@login_required
def gestionar_disponibilidad():
    """Gestiona la plantilla semanal por mes (T1-T4), copia del mes anterior y excepciones"""
    cliente_id = session.get('id_cliente')
    rol = session.get('user_role')
    user_id = session.get('user_id')

    if rol == 'Especialista':
        esp_actual = EspecialistaUni.query.filter_by(id_cliente=cliente_id, id_usuario=user_id).first()
        especialista_id = esp_actual.id_especialista if esp_actual else user_id
    else:
        especialista_id = request.form.get('id_especialista', type=int) or request.args.get('id_especialista', type=int)

    mes_gestion = (
        request.form.get('mes_gestion')
        or request.args.get('mes_gestion')
        or get_peru_time().strftime('%Y-%m')
    )

    if request.method == 'POST':
        if not especialista_id:
            flash('Debe seleccionar un especialista.', 'warning')
            return redirect(url_for('agenda.gestionar_disponibilidad', mes_gestion=mes_gestion))

        accion = request.form.get('accion', 'guardar')
        intervalo_minutos = request.form.get('intervalo_minutos', type=int) or 50

        try:
            # ACCIÓN A: Copiar horario del mes anterior
            if accion == 'copiar_mes_anterior':
                anio, mes = map(int, mes_gestion.split('-'))
                mes_anterior = f"{anio - 1}-12" if mes == 1 else f"{anio}-{mes - 1:02d}"

                bloques_anteriores = DisponibilidadUni.query.filter_by(
                    id_especialista=especialista_id,
                    mes_gestion=mes_anterior,
                    fecha_especifica=None
                ).all()

                if not bloques_anteriores:
                    flash(f'No se encontraron horarios registrados en el mes anterior ({mes_anterior}) para este especialista.', 'warning')
                    return redirect(url_for('agenda.gestionar_disponibilidad', id_especialista=especialista_id, mes_gestion=mes_gestion))

                DisponibilidadUni.query.filter(
                    DisponibilidadUni.id_especialista == especialista_id,
                    DisponibilidadUni.mes_gestion == mes_gestion,
                    DisponibilidadUni.fecha_especifica == None
                ).delete(synchronize_session=False)

                for b in bloques_anteriores:
                    copia = DisponibilidadUni(
                        id_cliente=cliente_id,
                        id_especialista=especialista_id,
                        mes_gestion=mes_gestion,
                        dia_semana=b.dia_semana,
                        hora_inicio=b.hora_inicio,
                        hora_fin=b.hora_fin,
                        bloqueado_todo_el_dia=b.bloqueado_todo_el_dia,
                        intervalo_minutos=b.intervalo_minutos or 50,
                        estado=True
                    )
                    db.session.add(copia)

                db.session.commit()
                flash(f'Horario de {mes_anterior} copiado exitosamente a {mes_gestion}.', 'success')
                return redirect(url_for('agenda.gestionar_disponibilidad', id_especialista=especialista_id, mes_gestion=mes_gestion))

            # ACCIÓN B: Guardar plantilla semanal del mes seleccionado
            dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

            DisponibilidadUni.query.filter(
                DisponibilidadUni.id_especialista == especialista_id,
                DisponibilidadUni.mes_gestion == mes_gestion,
                DisponibilidadUni.fecha_especifica == None
            ).delete(synchronize_session=False)

            for dia in dias_semana:
                dia_lower = dia.lower()
                bloqueado_dia = request.form.get(f'bloquear_{dia_lower}') == 'on'

                if bloqueado_dia:
                    bloqueo_total = DisponibilidadUni(
                        id_cliente=cliente_id,
                        id_especialista=especialista_id,
                        mes_gestion=mes_gestion,
                        dia_semana=dia,
                        bloqueado_todo_el_dia=True,
                        intervalo_minutos=intervalo_minutos,
                        estado=True
                    )
                    db.session.add(bloqueo_total)
                else:
                    for turno in ['T1', 'T2', 'T3', 'T4']:
                        h_ini_str = request.form.get(f'{dia_lower}_{turno}_inicio')
                        h_fin_str = request.form.get(f'{dia_lower}_{turno}_fin')

                        if h_ini_str and h_fin_str:
                            h_inicio = datetime.strptime(h_ini_str, '%H:%M').time()
                            h_fin = datetime.strptime(h_fin_str, '%H:%M').time()

                            turno_reg = DisponibilidadUni(
                                id_cliente=cliente_id,
                                id_especialista=especialista_id,
                                mes_gestion=mes_gestion,
                                dia_semana=dia,
                                hora_inicio=h_inicio,
                                hora_fin=h_fin,
                                bloqueado_todo_el_dia=False,
                                intervalo_minutos=intervalo_minutos,
                                estado=True
                            )
                            db.session.add(turno_reg)

            # Guardar excepciones puntuales si se llenaron
            fechas_exc = request.form.getlist('exc_fecha[]')
            bloqueados_exc = request.form.getlist('exc_bloqueado[]')
            inicios_exc = request.form.getlist('exc_inicio[]')
            fines_exc = request.form.getlist('exc_fin[]')

            for i, fecha_str in enumerate(fechas_exc):
                if fecha_str:
                    fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d').date()
                    bloqueado = bloqueados_exc[i] == '1' if i < len(bloqueados_exc) else False
                    h_ini_str = inicios_exc[i] if i < len(inicios_exc) else ''
                    h_fin_str = fines_exc[i] if i < len(fines_exc) else ''

                    h_inicio = datetime.strptime(h_ini_str, '%H:%M').time() if (h_ini_str and not bloqueado) else None
                    h_fin = datetime.strptime(h_fin_str, '%H:%M').time() if (h_fin_str and not bloqueado) else None

                    reg = DisponibilidadUni.query.filter_by(
                        id_especialista=especialista_id,
                        fecha_especifica=fecha_obj
                    ).first()

                    if reg:
                        reg.mes_gestion = fecha_obj.strftime('%Y-%m')
                        reg.hora_inicio = h_inicio
                        reg.hora_fin = h_fin
                        reg.bloqueado_todo_el_dia = bloqueado
                        reg.intervalo_minutos = intervalo_minutos
                    else:
                        nueva_exc = DisponibilidadUni(
                            id_cliente=cliente_id,
                            id_especialista=especialista_id,
                            mes_gestion=fecha_obj.strftime('%Y-%m'),
                            dia_semana='Excepción',
                            fecha_especifica=fecha_obj,
                            hora_inicio=h_inicio,
                            hora_fin=h_fin,
                            bloqueado_todo_el_dia=bloqueado,
                            intervalo_minutos=intervalo_minutos,
                            estado=True
                        )
                        db.session.add(nueva_exc)

            db.session.commit()
            flash(f'Disponibilidad de {mes_gestion} guardada correctamente.', 'success')

        except Exception as e:
            db.session.rollback()
            flash(f'Error al procesar la disponibilidad: {str(e)}', 'danger')

        return redirect(url_for('agenda.gestionar_disponibilidad', id_especialista=especialista_id, mes_gestion=mes_gestion))

    # Vista GET: cargar datos filtrados por especialista y mes
    especialistas = EspecialistaUni.query.filter_by(id_cliente=cliente_id).all()
    plantilla_base = []
    excepciones = []
    horarios_map = {}

    if especialista_id:
        plantilla_base = DisponibilidadUni.query.filter_by(
            id_especialista=especialista_id,
            mes_gestion=mes_gestion,
            fecha_especifica=None
        ).order_by(DisponibilidadUni.id_disponibilidad.asc()).all()

        for reg in plantilla_base:
            d_key = reg.dia_semana.lower()
            if d_key not in horarios_map:
                horarios_map[d_key] = {'bloqueado': False, 'turnos': []}
            if reg.bloqueado_todo_el_dia:
                horarios_map[d_key]['bloqueado'] = True
            elif reg.hora_inicio and reg.hora_fin:
                horarios_map[d_key]['turnos'].append({
                    'inicio': reg.hora_inicio.strftime('%H:%M'),
                    'fin': reg.hora_fin.strftime('%H:%M')
                })

        excepciones = DisponibilidadUni.query.filter(
            DisponibilidadUni.id_especialista == especialista_id,
            DisponibilidadUni.mes_gestion == mes_gestion,
            DisponibilidadUni.fecha_especifica != None
        ).order_by(DisponibilidadUni.fecha_especifica.desc()).all()

    intervalo_activo = plantilla_base[0].intervalo_minutos if (plantilla_base and plantilla_base[0].intervalo_minutos) else 50

    return render_template(
        'disponibilidad.html',
        especialistas=especialistas,
        plantilla_base=plantilla_base,
        horarios_map=horarios_map,
        excepciones=excepciones,
        especialista_activo=especialista_id,
        mes_activo=mes_gestion,
        intervalo_activo=intervalo_activo
    )

@agenda_bp.route('/disponibilidad/eliminar/<int:id_disponibilidad>', methods=['POST'])
@login_required
@role_required('Superadmin', 'Director', 'Administrador', 'Especialista')
def eliminar_disponibilidad(id_disponibilidad):
    """Permite eliminar un intervalo o bloque horario específico"""
    bloque = DisponibilidadUni.query.get_or_404(id_disponibilidad)
    especialista_id = bloque.id_especialista
    
    db.session.delete(bloque)
    db.session.commit()
    
    flash('Intervalo horario eliminado correctamente.', 'success')
    return redirect(url_for('agenda.gestionar_disponibilidad', id_especialista=especialista_id))

@agenda_bp.route('/citas/<int:id_cita>/eliminar', methods=['POST'])
@login_required
@role_required('Superadmin', 'Administrador')
def eliminar_cita(id_cita):
    """Elimina físicamente una cita de la base de datos (Exclusivo para Admins)"""
    cita = CitaUni.query.get_or_404(id_cita)

    try:
        # Al eliminar la cita, SQLAlchemy limpiará en cascada los permisos
        # de historia clínica huérfanos gracias a la configuración del modelo.
        db.session.delete(cita)
        db.session.commit()
        flash(f'La Cita #{id_cita} ha sido eliminada permanentemente del sistema.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al intentar eliminar la cita: {str(e)}', 'danger')

    return redirect(url_for('agenda.gestionar_citas'))

@agenda_bp.route('/citas/<int:id_cita>/editar', methods=['POST'])
@login_required
@role_required('Superadmin', 'Director', 'Administrador', 'Recepcionista', 'Especialista')
def editar_cita(id_cita):
    """Permite editar los datos de una cita existente (paciente, especialista, fecha o motivo)."""
    cita = CitaUni.query.get_or_404(id_cita)
    
    id_paciente = request.form.get('id_paciente')
    id_especialista = request.form.get('id_especialista')
    fecha_hora_str = request.form.get('fecha_hora_inicio')
    motivo = request.form.get('motivo_reserva', '')

    try:
        duracion = request.form.get('duracion_minutos', type=int) or 50
        nueva_inicio = datetime.strptime(fecha_hora_str, '%Y-%m-%dT%H:%M')
        nueva_fin = nueva_inicio + timedelta(minutes=duracion)

        # Si se cambió la hora, la duración o el especialista, validamos que no haya choque con otra cita
        if (nueva_inicio != cita.fecha_hora_inicio) or (nueva_fin != cita.fecha_hora_fin) or (int(id_especialista) != cita.id_especialista):
            solapada = CitaUni.query.filter(
                CitaUni.id_especialista == int(id_especialista),
                CitaUni.estado_cita.in_(['Programada', 'Confirmada']),
                CitaUni.fecha_hora_inicio < nueva_fin,
                CitaUni.fecha_hora_fin > nueva_inicio,
                CitaUni.id_cita != id_cita  # Ignorar la cita actual que estamos editando
            ).first()

            if solapada:
                flash('⚠️ Conflicto de horario: El especialista ya cuenta con otra cita activa en esa hora.', 'danger')
                return redirect(url_for('agenda.gestionar_citas'))

        # Aplicar la edición a la base de datos
        cita.id_paciente = int(id_paciente)
        cita.id_especialista = int(id_especialista)
        cita.fecha_hora_inicio = nueva_inicio
        cita.fecha_hora_fin = nueva_fin
        cita.motivo_reserva = motivo

        db.session.commit()
        flash(f'La Cita #{id_cita} fue actualizada exitosamente.', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Error al actualizar la cita: {str(e)}', 'danger')

    return redirect(url_for('agenda.gestionar_citas'))
