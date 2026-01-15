from app import app, db
from app.models import FormularioSalida, Usuario
from sqlalchemy import text
from datetime import datetime, timedelta, time
import random

def generar_hora_aleatoria(base_hora, minutos_variacion=15):
    """Genera una hora con variación aleatoria"""
    dummy_date = datetime.combine(datetime.today(), base_hora)
    variacion = random.randint(-minutos_variacion, minutos_variacion)
    nueva_hora = dummy_date + timedelta(minutes=variacion)
    return nueva_hora.time()

def limpiar_datos_anteriores():
    """Elimina TODOS los datos de prueba anteriores"""
    print("🗑️  Limpiando TODOS los datos anteriores...")
    
    # Eliminar TODAS las marcaciones de semilla_sistema
    sql_delete_marcaciones = text("""
        DELETE FROM control_asistencia.registro_entrada_salida
        WHERE usuario_alta = 'semilla_sistema'
    """)
    result_marc = db.session.execute(sql_delete_marcaciones)
    
    # Eliminar TODOS los formularios
    sql_delete_forms = text("""
        DELETE FROM registro_intermedio.formulario_salida
    """)
    result_forms = db.session.execute(sql_delete_forms, {})
    
    # Commit de la limpieza
    db.session.commit()
    
    print(f"   ✓ Eliminadas {result_marc.rowcount} marcaciones anteriores")
    print(f"   ✓ Eliminados {result_forms.rowcount} formularios anteriores")
    print()

def insertar_marcacion_reloj(ci_nro, fecha, hora_marcacion):
    """Inserta una marcación en la tabla base registro_entrada_salida"""
    if hora_marcacion is None:
        return
    
    registrado = datetime.combine(fecha, hora_marcacion)
    fecha_alta = datetime.now()
    
    sql = text("""
        INSERT INTO control_asistencia.registro_entrada_salida 
        (personal_id, registrado, fecha_alta, fecha_modificacion, 
         usuario_alta, usuario_modificacion, registrado_modificado, estado, mecanismo_creacion) 
        SELECT 
            p.id as personal_id,
            :registrado as registrado,
            :fecha_alta as fecha_alta,
            :fecha_alta as fecha_modificacion,
            'semilla_sistema' as usuario_alta,
            'semilla_sistema' as usuario_modificacion,
            :registrado as registrado_modificado,
            'PEN' as estado,
            1 as mecanismo_creacion
        FROM ficha_personal.personal p
        INNER JOIN asistencias.funcionarios f ON f.cedula = p.ci_nro
        WHERE f.cedula = :ci_nro
        LIMIT 1
    """)
    
    db.session.execute(sql, {
        'ci_nro': ci_nro,
        'registrado': registrado,
        'fecha_alta': fecha_alta
    })

