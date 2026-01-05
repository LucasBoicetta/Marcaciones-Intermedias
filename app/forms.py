from flask_wtf import FlaskForm
from wtforms import StringField, DateTimeField, SubmitField, TimeField
from wtforms.validators import DataRequired

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
