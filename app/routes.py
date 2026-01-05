from app import app, db
from app.function import obtener_hora_cercana
from app.models import FormularioSalida, Usuario, MarcacionIntermediaGeneral
from app.forms import CargarSalidaForm, LoginForm
from flask import render_template, redirect, url_for, flash, request
from flask_login import current_user, login_required, logout_user, login_user
from datetime import date, datetime
from urllib.parse import urlparse
import sqlalchemy as sa

@app.route('/')
@app.route('/index')
@login_required
def index():
    return render_template('index.html')

#RUTA PARA QUE EL FUNCIONARIO CARGUE EL FORMULARIO DE SALIDA DENTRO DEL HORARIO LABORAL.
@app.route('/formulario_salidas', methods=['GET','POST'])
@login_required
def formulario_salidas():
    form = CargarSalidaForm()

    if form.validate_on_submit():
        formulario = FormularioSalida(
            ci_nro = current_user.cedula,
            fecha = date.today(),
            hora_salida_estipulada=form.horario_salida.data,
            hora_llegada_estipulada=form.horario_llegada.data,
            motivo = form.motivo.data,
            destino = form.destino.data,
            estado = False,
            fecha_creacion = datetime.now()
        )
        db.session.add(formulario)
        db.session.commit()

        flash('Formulario enviado exitosamente, podrá revisar el registro mañana.', 'success')

        return redirect(url_for('index'))
    return render_template('formulario_salidas.html', form=form)

