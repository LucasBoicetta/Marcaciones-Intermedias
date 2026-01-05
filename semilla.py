from app import app, db
from app.models import FormularioSalida, MarcacionIntermediaGeneral
from datetime import datetime, timedelta, time
import random

def cargar_datos_prueba():
    with app.app_context():
        print("--- INICIANDO GENERACIÓN DE DATOS DE PRUEBA ---")
        
        marcaciones_reales = MarcacionIntermediaGeneral.query.order_by(
            MarcacionIntermediaGeneral.fecha_marcacion.desc()
        ).limit(20).all()

        if not marcaciones_reales:
            print("ERROR: No se encontraron datos.")
            return

        contador = 0
        for real in marcaciones_reales:
            # USAMOS EL MÉTODO QUE CREAMOS EN MODELS PARA OBTENER OBJETOS TIME
            lista_horas = real.get_marcaciones_list()
            
            if not lista_horas:
                continue
            
            # Tomamos la primera hora disponible como referencia
            hora_referencia = lista_horas[0]

            existe = FormularioSalida.query.filter_by(
                ci_nro=real.ci_nro, 
                fecha=real.fecha_marcacion
            ).first()

            if not existe:
                dummy_date = datetime.combine(datetime.today(), hora_referencia)
                
                # CASO 1: Normal (10 min antes)
                # CASO 2: Excedido (70 min antes) para probar el color rojo
                minutos_resta = 10 if random.random() > 0.3 else 70
                
                hora_estipulada = (dummy_date - timedelta(minutes=minutos_resta)).time()
                hora_llegada_est = (dummy_date + timedelta(minutes=60)).time()

                nuevo_form = FormularioSalida(
                    ci_nro=real.ci_nro,
                    fecha=real.fecha_marcacion,
                    hora_salida_estipulada=hora_estipulada,
                    hora_llegada_estipulada=hora_llegada_est,
                    motivo=f"Prueba {'Excedida' if minutos_resta > 60 else 'Normal'}",
                    destino="Test Auto",
                    estado=True,
                    fecha_creacion=datetime.now()
                )

                db.session.add(nuevo_form)
                contador += 1
                print(f"[CREADO] CI {real.ci_nro} - Diferencia: {minutos_resta} min")

        db.session.commit()
        print(f"--- FIN: {contador} formularios creados ---")

if __name__ == '__main__':
    cargar_datos_prueba()