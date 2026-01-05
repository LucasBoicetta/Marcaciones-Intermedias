from datetime import datetime, timedelta

def obtener_hora_cercana(hora_estipulada, lista_marcaciones, rango_minutos=60, filtrar=False):
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