#RUTA PARA QUE EL ADMINISTRADOR VEA EL REGISTRO DE SALIDAS DENTRO DEL HORARIO LABORAL.
@app.route('/registro_salidas', methods=['GET'])
@login_required
def registro_salidas():
    #Acceso solo permitido a administradores.

    fecha_desde_str = request.args.get('fecha_desde', '')
    fecha_hasta_str = request.args.get('fecha_hasta', '')
    cedula_filtro = request.args.get('cedula', '')# Opcional: filtro por CI

    #Si no hay fechas mostramos la tabla vacía al principio.
    if not fecha_desde_str or not fecha_hasta_str:
        return render_template('registro_salidas.html', registros=[],
                                fecha_desde='', fecha_hasta='', cedula_filtro='')
    
    try:
        fecha_desde_obj = datetime.strptime(fecha_desde_str, '%Y-%m-%d').date()
        fecha_hasta_obj = datetime.strptime(fecha_hasta_str, '%Y-%m-%d').date()

        if fecha_desde_obj > fecha_hasta_obj:
            flash('La fecha desde no puede ser mayor a la fecha hasta', 'danger')
            return render_template('registro_salidas.html')
        
        #QUERY COMPLETA.
        #1-FormularioSalida (es nuestra base, para que exista registro de una salida se debe completar un formulario).
        #2-MarcacionIntermediaGeneral (OUTER JOIN para ver si marcó o no).
        #3-Usuario (Join normal para obtener nombre y apellido siempre).
        query = db.session.query(FormularioSalida, MarcacionIntermediaGeneral, Usuario)\
            .outerjoin(MarcacionIntermediaGeneral, (FormularioSalida.ci_nro == MarcacionIntermediaGeneral.ci_nro) &
                        (FormularioSalida.fecha == MarcacionIntermediaGeneral.fecha_marcacion))\
            .join(Usuario, FormularioSalida.ci_nro == Usuario.cedula)\
            .filter(FormularioSalida.fecha.between(fecha_desde_obj, fecha_hasta_obj))
        
        #Aplicar filtro de cédula si el admin lo escribió.
        if cedula_filtro:
            query = query.filter(FormularioSalida.ci_nro == cedula_filtro)
        
        resultados = query.order_by(FormularioSalida.fecha.desc(), FormularioSalida.hora_salida_estipulada.desc()).all()

        datos_finales = []

        stats = {}

        for formulario, marcacion, usuario in resultados:

            hora_salida_cercana = None
            hora_llegada_cercana = None

            #Clases por defecto grises.
            clase_salida = "text-muted"
            clase_llegada = "text-muted"

            if marcacion:
                todas_las_horas = marcacion.get_marcaciones_list()
                horas_disponibles = list(todas_las_horas)  # Hacemos una copia para manipular

                # ---- SALIDA ----
                hora_salida_cercana = obtener_hora_cercana(formulario.hora_salida_estipulada, todas_las_horas)
                if hora_salida_cercana:
                    dummy = date.today()
                    dt_est = datetime.combine(dummy, formulario.hora_salida_estipulada)
                    dt_real = datetime.combine(dummy, hora_salida_cercana)
                    diff_minutos = abs((dt_real - dt_est).total_seconds() / 60)

                    if diff_minutos > 59:
                        clase_salida = "text-danger fw-bold"
                    elif diff_minutos <= 59 and diff_minutos >= 15:
                        clase_salida = "text-warning fw-bold"
                    else:
                        clase_salida = "text-success fw-bold"
                
                # ---- LLEGADA ----
                hora_llegada_cercana = obtener_hora_cercana(formulario.hora_llegada_estipulada, todas_las_horas)
                if hora_llegada_cercana and hora_llegada_cercana != hora_salida_cercana:
                    dummy = date.today()
                    dt_est = datetime.combine(dummy, formulario.hora_llegada_estipulada)
                    dt_real = datetime.combine(dummy, hora_llegada_cercana)
                    diff_minutos = abs((dt_real - dt_est).total_seconds() / 60)
                    if diff_minutos > 59:
                        clase_llegada = "text-danger fw-bold"
                    elif diff_minutos <= 59 and diff_minutos >= 15:
                        clase_llegada = "text-warning fw-bold"
                    else:
                        clase_llegada = "text-success fw-bold"
                else:
                    hora_llegada_cercana = None  # Aseguramos que sea None si no es válida
                    clase_llegada = "text-danger fw-bold"  
            
            #Inicializamos las estadisticas de un funcionario si este todavia no está.
            cedula = usuario.cedula
            if cedula not in stats:
                stats[cedula] = {
                    'nombre': f"{usuario.nombre} {usuario.apellido}",
                    'ci_nro': cedula,
                    'total': 0,
                    'cumplio': 0,
                    'alerta': 0,
                    'incumplio': 0
                }

            #Sumamos 1 correspondiente al formulario procesado.
            stats[cedula]['total'] += 1

            #Evaluamos cumplimiento.
            if clase_llegada == "text-success fw-bold":
                stats[cedula]['cumplio'] += 1
            elif clase_llegada == "text-warning fw-bold":
                stats[cedula]['alerta'] += 1
            else:
                stats[cedula]['incumplio'] += 1
            
            if clase_salida == "text-success fw-bold":
                stats[cedula]['cumplio'] += 1
            elif clase_salida == "text-warning fw-bold":
                stats[cedula]['alerta'] += 1
            else:
                stats[cedula]['incumplio'] += 1

            datos_finales.append(
                {
                    'nombre_completo': f"{usuario.nombre} {usuario.apellido}",
                    'ci_nro': usuario.cedula,
                    'fecha': formulario.fecha.strftime('%d-%m-%Y'),
                    'motivo': formulario.motivo,
                    'destino': formulario.destino,
                    'hora_salida_estipulada': formulario.hora_salida_estipulada.strftime('%H:%M'),
                    'hora_llegada_estipulada': formulario.hora_llegada_estipulada.strftime('%H:%M'),
                    'hora_salida_cercana': hora_salida_cercana.strftime('%H:%M') if hora_salida_cercana else '-',
                    'hora_llegada_cercana': hora_llegada_cercana.strftime('%H:%M') if hora_llegada_cercana else '-',
                    'clase_salida': clase_salida,
                    'clase_llegada': clase_llegada
                }
            )
        resumen_estadistico = list(stats.values())
        return render_template('registro_salidas.html', registros=datos_finales,
                                fecha_desde=fecha_desde_str, fecha_hasta=fecha_hasta_str,
                                cedula_filtro=cedula_filtro, resumen=resumen_estadistico)
    except ValueError:
        flash('Formato de fecha inválido', 'danger')
        return redirect(url_for('index'))


