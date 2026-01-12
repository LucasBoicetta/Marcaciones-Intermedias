from datetime import datetime, timedelta, date, time
from app.models import FormularioSalida

def _obtener_hora_cercana(hora_estipulada, lista_marcaciones, rango_minutos=60, filtrar=True):
    """Busca la hora mas cercana en la lista."""
    if not hora_estipulada or not lista_marcaciones:
        return None
    
    #Filtramos la Entrada y Salida.
    if filtrar:
        #Si hay 2 o menos marcaciones no hay intermedios.
        if len(lista_marcaciones) <= 2:
            return None
        
        #Ordenamos por seguridad.
        lista_ordenada = sorted(lista_marcaciones)

        #Recortamos la lista desde el segundo elemento hasta el penultimo.
        lista_procesada = lista_ordenada[1:-1]

        if not lista_procesada:
            return None

    #Convertir la hora estipulada a datetime para comparacion
    dummy_date = datetime(2000, 1, 1)
    target_dt = datetime.combine(dummy_date, hora_estipulada)

    mejor_match = None
    min_delta = timedelta(minutes=rango_minutos)

    for marcacion in lista_procesada if filtrar else lista_marcaciones:
        if marcacion is None:
            continue

        marcacion_dt = datetime.combine(dummy_date, marcacion)
        delta = abs(marcacion_dt - target_dt)
        if delta <= min_delta:
            min_delta = delta
            mejor_match = marcacion

    return mejor_match

#Constantes para evitar "numeros magicos".
TOLERANCIA_ALERTA = 15
TOLERANCIA_INCUMPLIMIENTO = 60
def _calcular_estado_marcacion(hora_estipulada, hora_marcacion):
    """Retorna el ESTADO semántico (cumplio, alerta, incumplio, no_marco)"""
    if not hora_marcacion:
        return 'no_marco'
    
    dummy = date.today()
    dt_est = datetime.combine(dummy, hora_estipulada)
    dt_marcacion = datetime.combine(dummy, hora_marcacion)
    diferencia_minutos = abs((dt_marcacion - dt_est).total_seconds() / 60)

    if diferencia_minutos >= TOLERANCIA_INCUMPLIMIENTO:
        return 'incumplio'
    elif diferencia_minutos >= TOLERANCIA_ALERTA:
        return 'alerta'
    else:
        return 'cumplio'
    

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


def _procesar_marcaciones(formulario, marcacion, cedula, horas_usadas):
    """Función auxiliar para procesar las marcaciones de un formulario."""
    #Inicializamos variables.
    hora_salida_cercana = None
    hora_salida_cercana = None
    estado_salida = "no_marco"
    estado_llegada = "no_marco"

    if marcacion:
        #Obtenemos todas las horas marcadas por el usuario en ese día.
        lista_horas = marcacion.get_marcaciones_list()
        #Creamos una lista de horas disponibles (no usadas).
        if lista_horas:
            horas_disponibles = [
                hora for hora in lista_horas
                if (cedula, formulario.fecha, hora) not in horas_usadas
            ]

        # ---- SALIDA ----
        hora_salida_cercana = _obtener_hora_cercana(formulario.hora_salida_estipulada, horas_disponibles)

        if hora_salida_cercana:
            llave_usada = (cedula, formulario.fecha, hora_salida_cercana)
            horas_usadas.add(llave_usada)
            estado_salida = _calcular_estado_marcacion(formulario.hora_salida_estipulada, hora_salida_cercana)
            if hora_salida_cercana in horas_disponibles: horas_disponibles.remove(hora_salida_cercana)

        # ---- LLEGADA ----
        hora_llegada_cercana = _obtener_hora_cercana(formulario.hora_llegada_estipulada, horas_disponibles)
        if hora_llegada_cercana:
            llave_usada = (cedula, formulario.fecha, hora_llegada_cercana)
            horas_usadas.add(llave_usada)
            estado_llegada = _calcular_estado_marcacion(formulario.hora_llegada_estipulada, hora_llegada_cercana)
    
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

