from datetime import datetime, timedelta, date, time
from app.models import FormularioSalida
from app.utils import generar_pdf_desde_html
from flask import render_template

def _obtener_hora_cercana(hora_estipulada, lista_marcaciones, rango_minutos=60, filtrar=True):
    """Busca la hora mas cercana en la lista."""
    if not hora_estipulada or not lista_marcaciones:
        return None
    
    # LIMPIEZA: Quitamos cualquier None de la lista antes de ordenar
    lista_limpia = [h for h in lista_marcaciones if h is not None]
    
    if not lista_limpia:
        return None

    lista_procesada = lista_limpia
    if filtrar:
        if len(lista_limpia) <= 2:
            return None
        lista_ordenada = sorted(lista_limpia) # Ahora es seguro ordenar
        lista_procesada = lista_ordenada[1:-1]

    if not lista_procesada:
        return None

    dummy_date = datetime(2000, 1, 1)
    target_dt = datetime.combine(dummy_date, hora_estipulada)

    mejor_match = None
    # Usamos un delta muy grande inicial para la comparación
    min_delta_seconds = rango_minutos * 60 

    for marcacion in lista_procesada:
        if marcacion is None:
            continue

        # Blindaje: asegurar que marcacion sea objeto time/datetime
        try:
            marcacion_dt = datetime.combine(dummy_date, marcacion)
            diff_seconds = abs((marcacion_dt - target_dt).total_seconds())
            
            if diff_seconds <= min_delta_seconds:
                min_delta_seconds = diff_seconds
                mejor_match = marcacion
        except Exception:
            continue

    return mejor_match

#Constantes para evitar "numeros magicos".
TOLERANCIA_ALERTA = 15
TOLERANCIA_INCUMPLIMIENTO = 60
def _calcular_estado_marcacion(hora_estipulada, hora_marcacion, es_llegada=False):
    """Retorna el ESTADO semántico (cumplio, alerta, incumplio, no_marco)"""
    if not hora_marcacion:
        return 'no_marco'
    
    try:
        dummy = date.today()
        dt_est = datetime.combine(dummy, hora_estipulada)
        dt_marcacion = datetime.combine(dummy, hora_marcacion)
        
        if es_llegada and dt_marcacion < dt_est:
            # Si es llegada y marcó antes de la hora estipulada, consideramos que cumplió.
            return 'cumplio'

        # Calculamos la diferencia absoluta en minutos (usando números puros)
        diff_segundos = abs((dt_marcacion - dt_est).total_seconds())
        diferencia_minutos = diff_segundos / 60

        if diferencia_minutos >= TOLERANCIA_INCUMPLIMIENTO:
            return 'incumplio'
        elif diferencia_minutos >= TOLERANCIA_ALERTA:
            return 'alerta'
        else:
            return 'cumplio'
    except Exception:
        return 'no_marco'

def _inicializar_estadisticas_funcionario(usuario):
    """Inicializa el diccionario de estadísticas para un funcionario."""
    return {
        'nombre': f"{usuario.nombre} {usuario.apellido}",
        'ci_nro': usuario.cedula,
        'total': 0,
        'cumplio': 0,
        'alerta': 0,
        'incumplio': 0,
    }

def _actualizar_estado_estadisticas(estadisticas, estado):
    """Pasando el objeto de estadísticas y el estado, actualiza los contadores."""
    if estado in ['incumplio', 'no_marco']:
        estadisticas['incumplio'] += 1
    elif estado == 'alerta':
        estadisticas['alerta'] += 1
    else:
        estadisticas['cumplio'] += 1

def _procesar_hora_unica(hora_salida_estipulada, hora_llegada_estipulada, hora_salida_cercana, hora_llegada_cercana, horas_usadas_set, cedula, fecha):
    """Funcion auxiliar para procesar una única hora (salida o llegada)."""
    dummy = date.today()
    estado_llegada = 'no_marco'
    estado_salida = 'no_marco'

    #Calculamos la distancia con la salida y la llegada.
    diff_salida = abs((datetime.combine(dummy, hora_salida_cercana) - datetime.combine(dummy, hora_salida_estipulada)).total_seconds()) if hora_salida_cercana else float('inf')
    diff_llegada = abs((datetime.combine(dummy, hora_llegada_cercana) - datetime.combine(dummy, hora_llegada_estipulada)).total_seconds()) if hora_llegada_cercana else float('inf')

    if diff_salida <= diff_llegada:
        hora_llegada_cercana = None
        estado_salida = _calcular_estado_marcacion(hora_salida_estipulada, hora_salida_cercana, es_llegada=False)
    else:
        hora_salida_cercana = None
        estado_llegada = _calcular_estado_marcacion(hora_llegada_estipulada, hora_llegada_cercana, es_llegada=True)


    horas_usadas_set.add((cedula, fecha, hora_salida_cercana if hora_salida_cercana else hora_llegada_cercana))


    return {
        'hora_salida_cercana': hora_salida_cercana,
        'hora_llegada_cercana': hora_llegada_cercana,
        'estado_salida': estado_salida,
        'estado_llegada': estado_llegada,
    }