#RUTA PARA QUE EL FUNCIONARIO VEA SUS PROPIAS SALIDAS DENTRO DEL HORARIO LABORAL REGISTRADAS.
@app.route('/registro_salidas_funcionario', methods=['GET'])
@login_required
def registro_salidas_funcionario():
        fecha_desde_str = request.args.get('fecha_desde', '')
        fecha_hasta_str = request.args.get('fecha_hasta', '')

        if not fecha_desde_str or not fecha_hasta_str:
            return render_template('registro_salidas_funcionario.html', registros=[],
                                    fecha_desde='', fecha_hasta='')

        try:
            fecha_desde_obj = datetime.strptime(fecha_desde_str, '%Y-%m-%d').date()
            fecha_hasta_obj = datetime.strptime(fecha_hasta_str, '%Y-%m-%d').date()
            if fecha_desde_obj > fecha_hasta_obj:
                flash('La fecha desde no puede ser mayor a la fecha hasta', 'danger')
                return render_template('registro_salidas_funcionario.html', registros=[])

            #Queremos ver el formulario siempre, aunque no haya marcaciones todavia.
            #Hacemos un outer join empezando por los formularios.
            resultados = db.session.query(FormularioSalida, MarcacionIntermediaGeneral).outerjoin(
                MarcacionIntermediaGeneral, (MarcacionIntermediaGeneral.ci_nro == FormularioSalida.ci_nro) &
                (MarcacionIntermediaGeneral.fecha_marcacion == FormularioSalida.fecha)).filter(
                    FormularioSalida.ci_nro == current_user.cedula,
                    FormularioSalida.fecha.between(fecha_desde_obj, fecha_hasta_obj)
                ).order_by(FormularioSalida.fecha.desc(), FormularioSalida.hora_salida_estipulada.desc()).all()
            
            datos_finales = []

            for formulario, marcacion in resultados:
                #Valores por defecto si no hay marcacion (caso del día actual sin migrar).
                hora_salida_cercana = None
                hora_llegada_cercana = None

                #Variables para controlar el color (clase CSS).
                clase_salida = "text_muted"
                clase_llegada = "text_muted"

                if marcacion:
                    #Si ya se migraron los datos, calculamos.
                    todas_las_horas = marcacion.get_marcaciones_list()
                    hora_salida_cercana = obtener_hora_cercana(formulario.hora_salida_estipulada, todas_las_horas)
                    if hora_salida_cercana:
                        #Calcular la diferencia en minutos
                        dummy = date.today()
                        dt_est = datetime.combine(dummy, formulario.hora_salida_estipulada)
                        dt_real = datetime.combine(dummy, hora_salida_cercana)
                        diff_minutos = abs((dt_real - dt_est).total_seconds() / 60)

                        if diff_minutos > 59:
                            clase_salida = "text-danger fw-bold"
                        elif diff_minutos <= 59 and diff_minutos >= 15:
                            clase_salida = "text-warning fw-bold"
                        else:
                            clase_salida = "text-success fw-bold"

                    hora_llegada_cercana = obtener_hora_cercana(formulario.hora_llegada_estipulada, todas_las_horas)
                    if hora_llegada_cercana:
                        dummy = date.today()
                        dt_est = datetime.combine(dummy, formulario.hora_llegada_estipulada)
                        dt_real = datetime.combine(dummy, hora_llegada_cercana)
                        diff_minutos = abs((dt_real - dt_est).total_seconds() / 60)
    
                        if diff_minutos > 59:
                            clase_llegada = "text-danger fw-bold"
                        elif diff_minutos <= 59 and diff_minutos >= 15:
                            clase_llegada = "text-warning fw-bold"
                        else:
                            clase_llegada = "text-success fw-bold"

                    if hora_salida_cercana == hora_llegada_cercana:
                        clase_salida = "text-danger fw-bold"
                        clase_llegada = "text-danger fw-bold"
                                       
                datos_finales.append(
                    {
                        'fecha': formulario.fecha.strftime('%Y-%m-%d'),
                        'motivo': formulario.motivo,
                        'destino': formulario.destino,
                        'hora_salida_estipulada': formulario.hora_salida_estipulada.strftime('%H:%M'),
                        'hora_llegada_estipulada': formulario.hora_llegada_estipulada.strftime('%H:%M'),
                        'hora_salida_cercana': hora_salida_cercana.strftime('%H:%M') if hora_salida_cercana else '-',
                        'hora_llegada_cercana': hora_llegada_cercana.strftime('%H:%M') if hora_llegada_cercana else '-',
                        'clase_salida': clase_salida,
                        'clase_llegada': clase_llegada
                    }
                )
            return render_template('registro_salidas_funcionario.html', registros=datos_finales,
                                    fecha_desde=fecha_desde_str, fecha_hasta=fecha_hasta_str)

        except ValueError:
            return 'Formato de fecha invalido', 400


#RUTAS PARA INICIAR Y CERRAR SESIÓN.
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        #Buscamos el usuario por cedula en la tabla de asistencias.
        user = Usuario.query.filter_by(cedula=form.ci.data).first()

        #Usamos nuestra funcion personalizada check_password para validar la contraseña.
        if user and user.check_password(form.password.data):
            login_user(user)
            flash('Inicio de sesión exitoso.', 'success')

            next_page = request.args.get('next')
            if not next_page or urlparse(next_page).netloc != '':
                next_page = url_for('index')
            return redirect(next_page)  
        else:
            flash('Cédula o contraseña incorrecta', 'danger')    

    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión correctamente.', 'success')
    return redirect(url_for('login'))


#RUTA PARA VER ESTADISTICAS.
@app.route('/estadisticas', methods=['GET'])
@login_required
def estadisticas():
    datos = {}

    total_salidas = db.session.query(sa.func.count(FormularioSalida.id_salida)).scalar()

    return render_template('estadisticas.html')
    