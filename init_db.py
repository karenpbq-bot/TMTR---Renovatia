import os
from datetime import datetime, date, timedelta
from flask import Flask
from config import Config
from models import db, Usuario, Cita, HistoriaClinica, SesionEvolucion

def init_db():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)

    with app.app_context():
        print("🔨 Verificando tablas de la base de datos...")
        db.create_all()
        print("✅ Tablas listas.")

        # 1. Crear tu cuenta Administrador Personal
        admin_email = "kbarrientosq.2604@gmail.com"
        admin_user = Usuario.query.filter_by(correo=admin_email).first()

        if not admin_user:
            print(f"👤 Creando cuenta administradora para: {admin_email}...")
            admin_user = Usuario(
                nombres_apellidos="Karen Paola Barrientos",
                correo=admin_email,
                rol="Administrador"
            )
            admin_user.set_password("admin123")
            db.session.add(admin_user)
            db.session.commit()
            print("✅ ¡Cuenta Administrador creada exitosamente!")
        else:
            print("ℹ️ Tu cuenta de administrador ya se encuentra registrada.")

        # 2. Datos de prueba opcionales
        sembrar_datos_ejemplo(db)

def sembrar_datos_ejemplo(database):
    # Crear Especialista de prueba si no existe
    esp_email = "dr.mendoza@consultorio.com"
    especialista = Usuario.query.filter_by(correo=esp_email).first()
    if not especialista:
        especialista = Usuario(
            nombres_apellidos="Dr. Carlos Mendoza",
            correo=esp_email,
            rol="Especialista"
        )
        especialista.set_password("esp123")
        database.session.add(especialista)

    # Crear Recepcionista de prueba si no existe
    rec_email = "recepcion@consultorio.com"
    recepcionista = Usuario.query.filter_by(correo=rec_email).first()
    if not recepcionista:
        recepcionista = Usuario(
            nombres_apellidos="María Torres",
            correo=rec_email,
            rol="Recepcionista"
        )
        recepcionista.set_password("rec123")
        database.session.add(recepcionista)

    # Crear Cliente de prueba si no existe
    cli_email = "ana.gomez@gmail.com"
    cliente = Usuario.query.filter_by(correo=cli_email).first()
    if not cliente:
        cliente = Usuario(
            nombres_apellidos="Ana Sofía Gómez",
            correo=cli_email,
            rol="Cliente"
        )
        cliente.set_password("cli123")
        database.session.add(cliente)

    database.session.commit()

    # Crear Historia Clínica de prueba si no existe
    if cliente and especialista:
        historia = HistoriaClinica.query.filter_by(id_cliente=cliente.id_usuario).first()
        if not historia:
            historia = HistoriaClinica(
                id_cliente=cliente.id_usuario,
                fecha_nacimiento=date(1995, 6, 15),
                edad=29,
                procedencia="Lima, Perú",
                grado_instruccion="Superior Completa",
                institucion="Universidad Nacional",
                nombres_padres="Roberto Gómez / Elena Silva",
                telefono="+51 987654321",
                motivo_consulta="Manifiesta episodios repetidos de ansiedad académica y sobrecarga laboral.",
                problema_actual="Dificultad para conciliar el sueño y palpitaciones antes de presentaciones de trabajo.",
                historia_desarrollo="Sin complicaciones perinatales destacables. Crecimiento regular.",
                historia_escolar_social="Rendimiento académico sobresaliente, tendencia al perfeccionismo.",
                dinamica_familiar="Núcleo familiar funcional pero con altas exigencias de rendimiento.",
                codigo_cie11_dsm5="CIE-11: 6B00 Trastorno de Ansiedad Generalizada / DSM-5: 300.02 (F41.1)",
                objetivos_menor="Desarrollar herramientas de afrontamiento cognitivo-conductual frente al estrés.",
                objetivos_padres="Establecer límites saludables entre tiempo de descanso y expectativas.",
                coordinacion_externa="Sin requerimiento de evaluación psiquiátrica farmacológica al momento.",
                psicologo_responsable=especialista.nombres_apellidos,
                colegiatura_csp="C.Ps.P. 34512"
            )
            database.session.add(historia)
            database.session.commit()

            # Crear Sesión de Evolución de prueba
            sesion = SesionEvolucion(
                id_historia=historia.id_historia,
                fecha_sesion=datetime.now() - timedelta(days=7),
                evolucion_clinica="Primera sesión de evaluación. Se aplica inventario de ansiedad de Beck (BAI) obteniendo puntaje moderado. Se establece encuadre terapéutico.",
                observaciones_conductuales="Paciente orientada en tiempo y espacio. Muestra disposición favorable al diálogo aunque con gestos de tensión motora."
            )
            database.session.add(sesion)

        # Crear Cita de prueba si no existe
        cita = Cita.query.filter_by(id_cliente=cliente.id_usuario).first()
        if not cita:
            cita = Cita(
                id_cliente=cliente.id_usuario,
                id_especialista=especialista.id_usuario,
                fecha_hora=datetime.now() + timedelta(days=2, hours=10),
                estado="Programada",
                motivo="Sesión de seguimiento de técnicas de relajación."
            )
            database.session.add(cita)

        database.session.commit()
        print("🌱 Datos iniciales sembrados con éxito.")

if __name__ == '__main__':
    init_db()
