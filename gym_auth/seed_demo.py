"""
================================================================================
 SEED DE DATOS DEMO — Sistema de Gimnasio
================================================================================
Puebla la base de datos con datos realistas en TODOS los módulos para poder
visualizar que las funcionalidades funcionan:

  clientes + usuarios (login) · membresías · tarjetas · pagos (pagados / con
  deuda / vencidos) · asistencias (con horas pico) · clientes diarios · rutinas
  · planes de entrenamiento (hoy) · reservas de máquina (hoy) · comentarios ·
  recomendaciones de horario (afluencia) · recomendaciones a cliente.

USO:
    cd gym_auth
    python seed_demo.py

Es RE-EJECUTABLE: primero borra sus propios datos demo (marcados con el correo
'@demo.gym', documento 'DEMO...', rutinas '[DEMO]...') y luego reinserta.
No toca al admin ni a tus clientes reales existentes.

Credenciales generadas:  demo1@demo.gym ... demoN@demo.gym  /  contraseña: Demo1234
================================================================================
"""
import os
import random
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from dotenv import dotenv_values
from passlib.context import CryptContext
from sqlalchemy import create_engine, text

random.seed(7)

# ── Conexión ────────────────────────────────────────────────────────────────
_ENV = dotenv_values(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
DATABASE_URL = _ENV.get("DATABASE_URL")
if not DATABASE_URL:
    raise SystemExit("No se encontró DATABASE_URL en .env")
engine = create_engine(DATABASE_URL)

# Un solo hash bcrypt reutilizado (todos los demo usan la misma contraseña)
PWD_HASH = CryptContext(schemes=["bcrypt"], deprecated="auto").hash("Demo1234")

TODAY = date.today()
N_CLIENTS = 40
WEEKS_BACK = 8

# ── Parámetros ──────────────────────────────────────────────────────────────
NOMBRES_M = ["Carlos", "Luis", "Jorge", "Miguel", "Pedro", "Diego", "Andrés", "Kevin",
             "Bruno", "Marco", "Iván", "Raúl", "Sergio", "Fabio", "Renzo", "Hugo"]
NOMBRES_F = ["María", "Lucía", "Ana", "Sofía", "Camila", "Valeria", "Rosa", "Elena",
             "Paola", "Diana", "Karla", "Gaby", "Lorena", "Fiorella", "Milagros", "Nadia"]
APELLIDOS = ["Quispe", "Flores", "Rojas", "Vargas", "Chávez", "Torres", "Ramírez", "Díaz",
             "Mendoza", "Castro", "Guerrero", "Salazar", "Ríos", "Paredes", "Núñez", "Ponce",
             "Cárdenas", "Espinoza", "Zapata", "Bravo"]
OCUPACIONES = ["Estudiante", "Ingeniero", "Docente", "Comerciante", "Enfermero", "Contador",
               "Diseñador", "Chofer", "Abogado", "Programador", None]
# Distribución de horas de ingreso (crea horas pico por la tarde)
HORAS = [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21]
HORA_PESOS = [6, 9, 6, 3, 2, 3, 3, 2, 2, 4, 7, 12, 14, 10, 5]
DIA_NOMBRE = {0: "LUNES", 1: "MARTES", 2: "MIERCOLES", 3: "JUEVES", 4: "VIERNES", 5: "SABADO"}


def nivel_afluencia(cant: float) -> str:
    if cant <= 20:
        return "BAJA"
    if cant <= 45:
        return "MEDIA"
    return "ALTA"


def limpiar(conn):
    """Borra datos demo previos para poder re-ejecutar sin duplicar."""
    demo = "(SELECT id FROM clientes WHERE correo LIKE '%@demo.gym')"
    demo_daily = "(SELECT id FROM clientes_diarios WHERE documento LIKE 'DEMO%')"
    stmts = [
        f"DELETE FROM reservas_maquina WHERE cliente_id IN {demo}",
        f"DELETE FROM plan_maquinas WHERE plan_id IN (SELECT id FROM planes_entrenamiento WHERE cliente_id IN {demo})",
        f"DELETE FROM planes_entrenamiento WHERE cliente_id IN {demo}",
        f"DELETE FROM comentarios_cliente WHERE cliente_id IN {demo}",
        f"DELETE FROM recomendaciones_cliente WHERE cliente_id IN {demo}",
        f"DELETE FROM asistencias WHERE cliente_id IN {demo}",
        f"DELETE FROM pagos WHERE cliente_id IN {demo}",
        f"DELETE FROM tarjetas WHERE cliente_id IN {demo}",
        f"DELETE FROM membresias WHERE cliente_id IN {demo}",
        "DELETE FROM clientes WHERE correo LIKE '%@demo.gym'",
        "DELETE FROM usuarios WHERE email LIKE '%@demo.gym'",
        f"DELETE FROM ingresos_diarios WHERE cliente_id IN {demo_daily}",
        f"DELETE FROM pagos_diarios WHERE cliente_id IN {demo_daily}",
        "DELETE FROM clientes_diarios WHERE documento LIKE 'DEMO%'",
        "DELETE FROM rutina_maquinas WHERE rutina_id IN (SELECT id FROM rutinas WHERE nombre LIKE '[DEMO]%')",
        "DELETE FROM rutinas WHERE nombre LIKE '[DEMO]%'",
        # recomendaciones_horario es global/derivable: se regenera limpio
        "DELETE FROM recomendaciones_horario",
    ]
    for s in stmts:
        conn.execute(text(s))


def main():
    with engine.begin() as conn:
        print("Limpiando datos demo previos...")
        limpiar(conn)

        admin_id = conn.execute(
            text("SELECT id FROM usuarios WHERE rol='ADMINISTRADOR' ORDER BY id LIMIT 1")
        ).scalar()

        # ── Catálogo de máquinas existente (por zona) ───────────────────────
        maquinas = conn.execute(text("SELECT id, nombre, zona FROM maquinas WHERE activa=1")).fetchall()
        por_zona = {}
        for m in maquinas:
            por_zona.setdefault(str(m.zona), []).append(m.id)
        zonas_disp = list(por_zona.keys())

        # ══════════════════════════════════════════════════════════════════
        #  1. CLIENTES + USUARIOS + MEMBRESÍAS + TARJETAS + PAGOS
        # ══════════════════════════════════════════════════════════════════
        print(f"Creando {N_CLIENTS} clientes con membresías, tarjetas y pagos...")
        clientes = []  # (cliente_id, tarjeta_id | None, perfil)
        for i in range(1, N_CLIENTS + 1):
            sexo = "MASCULINO" if i % 2 else "FEMENINO"
            nombres = random.choice(NOMBRES_M if sexo == "MASCULINO" else NOMBRES_F)
            apellidos = f"{random.choice(APELLIDOS)} {random.choice(APELLIDOS)}"
            dni = f"9{i:07d}"
            correo = f"demo{i}@demo.gym"
            edad = random.randint(16, 48)
            grupo = "JOVEN" if edad <= 25 else "ADULTO"
            nacimiento = date(TODAY.year - edad, random.randint(1, 12), random.randint(1, 28))
            estado_cli = "INACTIVO" if i > N_CLIENTS - 4 else "ACTIVO"   # últimos 4 inactivos

            uid = conn.execute(text(
                "INSERT INTO usuarios (nombres, apellidos, dni, email, password, rol, estado) "
                "VALUES (:n,:a,:d,:e,:p,'CLIENTE',:est)"),
                {"n": nombres, "a": apellidos, "d": dni, "e": correo, "p": PWD_HASH,
                 "est": "ACTIVO" if estado_cli == "ACTIVO" else "INACTIVO"}).lastrowid

            cid = conn.execute(text(
                "INSERT INTO clientes (nombres, apellidos, dni, telefono, correo, direccion, sexo, "
                "fecha_nacimiento, ocupacion, grupo_edad, estado, user_id) "
                "VALUES (:n,:a,:d,:tel,:e,:dir,:s,:fn,:oc,:g,:est,:uid)"),
                {"n": nombres, "a": apellidos, "d": dni, "tel": f"9{random.randint(10000000, 99999999)}",
                 "e": correo, "dir": f"Av. Demo {i}", "s": sexo, "fn": nacimiento,
                 "oc": random.choice(OCUPACIONES), "g": grupo, "est": estado_cli, "uid": uid}).lastrowid

            # Perfil de actividad (para variar frecuencia/segmentación)
            perfil = random.choices(["alto", "medio", "bajo", "nulo"], [3, 4, 3, 1])[0]
            if estado_cli == "INACTIVO":
                perfil = "nulo"

            # Membresía (mensual/anual → con tarjeta y asistencia; diario → sin)
            tipo = random.choices(["MENSUAL", "ANUAL", "DIARIO"], [60, 25, 15])[0]
            dur = {"MENSUAL": 30, "ANUAL": 365, "DIARIO": 1}[tipo]
            precio = {"MENSUAL": Decimal("80.00"), "ANUAL": Decimal("800.00"), "DIARIO": Decimal("15.00")}[tipo]
            # La mayoría vigentes; algunas vencidas para mostrar deuda vencida
            vencida = (i % 9 == 0)
            if vencida:
                f_ini = TODAY - timedelta(days=dur + random.randint(5, 30))
                f_fin = f_ini + timedelta(days=dur)
                estado_mem = "VENCIDA"
            else:
                f_ini = TODAY - timedelta(days=random.randint(0, dur - 1)) if dur > 1 else TODAY
                f_fin = f_ini + timedelta(days=dur)
                estado_mem = "ACTIVA"

            mid = conn.execute(text(
                "INSERT INTO membresias (cliente_id, tipo, precio, duracion_dias, fecha_inicio, fecha_fin, estado) "
                "VALUES (:c,:t,:pr,:du,:fi,:ff,:est)"),
                {"c": cid, "t": tipo, "pr": precio, "du": dur, "fi": f_ini, "ff": f_fin, "est": estado_mem}).lastrowid

            # Tarjeta (solo mensual/anual)
            tarjeta_id = None
            if tipo in ("MENSUAL", "ANUAL") and estado_cli == "ACTIVO":
                tarjeta_id = conn.execute(text(
                    "INSERT INTO tarjetas (codigo, cliente_id, fecha_emision, estado) "
                    "VALUES (:cod,:c,:fe,'ACTIVA')"),
                    {"cod": f"GYM-D{i:04d}", "c": cid, "fe": f_ini}).lastrowid

            # Pago (pagado / parcial-con-deuda / vencido)
            metodo = random.choice(["EFECTIVO", "TRANSFERENCIA", "YAPE", "PLIN"])
            if vencida:
                pagado = (precio * Decimal("0.5")).quantize(Decimal("0.01"))
                saldo = precio - pagado
                estado_pago = "VENCIDO"
            elif i % 5 == 0:   # ~20% con deuda pendiente
                pagado = (precio * Decimal("0.4")).quantize(Decimal("0.01"))
                saldo = precio - pagado
                estado_pago = "PENDIENTE"
            else:
                pagado = precio
                saldo = Decimal("0.00")
                estado_pago = "PAGADO"
            conn.execute(text(
                "INSERT INTO pagos (cliente_id, membresia_id, monto_total, monto_pagado, saldo_pendiente, "
                "metodo_pago, fecha_pago, estado) VALUES (:c,:m,:mt,:mp,:sp,:me,:fp,:est)"),
                {"c": cid, "m": mid, "mt": precio, "mp": pagado, "sp": saldo,
                 "me": metodo, "fp": f_ini, "est": estado_pago})

            clientes.append((cid, tarjeta_id, perfil))

        # ══════════════════════════════════════════════════════════════════
        #  2. ASISTENCIAS (historial → horas pico, frecuencia, segmentación)
        # ══════════════════════════════════════════════════════════════════
        print("Generando asistencias (historial de las últimas semanas)...")
        visitas_por_perfil = {"alto": (3, 4), "medio": (1, 2), "bajo": (0, 1), "nulo": (0, 0)}
        asist_rows = []
        monday_this = TODAY - timedelta(days=TODAY.weekday())
        for cid, tid, perfil in clientes:
            if tid is None:
                continue
            lo, hi = visitas_por_perfil[perfil]
            for w in range(WEEKS_BACK):
                if hi == 0:
                    break
                monday = monday_this - timedelta(weeks=w)
                n_vis = random.randint(lo, hi)
                for d in random.sample(range(6), min(n_vis, 6)):   # Lun-Sáb
                    fecha = monday + timedelta(days=d)
                    if fecha > TODAY or fecha < TODAY - timedelta(weeks=WEEKS_BACK):
                        continue
                    hora = random.choices(HORAS, HORA_PESOS)[0]
                    asist_rows.append({
                        "cliente_id": cid, "tarjeta_id": tid, "fecha": fecha,
                        "hora": time(hora, random.randint(0, 59)),
                        "estado": "INGRESO_APROBADO", "motivo": None,
                    })
            # algunas denegaciones para mostrar en "Mi asistencia"
            if perfil in ("alto", "medio") and random.random() < 0.3:
                asist_rows.append({
                    "cliente_id": cid, "tarjeta_id": tid,
                    "fecha": TODAY - timedelta(days=random.randint(1, 20)),
                    "hora": time(random.choice(HORAS), 0),
                    "estado": "INGRESO_DENEGADO", "motivo": "DEUDA_VENCIDA",
                })
        if asist_rows:
            conn.execute(text(
                "INSERT INTO asistencias (cliente_id, tarjeta_id, fecha, hora, estado, motivo_denegacion) "
                "VALUES (:cliente_id,:tarjeta_id,:fecha,:hora,:estado,:motivo)"), asist_rows)

        # ══════════════════════════════════════════════════════════════════
        #  3. RECOMENDACIONES DE HORARIO (afluencia por bloque)
        # ══════════════════════════════════════════════════════════════════
        print("Generando recomendaciones de horario (afluencia)...")
        reco_rows = []
        base_por_hora = {h: p for h, p in zip(HORAS, HORA_PESOS)}
        for d in range(6):  # Lun-Sáb
            factor = 1.4 if d == 4 else (1.2 if d in (0, 2) else 1.0)  # viernes más lleno
            for h in HORAS:
                prom = round(base_por_hora[h] * factor * random.uniform(2.5, 3.6), 2)
                niv = nivel_afluencia(prom)
                reco_rows.append({
                    "dia": DIA_NOMBRE[d], "hi": time(h, 0), "hf": time((h + 1) % 24, 0),
                    "prom": prom, "niv": niv,
                    "rec": 1 if niv == "BAJA" else 0, "ev": 1 if niv == "ALTA" else 0,
                })
        conn.execute(text(
            "INSERT INTO recomendaciones_horario (dia_semana, hora_inicio, hora_fin, cantidad_promedio, "
            "nivel_afluencia, es_recomendado, evitar) VALUES (:dia,:hi,:hf,:prom,:niv,:rec,:ev)"), reco_rows)

        # ══════════════════════════════════════════════════════════════════
        #  4. RECOMENDACIONES A CLIENTE (algunas activas)
        # ══════════════════════════════════════════════════════════════════
        print("Asignando recomendaciones de horario a algunos clientes...")
        activos = [c for c in clientes if c[1] is not None][:6]
        for idx, (cid, _tid, _p) in enumerate(activos):
            dia = DIA_NOMBRE[idx % 6]
            h = 8 + idx
            conn.execute(text(
                "INSERT INTO recomendaciones_cliente (cliente_id, dia_semana, hora_inicio, hora_fin, "
                "cantidad_promedio_estimada, nivel_afluencia, mensaje, origen, estado, creado_por) "
                "VALUES (:c,:d,:hi,:hf,:cp,:niv,:msg,:org,'ACTIVA',:adm)"),
                {"c": cid, "d": dia, "hi": time(h, 0), "hf": time(h + 1, 0),
                 "cp": Decimal("8.00"), "niv": "BAJA",
                 "msg": "Ven a esta hora, hay menos gente.", "org": "ASISTIDA", "adm": admin_id})

        # ══════════════════════════════════════════════════════════════════
        #  5. RUTINAS
        # ══════════════════════════════════════════════════════════════════
        print("Creando rutinas...")
        rutinas_def = [
            ("[DEMO] Pecho y Tríceps", ["PECHO", "TRICEPS"]),
            ("[DEMO] Espalda y Bíceps", ["ESPALDA", "BICEPS"]),
            ("[DEMO] Pierna completa", ["PIERNAS", "GLUTEOS"]),
            ("[DEMO] Full body + cardio", ["PECHO", "ESPALDA", "PIERNAS", "CARDIO"]),
        ]
        rutina_ids = []
        for nombre, zonas in rutinas_def:
            rid = conn.execute(text(
                "INSERT INTO rutinas (nombre, descripcion, activa, creada_por) VALUES (:n,:d,1,:adm)"),
                {"n": nombre, "d": "Rutina de ejemplo", "adm": admin_id}).lastrowid
            mids = []
            for z in zonas:
                mids += por_zona.get(z, [])
            for mmid in dict.fromkeys(mids):
                conn.execute(text("INSERT INTO rutina_maquinas (rutina_id, maquina_id) VALUES (:r,:m)"),
                             {"r": rid, "m": mmid})
            rutina_ids.append(rid)

        # ══════════════════════════════════════════════════════════════════
        #  6. PLANES DE ENTRENAMIENTO (HOY) → demanda / entrenador / afluencia
        # ══════════════════════════════════════════════════════════════════
        print("Generando planes de entrenamiento para hoy...")
        planificadores = [c for c in clientes if c[1] is not None][:14]
        estados_plan = ["PLANEADO", "CONFIRMADO", "EN_CAMINO"]
        for k, (cid, _tid, _p) in enumerate(planificadores):
            zonas = random.sample(zonas_disp, random.randint(1, 3))
            hora = random.choices(HORAS, HORA_PESOS)[0]
            estado = random.choice(estados_plan)
            pid = conn.execute(text(
                "INSERT INTO planes_entrenamiento (cliente_id, fecha, hora_inicio, estado, rutina_id) "
                "VALUES (:c,:f,:h,:e,:r)"),
                {"c": cid, "f": TODAY, "h": time(hora, 0), "e": estado,
                 "r": random.choice(rutina_ids) if random.random() < 0.4 else None}).lastrowid
            mids = []
            for z in zonas:
                mids += por_zona.get(z, [])
            for mmid in dict.fromkeys(mids):
                conn.execute(text("INSERT INTO plan_maquinas (plan_id, maquina_id) VALUES (:p,:m)"),
                             {"p": pid, "m": mmid})

        # ══════════════════════════════════════════════════════════════════
        #  7. RESERVAS DE MÁQUINA (HOY)
        # ══════════════════════════════════════════════════════════════════
        print("Generando reservas de máquina para hoy...")
        reservistas = [c for c in clientes if c[1] is not None][:12]
        for cid, _tid, _p in reservistas:
            maq = random.choice(maquinas)
            h = random.choice([8, 9, 17, 18, 19, 20])
            dur = random.choice([30, 45, 60])
            fin = (datetime.combine(TODAY, time(h, 0)) + timedelta(minutes=dur)).time()
            conn.execute(text(
                "INSERT INTO reservas_maquina (cliente_id, maquina_id, fecha, hora_inicio, hora_fin, "
                "duracion_min, estado) VALUES (:c,:m,:f,:hi,:hf,:d,'ACTIVA')"),
                {"c": cid, "m": maq.id, "f": TODAY, "hi": time(h, 0), "hf": fin, "d": dur})

        # ══════════════════════════════════════════════════════════════════
        #  8. COMENTARIOS
        # ══════════════════════════════════════════════════════════════════
        print("Generando comentarios de clientes...")
        coment = [
            ("SUGERENCIA", "Más mancuernas", "Sería genial tener más mancuernas de 10kg.", "NUEVO"),
            ("QUEJA", "Aire acondicionado", "En la tarde hace mucho calor en la zona de pesas.", "NUEVO"),
            ("COMENTARIO", None, "El nuevo entrenador es excelente, muy atento.", "LEIDO"),
            ("RECOMENDACION", "Horario extendido", "Podrían abrir más temprano los sábados.", "NUEVO"),
            ("SUGERENCIA", "Música", "Bajar un poco el volumen de la música por las mañanas.", "ARCHIVADO"),
            ("COMENTARIO", "Limpieza", "Los baños siempre están muy limpios, felicitaciones.", "LEIDO"),
        ]
        for j, (tipo, asunto, msg, est) in enumerate(coment):
            cid = clientes[j][0]
            conn.execute(text(
                "INSERT INTO comentarios_cliente (cliente_id, tipo, asunto, mensaje, estado) "
                "VALUES (:c,:t,:a,:m,:e)"),
                {"c": cid, "t": tipo, "a": asunto, "m": msg, "e": est})

        # ══════════════════════════════════════════════════════════════════
        #  9. CLIENTES DIARIOS (+ pagos e ingresos)
        # ══════════════════════════════════════════════════════════════════
        print("Creando clientes diarios con pagos e ingresos...")
        for i in range(1, 8):
            nom = f"{random.choice(NOMBRES_M + NOMBRES_F)} {random.choice(APELLIDOS)}"
            did = conn.execute(text(
                "INSERT INTO clientes_diarios (nombre, documento, estado) VALUES (:n,:doc,'ACTIVO')"),
                {"n": nom, "doc": f"DEMO{i:03d}"}).lastrowid
            # pagos e ingresos en varios días (incluye hoy)
            for off in random.sample(range(0, 15), random.randint(1, 4)):
                f = TODAY - timedelta(days=off)
                conn.execute(text(
                    "INSERT INTO pagos_diarios (cliente_id, monto, fecha_pago) VALUES (:c,:m,:f)"),
                    {"c": did, "m": Decimal("15.00"), "f": f})
                conn.execute(text(
                    "INSERT INTO ingresos_diarios (cliente_id, fecha, hora, estado, motivo) "
                    "VALUES (:c,:f,:h,'APROBADO',NULL)"),
                    {"c": did, "f": f, "h": time(random.choice(HORAS), random.randint(0, 59))})

        # ── Resumen ─────────────────────────────────────────────────────────
        n_clientes = conn.execute(
            text("SELECT COUNT(*) FROM clientes WHERE correo LIKE '%@demo.gym'")
        ).scalar()

        print("\n" + "=" * 60)
        print(" SEED COMPLETADO")
        print("=" * 60)
        print(f"  Clientes demo:        {n_clientes}")
        print(f"  Asistencias:          {len(asist_rows)}")
        print(f"  Recom. horario:       {len(reco_rows)} bloques")
        print(f"  Planes de hoy:        {len(planificadores)}")
        print(f"  Reservas de hoy:      {len(reservistas)}")
        print(f"  Rutinas:              {len(rutina_ids)}")
        print("  Clientes diarios:     7")
        print(f"  Comentarios:          {len(coment)}")
        print("-" * 60)
        print(f"  Login clientes demo:  demo1@demo.gym ... demo{N_CLIENTS}@demo.gym")
        print("  Contraseña:           Demo1234")
        print("  Login admin:          admin@gym.com / Admin123")
        print("=" * 60)


if __name__ == "__main__":
    main()