def generar_marcaciones_para_formulario(hora_salida_est, hora_llegada_est, fecha, tipo_caso):
    """
    Genera marcaciones realistas:
    - Siempre incluye marcación de entrada (07:00) y salida del trabajo (15:00)
    - tipo_caso 1: No marcó salida ni llegada intermedia (solo 2 marcaciones)
    - tipo_caso 2: Solo marcó UNA de las intermedias (3 marcaciones totales)
    - tipo_caso 3: Marcó ambas intermedias (4+ marcaciones)
    
    Estados:
    - Correcto (🟢): ≤ 15 minutos
    - Alerta (🟡): > 15 min y ≤ 60 min
    - Falta (🔴): > 60 min o no marcó
    """
    dummy_salida = datetime.combine(fecha, hora_salida_est)
    dummy_llegada = datetime.combine(fecha, hora_llegada_est)
    
    # SIEMPRE generar marcación de entrada (07:00) y salida del trabajo (15:00)
    hora_entrada_trabajo = generar_hora_aleatoria(time(7, 0), 10)  # ~07:00 ±10 min
    hora_salida_trabajo = generar_hora_aleatoria(time(15, 0), 10)  # ~15:00 ±10 min
    
    marcaciones = [hora_entrada_trabajo]  # Siempre empieza con entrada
    escenario = "desconocido"
    
    if tipo_caso == 1:
        # CASO 1: No marcó ni salida ni llegada intermedia
        # Solo 2 marcaciones: entrada trabajo + salida trabajo
        marcaciones.append(hora_salida_trabajo)
        escenario = "🔴 sin_marcar_intermedias"
        
    elif tipo_caso == 2:
        # CASO 2: Solo marcó UNA intermedia
        marca_salida = random.choice([True, False])
        
        if marca_salida:
            # Solo marcó salida intermedia
            variacion = random.choice(['correcto', 'alerta', 'falta'])
            
            if variacion == 'correcto':
                # ≤ 15 minutos
                minutos_var = random.randint(-15, 15)
                hora_marc = (dummy_salida + timedelta(minutes=minutos_var)).time()
                emoji = '🟢'
            elif variacion == 'alerta':
                # > 15 min y ≤ 60 min
                minutos_var = random.randint(16, 60)
                hora_marc = (dummy_salida + timedelta(minutes=minutos_var)).time()
                emoji = '🟡'
            else:  # falta
                # > 60 min
                minutos_var = random.randint(61, 120)
                hora_marc = (dummy_salida + timedelta(minutes=minutos_var)).time()
                emoji = '🔴'
            
            # 3 marcaciones: entrada + salida intermedia + salida trabajo
            marcaciones.append(hora_marc)
            marcaciones.append(hora_salida_trabajo)
            escenario = f"{emoji} solo_salida_{variacion}"
            
        else:
            # Solo marcó llegada intermedia
            variacion = random.choice(['correcto', 'alerta', 'falta'])
            
            if variacion == 'correcto':
                minutos_var = random.randint(-15, 15)
                hora_marc = (dummy_llegada + timedelta(minutes=minutos_var)).time()
                emoji = '🟢'
            elif variacion == 'alerta':
                minutos_var = random.randint(16, 60)
                hora_marc = (dummy_llegada - timedelta(minutes=minutos_var)).time()
                emoji = '🟡'
            else:  # falta
                minutos_var = random.randint(61, 120)
                hora_marc = (dummy_llegada - timedelta(minutes=minutos_var)).time()
                emoji = '🔴'
            
            # 3 marcaciones: entrada + llegada intermedia + salida trabajo
            marcaciones.append(hora_marc)
            marcaciones.append(hora_salida_trabajo)
            escenario = f"{emoji} solo_llegada_{variacion}"
            
    else:  # tipo_caso == 3
        # CASO 3: Marcó AMBAS intermedias (4 marcaciones mínimo)
        
        # Variaciones independientes
        var_salida = random.choice(['correcto', 'alerta', 'falta'])
        var_llegada = random.choice(['correcto', 'alerta', 'falta'])
        
        # Generar hora de salida intermedia
        if var_salida == 'correcto':
            minutos_var = random.randint(-15, 15)
            hora_salida_marc = (dummy_salida + timedelta(minutes=minutos_var)).time()
        elif var_salida == 'alerta':
            minutos_var = random.randint(16, 60)
            hora_salida_marc = (dummy_salida + timedelta(minutes=minutos_var)).time()
        else:  # falta
            minutos_var = random.randint(61, 120)
            hora_salida_marc = (dummy_salida + timedelta(minutes=minutos_var)).time()
        
        # Generar hora de llegada intermedia
        if var_llegada == 'correcto':
            minutos_var = random.randint(-15, 15)
            hora_llegada_marc = (dummy_llegada + timedelta(minutes=minutos_var)).time()
        elif var_llegada == 'alerta':
            minutos_var = random.randint(16, 60)
            hora_llegada_marc = (dummy_llegada - timedelta(minutes=minutos_var)).time()
        else:  # falta
            minutos_var = random.randint(61, 120)
            hora_llegada_marc = (dummy_llegada - timedelta(minutes=minutos_var)).time()
        
        # 4 marcaciones: entrada + salida intermedia + llegada intermedia + salida trabajo
        marcaciones.append(hora_salida_marc)
        marcaciones.append(hora_llegada_marc)
        marcaciones.append(hora_salida_trabajo)
        
        # Determinar color según peor caso
        if var_salida == 'falta' or var_llegada == 'falta':
            color = '🔴'
        elif var_salida == 'alerta' or var_llegada == 'alerta':
            color = '🟡'
        else:
            color = '🟢'
        
        escenario = f"{color} ambas_s:{var_salida}_l:{var_llegada}"
    
    # Ordenar marcaciones por hora
    marcaciones.sort()
    
    return marcaciones, escenario