def _cantidad_horas(lista_horas, filtrar=True):
    """Funcion para contar la cantidad de horas utilizables para procesar."""
    if not lista_horas:
        return 0

    lista_limpia = [h for h in lista_horas if h is not None]

    lista_procesada = lista_limpia
    if filtrar:
        if len(lista_limpia) <= 2:
            return 0
        lista_ordenada = sorted(lista_limpia)
        lista_procesada = lista_ordenada[1:-1]
    return len(lista_procesada)

def _procesar_marcaciones(formulario, marcacion, cedula, horas_usadas):
    """Función auxiliar para procesar las marcaciones de un formulario."""
    #Inicializamos variables.
    hora_salida_cercana = None
    hora_llegada_cercana = None
    estado_salida = "no_marco"
    estado_llegada = "no_marco"

    try:
        # Verificamos que el formulario tenga las horas estipuladas
        if not formulario.hora_salida_estipulada or not formulario.hora_llegada_estipulada:
            return {
                'hora_salida_cercana': None, 'hora_llegada_cercana': None,
                'estado_salida': 'no_marco', 'estado_llegada': 'no_marco'
            }

        if marcacion:
            #Obtenemos todas las horas marcadas por el usuario en ese día.
            lista_horas = marcacion.get_marcaciones_list()
            #Creamos una lista de horas disponibles (no usadas).
            if lista_horas:
                horas_disponibles = [
                    hora for hora in lista_horas
                    if (cedula, formulario.fecha, hora) not in horas_usadas
                ]
            
            # ---- CASO ESPECIAL: Si solo hay una hora disponible----
            if _cantidad_horas(horas_disponibles) == 1:
                return _procesar_hora_unica(
                    formulario.hora_salida_estipulada,
                    formulario.hora_llegada_estipulada,
                    _obtener_hora_cercana(formulario.hora_salida_estipulada, horas_disponibles),
                    _obtener_hora_cercana(formulario.hora_llegada_estipulada, horas_disponibles),
                    horas_usadas,
                    cedula,
                    formulario.fecha   
                )

            # ---- SALIDA ----
            hora_salida_cercana = _obtener_hora_cercana(formulario.hora_salida_estipulada, horas_disponibles)

            if hora_salida_cercana:
                llave_usada = (cedula, formulario.fecha, hora_salida_cercana)
                horas_usadas.add(llave_usada)
                estado_salida = _calcular_estado_marcacion(formulario.hora_salida_estipulada, hora_salida_cercana, es_llegada=False)
                if hora_salida_cercana in horas_disponibles: horas_disponibles.remove(hora_salida_cercana)

            # ---- LLEGADA ----
            hora_llegada_cercana = _obtener_hora_cercana(formulario.hora_llegada_estipulada, horas_disponibles)
            if hora_llegada_cercana:
                llave_usada = (cedula, formulario.fecha, hora_llegada_cercana)
                horas_usadas.add(llave_usada)
                estado_llegada = _calcular_estado_marcacion(formulario.hora_llegada_estipulada, hora_llegada_cercana, es_llegada=True)
    except Exception as e:
        import logging
        logging.error(f"Error procesando marcaciones para CI {cedula}: {str(e)}")
        
    return {
        'hora_salida_cercana': hora_salida_cercana,
        'hora_llegada_cercana': hora_llegada_cercana,
        'estado_salida': estado_salida,
        'estado_llegada': estado_llegada,
    }



def obtener_reporte_salidas_procesado(fecha_desde, fecha_hasta, cedula_filtro=None):
    """
    Orquestador Principal:
    1- Obtiene los registros que queremos de la base de datos.
    2- Procesa la lógica de negocio (obtiene las horas cercanas a las estipuladas).
    3- Obtiene las estadísticas generales por cada funcionario que haya enviado formularios en el rango de fechas.
    4- Devuelve objetos limpios para la vista.
    """
    #Obtenemos los datos crudos (Delegamos la query al modelo).
    resultados = FormularioSalida.obtener_reporte_admin(fecha_desde, fecha_hasta, cedula_filtro)

    datos_procesados = []
    estadisticas_funcionarios = {}
    horas_usadas = set()

    for formulario, marcacion, usuario in resultados:
        #Utilizamos la funcion auxiliar para procesar las marcaciones.    
        resultado_marcaciones = _procesar_marcaciones(formulario, marcacion, usuario.cedula, horas_usadas)

        #Acumulamos Estadísticas.
        #Si el usuario nunca completo un formulario.
        if usuario.cedula not in estadisticas_funcionarios:
            estadisticas_funcionarios[usuario.cedula] = _inicializar_estadisticas_funcionario(usuario)
        
        #Obtenemos el objeto de estadísticas.
        estadisticas=estadisticas_funcionarios[usuario.cedula]
        #Sumamos al total.
        estadisticas['total'] += 1
        #Actualizamos los estados.
        _actualizar_estado_estadisticas(estadisticas, resultado_marcaciones['estado_salida'])
        _actualizar_estado_estadisticas(estadisticas, resultado_marcaciones['estado_llegada'])
        
        #Preparamos el objeto para la vista (DTO - Data Transfer Object).
        datos_procesados.append({
            'nombre_completo': f"{usuario.nombre} {usuario.apellido}",
            'ci_nro': usuario.cedula,
            'fecha': formulario.fecha.strftime('%d-%m-%Y'),
            'motivo': formulario.motivo,
            'destino': formulario.destino,
            'hora_salida_estipulada': formulario.hora_salida_estipulada.strftime('%H:%M'),
            'hora_llegada_estipulada': formulario.hora_llegada_estipulada.strftime('%H:%M'),
            'hora_salida_cercana': resultado_marcaciones['hora_salida_cercana'].strftime('%H:%M') if resultado_marcaciones['hora_salida_cercana'] else '-',
            'hora_llegada_cercana': resultado_marcaciones['hora_llegada_cercana'].strftime('%H:%M') if resultado_marcaciones['hora_llegada_cercana'] else '-',
            'estado_salida': resultado_marcaciones['estado_salida'],
            'estado_llegada': resultado_marcaciones['estado_llegada'],
        })
    
    return datos_procesados, list(estadisticas_funcionarios.values())


