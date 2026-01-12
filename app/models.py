from app import db
from flask_login import UserMixin, current_user
from datetime import datetime, date
import hashlib
import base64

#Tabla existente usuarios.
class Usuario(db.Model, UserMixin):
    __tablename__ = 'funcionarios'
    __table_args__ = {'schema': 'asistencias'}

    cedula = db.Column(db.String(20), primary_key=True)

    nombre = db.Column(db.String(30), nullable=False)
    apellido = db.Column(db.String(30), nullable=False)
    tipousuario = db.Column(db.String(1))
    password = db.Column(db.String(100))    

    def get_id(self):
        return self.cedula
    
    def check_password(self, raw_password):
        """Valida hash de Django (pbkdf2_sha256)"""

        if not self.password: return False
        try:
            algorithm, iterations, salt, hash_val = self.password.split('$', 3)
        except ValueError: return False

        if algorithm != 'pbkdf2_sha256': return False

        encrypted = hashlib.pbkdf2_hmac('sha256', raw_password.encode('utf-8'), salt.encode('utf-8'), int(iterations))
        encoded = base64.b64encode(encrypted).decode('ascii').strip()
        return encoded == hash_val
    
#Nueva tabla formulario_salida.
class FormularioSalida(db.Model):
    __tablename__ = 'formulario_salida'
    __table_args__ = {'schema': 'registro_intermedio'}

    id_salida = db.Column(db.Integer, primary_key=True)
    ci_nro = db.Column(db.String(20), nullable=False)
    fecha = db.Column(db.Date, nullable=False, default=date.today)
    hora_salida_estipulada = db.Column(db.Time, nullable=False)
    hora_llegada_estipulada = db.Column(db.Time, nullable=False)
    motivo = db.Column(db.String(100))
    destino = db.Column(db.String(100))
    estado = db.Column(db.Boolean, nullable=False)
    fecha_creacion = db.Column(db.DateTime, nullable=False, default=date.today())


    @classmethod
    def obtener_reporte_admin(cls, fecha_desde, fecha_hasta, cedula=None):
        """Retorna un reporte con todos los formularios enviados, tengan o no registrada marcaciones en un rango de fechas.
           Tambien se puede filtrar por cedula."""
        query = db.session.query(cls, MarcacionIntermediaGeneral, Usuario)\
        .outerjoin(MarcacionIntermediaGeneral, (cls.ci_nro == MarcacionIntermediaGeneral.ci_nro) & 
                   (cls.fecha == MarcacionIntermediaGeneral.fecha_marcacion))\
        .join(Usuario, cls.ci_nro == Usuario.cedula)\
        .filter(cls.fecha.between(fecha_desde, fecha_hasta))

        if cedula:
            query = query.filter(cls.ci_nro == cedula)

        return query.order_by(cls.fecha.desc(), cls.hora_salida_estipulada.asc()).all()
    
    @classmethod
    def obtener_reporte_usuario(cls, fecha_desde, fecha_hasta):
        """Retorna un reporte al usuario que muestra el resultado de sus formularios enviados y sus marcaciones"""
        query = db.session.query(cls, MarcacionIntermediaGeneral)\
        .outerjoin(MarcacionIntermediaGeneral, (cls.ci_nro == MarcacionIntermediaGeneral.ci_nro) &
                (cls.fecha == MarcacionIntermediaGeneral.fecha_marcacion))\
        .filter(cls.ci_nro == current_user.cedula, cls.fecha.between(fecha_desde, fecha_hasta))

        return query.order_by(cls.fecha.desc(), cls.hora_salida_estipulada.asc()).all()
    
#Vista existente marcaciones_intermedias_general (solo de lectura).
class MarcacionIntermediaGeneral(db.Model):
    __tablename__ = 'marcaciones_intermedias_general'
    __table_args__ = {'schema': 'registro_intermedio'}

    ci_nro = db.Column(db.String(20), primary_key=True)
    fecha_marcacion = db.Column(db.Date, primary_key=True)
    nombre = db.Column(db.String(30))
    apellido = db.Column(db.String(30))
    hora_marcacion_1 = db.Column(db.String)
    hora_marcacion_2 = db.Column(db.String)
    hora_marcacion_3 = db.Column(db.String)
    hora_marcacion_4 = db.Column(db.String)
    hora_marcacion_5 = db.Column(db.String)
    hora_marcacion_6 = db.Column(db.String)
    hora_marcacion_7 = db.Column(db.String)
    hora_marcacion_8 = db.Column(db.String)
    hora_marcacion_9 = db.Column(db.String)
    hora_marcacion_10 = db.Column(db.String)

    
    def get_marcaciones_list(self):
        """Retorna lista de objetos time, convirtiendo desde string"""
        marcaciones = []
        for i in range(1, 11):
            val_str = getattr(self, f'hora_marcacion_{i}')
            if val_str:
                try:
                    # Intentamos convertir el string "08:00:00" a objeto time.
                    # Ajusta el formato '%H:%M:%S' si tus datos son diferentes.
                    if len(val_str) >= 8: # Formato HH:MM:SS
                        time_obj = datetime.strptime(val_str, '%H:%M:%S').time()
                    else: # Formato HH:MM
                        time_obj = datetime.strptime(val_str, '%H:%M').time()
                    marcaciones.append(time_obj)
                except ValueError:
                    # Si hay un error de conversión, simplemente ignoramos esa marcación.
                    continue
        return marcaciones