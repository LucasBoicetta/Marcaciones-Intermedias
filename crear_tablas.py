from app import app, db

with app.app_context():
    print("Creando tablas nuevas...")
    #Esto solo crea las tablas que NO existen en la BD.
    db.create_all()
    print("Tablas creadas exitosamente.")