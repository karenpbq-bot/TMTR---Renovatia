import os
from datetime import datetime, date, timedelta, timezone
from flask import Flask
from config import Config
from models import (
    db, ClienteEmpresa, UsuarioUni, EspecialistaUni, 
    PacienteUni, DisponibilidadUni, CitaUni, 
    HistoriaClinica, SesionEvolucion
)

def init_db():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)

    # Definir la zona horaria de Perú (UTC-5)
    PERU_TZ = timezone(timedelta(hours=-5))

    with app.app_context():
        print("🔨 Verificando tablas de la base de datos...")
        db.create_all()
        print("✅ Tablas listas.")

        # 0. Crear un Consultorio / Cliente de Prueba Base (para el multi-tenant)
        cliente_prueba = ClienteEmpresa.query.filter_by(ruc="20123456789").first()
        if not cliente_prueba:
            print("🏢 Creando consultorio de prueba por defecto...")
            cliente_prueba = ClienteEmpresa(
                tipo_especialidad="Psicología",
                nombre_empresa="Centro Psicológico Integral S.A.C.",
                nombre_marca="Renovatia Consultorio",
                ruc="20123456789",
                representante="Karen Paola Barrientos",
                contacto_correo="contacto@renovatia.com",
                contacto_telefono="+51 987654321",
                tipo_plan="Pro",
                vigencia_plan=date(2027, 12, 31),
                costo_plan=150.00,
                modo_pago="Transferencia"
            )
            db.session.add(cliente_prueba)
            db.session.commit()
            print(f"✅ Consultorio creado con Código 5D: {cliente_prueba.codigo_invitacion_5d}")

        # 1. Crear tu cuenta Superadmin / Director Principal
        admin_email = "kbarrientosq.2604@gmail.com"
        admin_user = UsuarioUni.query.filter_by(correo=admin_email).first()

        if not admin_user:
            print(f"👤 Creando cuenta de Director para: {admin_email}...")
            admin_user = UsuarioUni(
                id_cliente=cliente_prueba.id_cliente,
                nombres_apellidos="Karen Paola Barrientos",
                correo=admin_email,
                rol="Director",
                fecha_registro=datetime.now(PERU_TZ)
            )
            admin_user.set_password("admin123")
            db.session.add(admin_user)
            db.session.commit()
            print("✅ ¡Cuenta Director creada exitosamente!")
        else:
            admin_user.rol = "Director"
            admin_user.id_cliente = cliente_prueba.id_cliente
            admin_user.set_password("admin123")
            db.session.commit()
            print("ℹ️ Tu cuenta de Director ya se encuentra registrada y actualizada.")

        # 2. Sembrar datos de ejemplo (Especialistas, Pacientes, Disponibilidad y Citas)
        sembrar_datos_ejemplo(db, cliente_prueba, PERU_TZ)

def sembrar_datos_ejemplo(database, cliente, peru_tz):
    # Crear Especialista de prueba en uni_especialistas
    esp_email = "dr.mendoza@consultorio.com"
    especialista = EspecialistaUni.query.filter_by(email=esp_email).first()
    if not especialista:
        especialista = EspecialistaUni(
            id_cliente=cliente.id_cliente,
            nombre="Carlos",
            apellido="Mendoza",
            matricula="C.Ps.P. 34512",
            especialidades=["Psicología Clínica", "Terapia Cognitivo-Conductual"],
            telefono="+51 911223344",
            email=esp_email
        )
        especialista.set_password("esp123")
        database.session.add(especialista)
        database.session.commit()

    # Crear Paciente de prueba en uni_pacientes
    cli_email = "ana.gomez@gmail.com"
    paciente = PacienteUni.query.filter_by(email=cli_email).first()
    if not paciente:
        paciente = PacienteUni(
            id_cliente=cliente.id_cliente,
            nombre="Ana Sofía",
            apellido="Gómez",
            dni="71234567",
            fecha_nac=date(1995, 6, 15),
            telefono="+51 987654321",
            direccion="Arequipa, Perú",
            grupo_sangre="O+",
            obra_social="Particular",
            alergias="Ninguna",
            email=cli_email
        )
        paciente.set_password("cli123")
        database.session.add(paciente)
        database.session.commit()

    # Crear Historia Clínica de Psicología (psi_historias_clinicas)
    if paciente and especialista:
        historia = HistoriaClinica.query.filter_by(id_paciente=paciente.id_paciente).first()
        if not historia:
            historia = HistoriaClinica(
                id_paciente=paciente.id_paciente,
                fecha_nacimento=date(1995, 6, 15),
                edad=29,
                procedencia="Arequipa, Perú",
                grado_instruccion="Superior Completa",
                institucion="Universidad Nacional",
                nombres_padres="Roberto Gómez / Elena Silva",
                telefono="+51 987654321",
                motivo_consulta="Manifiesta episodios repetidos de ansiedad académica y sobrecarga laboral.",
                problema_actual="Dificultad para conciliar el sueño y palpitaciones antes de presentaciones.",
                codigo_cie11_dsm5="CIE-11: 6B00 Trastorno de Ansiedad Generalizada",
                psicologo_responsable=f"{especialista.nombre} {especialista.apellido}",
                colegiatura_csp=especialista.matricula,
                fecha_creacion=datetime.now(peru_tz)
            )
            database.session.add(historia)
            database.session.commit()

            # Crear Sesión de Evolución de prueba (psi_sesiones_evolucion)
            sesion = SesionEvolucion(
                id_historia=historia.id_historia,
                fecha_sesion=datetime.now(peru_tz) - timedelta(days=7),
                evolucion_clinica="Primera sesión de evaluación. Se establece encuadre terapéutico.",
                observaciones_conductuales="Paciente orientada en tiempo y espacio."
            )
            database.session.add(sesion)

        # Crear Disponibilidad de ejemplo para el especialista (uni_disponibilidad)
        disp_existente = DisponibilidadUni.query.filter_by(id_especialista=especialista.id_especialista).first()
        if not disp_existente:
            disponibilidad = DisponibilidadUni(
                id_cliente=cliente.id_cliente,
                id_especialista=especialista.id_especialista,
                dia_semana="Lunes",
                hora_inicio=datetime.strptime("09:00", "%H:%M").time(),
                hora_fin=datetime.strptime("14:00", "%H:%M").time(),
                intervalo_minutos=45,
                estado=True
            )
            database.session.add(disponibilidad)

        # Crear Cita de prueba en el módulo de agendamiento (uni_citas)
        cita_existente = CitaUni.query.filter_by(id_paciente=paciente.id_paciente).first()
        if not cita_existente:
            ahora_peru = datetime.now(peru_tz)
            inicio_cita = ahora_peru + timedelta(days=2, hours=10)
            fin_cita = inicio_cita + timedelta(minutes=45)

            cita = CitaUni(
                id_cliente=cliente.id_cliente,
                id_paciente=paciente.id_paciente,
                id_especialista=especialista.id_especialista,
                fecha_hora_inicio=inicio_cita,
                fecha_hora_fin=fin_cita,
                estado_cita="Programada",
                motivo_reserva="Sesión de seguimiento de técnicas de relajación."
            )
            database.session.add(cita)

        database.session.commit()
        print("🌱 Datos iniciales, especialistas, pacientes y citas de agendamiento sembrados con éxito.")

if __name__ == '__main__':
    init_db()