def cargar_datos_completos():
    with app.app_context():
        print("=" * 80)
        print("GENERANDO DATOS DE PRUEBA - AÑO 2026")
        print("=" * 80)
        print()
        
        # Limpiar TODOS los datos anteriores
        limpiar_datos_anteriores()
        
        # Obtener 20 funcionarios
        funcionarios = Usuario.query.limit(20).all()
        
        if not funcionarios:
            print("❌ ERROR: No hay funcionarios en la BD")
            return
        
        print(f"✓ Encontrados {len(funcionarios)} funcionarios para generar datos")
        print()
        
        # Motivos y destinos
        motivos = [
            "Consulta médica", "Trámites bancarios", "IPS", 
            "Gestión judicial", "Reunión externa", "Trámite personal",
            "Consulta odontológica", "Retiro de documentos",
            "Trámites municipales", "Gestión administrativa"
        ]
        
        destinos = [
            "Hospital de Clínicas", "Banco Nacional", "IPS Central",
            "Palacio de Justicia", "Municipalidad", "SET",
            "ANDE", "ESSAP", "Registro Civil", "Policía Nacional"
        ]
        
        # Generar datos SOLO para 2026 (desde 01-01-2026 hasta hoy)
        fecha_inicio = datetime(2026, 1, 1).date()
        fecha_fin = datetime.now().date()
        
        print(f"📅 Generando datos desde {fecha_inicio} hasta {fecha_fin}")
        print()
        
        contador_formularios = 0
        contador_marcaciones = 0
        
        casos_tipo1 = 0
        casos_tipo2 = 0
        casos_tipo3 = 0
        
        try:
            for func in funcionarios:
                cantidad_salidas = random.randint(3, 6)
                fechas_salida = []
                
                for _ in range(cantidad_salidas):
                    dias_diff = (fecha_fin - fecha_inicio).days
                    fecha_random = fecha_inicio + timedelta(days=random.randint(0, dias_diff))
                    
                    # Evitar fines de semana
                    while fecha_random.weekday() >= 5:
                        fecha_random += timedelta(days=1)
                        if fecha_random > fecha_fin:
                            fecha_random -= timedelta(days=2)
                            
                    fechas_salida.append(fecha_random)
                
                for fecha in fechas_salida:
                    existe_form = FormularioSalida.query.filter_by(
                        ci_nro=func.cedula,
                        fecha=fecha
                    ).first()
                    
                    if existe_form:
                        continue
                    
                    # Horarios intermedios entre 08:00 y 14:00
                    hora_inicio_laboral = time(8, 0)
                    minutos_desde_inicio = random.randint(0, 300)  # 0-5 horas
                    dummy_salida = datetime.combine(fecha, hora_inicio_laboral) + timedelta(minutes=minutos_desde_inicio)
                    hora_salida_est = dummy_salida.time()
                    
                    minutos_ausencia = random.randint(30, 90)
                    hora_llegada_est = (dummy_salida + timedelta(minutes=minutos_ausencia)).time()
                    
                    # Distribución: 20% caso1, 30% caso2, 50% caso3
                    tipo_caso = random.choices([1, 2, 3], weights=[20, 30, 50])[0]
                    
                    if tipo_caso == 1:
                        casos_tipo1 += 1
                    elif tipo_caso == 2:
                        casos_tipo2 += 1
                    else:
                        casos_tipo3 += 1
                    
                    nuevo_form = FormularioSalida(
                        ci_nro=func.cedula,
                        fecha=fecha,
                        hora_salida_estipulada=hora_salida_est,
                        hora_llegada_estipulada=hora_llegada_est,
                        motivo=random.choice(motivos),
                        destino=random.choice(destinos),
                        estado=True,
                        fecha_creacion=datetime.combine(fecha, time(7, 0))
                    )
                    
                    db.session.add(nuevo_form)
                    contador_formularios += 1
                    
                    marcaciones, escenario = generar_marcaciones_para_formulario(
                        hora_salida_est, 
                        hora_llegada_est, 
                        fecha,
                        tipo_caso
                    )
                    
                    for hora_marc in marcaciones:
                        insertar_marcacion_reloj(func.cedula, fecha, hora_marc)
                        contador_marcaciones += 1
                    
                    emoji_caso = {
                        1: '⭕',
                        2: '🔶',
                        3: '✅'
                    }
                    
                    nombre_completo = f"{func.nombre} {func.apellido}"
                    cant_marc = len(marcaciones)
                    print(f"{emoji_caso[tipo_caso]} CASO {tipo_caso} ({cant_marc} marc) | {nombre_completo[:25]:<25} | {fecha} | {escenario}")
            
            db.session.commit()
            print("\n" + "=" * 80)
            print(f"✓ DATOS GENERADOS EXITOSAMENTE")
            print(f"✓ Formularios creados: {contador_formularios}")
            print(f"✓ Marcaciones insertadas: {contador_marcaciones}")
            print()
            print(f"📊 Distribución por casos:")
            if contador_formularios > 0:
                print(f"   ⭕ Caso 1 (2 marc - sin intermedias):    {casos_tipo1} ({casos_tipo1/contador_formularios*100:.1f}%)")
                print(f"   🔶 Caso 2 (3 marc - solo una):          {casos_tipo2} ({casos_tipo2/contador_formularios*100:.1f}%)")
                print(f"   ✅ Caso 3 (4 marc - ambas):             {casos_tipo3} ({casos_tipo3/contador_formularios*100:.1f}%)")
            print()
            print(f"🎨 Estados esperados:")
            print(f"   🟢 Correcto: ≤ 15 minutos")
            print(f"   🟡 Alerta: > 15 min y ≤ 60 min")
            print(f"   🔴 Falta: > 60 min o sin marcar")
            print("=" * 80)
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ ERROR al guardar: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    cargar_datos_completos()