from app import app, db
from app.services import obtener_reporte_salidas_procesado, obtener_reporte_salidas_funcionario
from app.models import FormularioSalida, Usuario, MarcacionIntermediaGeneral
from app.forms import CargarSalidaForm, LoginForm, FiltroReporteForm
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
#RUTA PARA QUE EL ADMINISTRADOR VEA LAS ESTADISTICAS TOTALES DE SALIDAS DENTRO DEL HORARIO LABORAL.
@app.route('/registro_salidas', methods=['GET'])
@login_required
def registro_salidas():
    #Le pasamos request.args al formulario (para que mantenga los valores en la URL)
    form = FiltroReporteForm(request.args)

    #Valores por defecto para no mostrar un reporte con tablas vacías.
    if not request.args:
        return render_template('registro_salidas.html', registros=[],
                                form=form, resumen=[])
    
    #Cuando el formulario usa metodos get se utiliza el form.validate()
    if form.validate() and form.validar_fechas():
        try:
            #--- Llamada al servicio ---
            registros, resumen_estadistico = obtener_reporte_salidas_procesado(
                form.fecha_desde.data, form.fecha_hasta.data, form.cedula.data or None)
        
            return render_template('registro_salidas.html', registros=registros,
                                form=form, resumen=resumen_estadistico)
        except Exception as e:
            #Manejo general de errores inesperados. Guarda el error en el log del app.
            app.logger.error(f'Error generando reporte: {e}')
            flash('Ocurrió un error al generar el reporte. Intente nuevamente.', 'danger')
    
    #Si llega hasta acá es porque validate() falló o hubo una excepción.
    return render_template('registro_salidas.html', registros=[],
                                form=form, resumen=[])

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

            #--- Llamada al servicio ---
            registro = obtener_reporte_salidas_funcionario(fecha_desde_obj, fecha_hasta_obj)

            return render_template('registro_salidas_funcionario.html', registros=registro,
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

