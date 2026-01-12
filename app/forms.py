from flask_wtf import FlaskForm
from wtforms import StringField, DateField, SubmitField, TimeField
from wtforms.validators import DataRequired, Optional

class CargarSalidaForm(FlaskForm):
    horario_salida = TimeField('Horario de salida', validators=[DataRequired()])
    horario_llegada = TimeField('Horario de llegada', validators=[DataRequired()])
    motivo = StringField('Motivo de la salida')
    destino = StringField('Destino de la salida', validators=[DataRequired()])
    submit = SubmitField('Guardar')


class LoginForm(FlaskForm):
    ci = StringField('Cédula de Identidad', validators=[DataRequired()])
    password = StringField('Contraseña', validators=[DataRequired()])
    submit = SubmitField('Iniciar Sesión')


class FiltroReporteForm(FlaskForm):
    #Usamos meta para desactivar CSRF solo en este form.
    class Meta:
        csrf = False

    fecha_desde = DateField('Fecha desde', format='%Y-%m-%d', validators=[DataRequired()])
    fecha_hasta = DateField('Fecha hasta', format='%Y-%m-%d', validators=[DataRequired()])
    cedula = StringField('Cédula de Identidad (opcional)', validators=[Optional()])
    submit = SubmitField('Generar Reporte')

    def validar_fechas(self):
        """Validación personalizada para el rango"""
        if self.fecha_desde.data and self.fecha_hasta.data:
            if self.fecha_desde.data > self.fecha_hasta.data:
                self.fecha_desde.errors.append('La fecha desde no puede ser mayor a la fecha hasta')
                return False
        return True