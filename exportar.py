import csv
from app.core.database import SessionLocal
from app.db.models import Medicion

db = SessionLocal()
mediciones = db.query(Medicion).all()

with open('datos_sensores.csv', mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    writer.writerow(['voltaje_v', 'corriente_a', 'potencia_w', 'label'])
    
    for m in mediciones:
        v = m.voltaje_v
        i = m.corriente_a
        p = m.potencia_w
        
        if p > 500 or i > 4.5:
            label = "sobrecarga"
        elif p > 250:
            label = "alto"
        elif p > 50:
            label = "normal"
        else:
            label = "standby"
            
        writer.writerow([v, i, p, label])

print("Archivo datos_sensores.csv generado con exito")
db.close()