def obtener_reporte_salidas_funcionario(fecha_desde, fecha_hasta):
    """
    Orquestador Principal para el reporte de funcionarios:
    1- Obtiene los registros que queremos de la base de datos.
    2- Procesa la lógica de negocio (obtiene las horas cercanas a las estipuladas).
    3- Devuelve objetos limpios para la vista.
    """
    from flask_login import current_user
    #Obtenemos los datos crudos (Delegamos la query al modelo).
    resultados = FormularioSalida.obtener_reporte_usuario(fecha_desde, fecha_hasta)

    datos_procesados = []
    horas_usadas = set()

    for formulario, marcacion in resultados:
        #Utilizamos la funcion auxiliar para procesar las marcaciones.
        resultado_marcaciones = _procesar_marcaciones(formulario, marcacion, current_user.cedula, horas_usadas)


        #Preparamos el objeto para la vista (DTO - Data Transfer Object).
        datos_procesados.append({
            'fecha': formulario.fecha.strftime('%d-%m-%Y'),
            'motivo': formulario.motivo,
            'destino': formulario.destino,
            'hora_salida_estipulada': formulario.hora_salida_estipulada.strftime('%H:%M'),
            'hora_llegada_estipulada': formulario.hora_llegada_estipulada.strftime('%H:%M'),
            'hora_salida_cercana': resultado_marcaciones['hora_salida_cercana'].strftime('%H:%M') if resultado_marcaciones['hora_salida_cercana'] else '-',
            'hora_llegada_cercana': resultado_marcaciones['hora_llegada_cercana'].strftime('%H:%M') if resultado_marcaciones['hora_llegada_cercana'] else '-',
            'estado_salida': resultado_marcaciones['estado_salida'],
            'estado_llegada': resultado_marcaciones['estado_llegada'],
        })
    
    return datos_procesados

def preparar_reporte_para_pdf(tipo, fecha_desde, fecha_hasta, cedula_filtro=None, usuario_actual=None):
    """Prepara los datos necesarios para generar el reporte en PDF.
       Retorna (pdf_bytes, file_name)"""
    registros = []
    resumen = []
    nombre_funcionario = ""
    cedula_funcionario = ""

    #Obtención de datos segun el tipo.
    if tipo == 'funcionario' and usuario_actual:
        registros = obtener_reporte_salidas_funcionario(fecha_desde, fecha_hasta)
        nombre_funcionario = f"{usuario_actual.nombre} {usuario_actual.apellido}"
        cedula_funcionario = usuario_actual.cedula
        file_name = f"Mis_Salidas_{cedula_funcionario}_{fecha_desde}_{fecha_hasta}.pdf"
    else:
        #Reporte para admin.
        registros, resumen = obtener_reporte_salidas_procesado(fecha_desde, fecha_hasta, cedula_filtro or None)
        file_name = f"Reporte_Salidas_{fecha_desde}_{fecha_hasta}.pdf"
    
    #Renderizado de contenido HTML (usando template especifico para PDF).
    html_content = render_template('pdf_template.html',
                                   registros=registros,
                                   resumen=resumen,
                                   fecha_desde=fecha_desde.strftime('%d-%m-%Y'),
                                   fecha_hasta=fecha_hasta.strftime('%d-%m-%Y'),
                                   fecha_generacion=datetime.now().strftime('%d-%m-%Y %H:%M'),
                                   tipo=tipo,
                                   nombre_funcionario=nombre_funcionario,
                                   cedula_funcionario=cedula_funcionario
                                   )
    #Conversion a PDF usando la utilidad.
    pdf_bytes = generar_pdf_desde_html(html_content)

    return pdf_bytes, file_name
