
import os
import json
from datetime import date, timedelta
from typing import List, Optional
from dotenv import load_dotenv

from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, Date
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base

# --- Configuración de la Base de Datos ---
DATABASE_URL = os.getenv("DATABASE_URL") # Se leerá de las variables de entorno
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Modelos de la Base de Datos (SQLAlchemy) ---
class EquipmentDB(Base):
    __tablename__ = "equipment"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    category = Column(String, index=True)
    description = Column(String)
    price_per_day = Column(Float)
    image_url = Column(String, nullable=True)

class BookingDB(Base):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True, index=True)
    equipment_id = Column(Integer, index=True)
    customer_name = Column(String)
    customer_email = Column(String)
    start_date = Column(Date)
    end_date = Column(Date)
    total_price = Column(Float)
    status = Column(String, default="confirmed")

Base.metadata.create_all(bind=engine)

# --- Modelos de Datos (Pydantic) ---
class EquipmentBase(BaseModel):
    name: str
    category: str
    description: Optional[str] = None
    price_per_day: float
    image_url: Optional[str] = None

class EquipmentCreate(EquipmentBase): pass

class Equipment(EquipmentBase):
    id: int
    class Config: orm_mode = True

class BookingBase(BaseModel):
    equipment_id: int
    customer_name: str
    customer_email: str
    start_date: date
    end_date: date

class BookingCreate(BookingBase): pass

class Booking(BookingBase):
    id: int
    total_price: float
    status: str
    class Config: orm_mode = True

# --- Inicialización de la App FastAPI ---
app = FastAPI(title="Rental System API", version="1.0")

# --- CONFIGURACIÓN DE CORS ---
origins = ["*"]


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Dependencia para la Sesión de DB ---
def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

# --- Endpoints de la API ---
@app.get("/")
def read_root(): return {"message": "Bienvenido a la API del Sistema de Rentas"}

@app.post("/equipment/", response_model=Equipment) 
def create_equipment(equipment: EquipmentCreate, db: Session = Depends(get_db)):
    db_equipment = EquipmentDB(**equipment.dict())
    db.add(db_equipment)
    db.commit()
    db.refresh(db_equipment)
    return db_equipment

@app.get("/equipment/", response_model=List[Equipment])
def read_equipment_list(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(EquipmentDB).offset(skip).limit(limit).all()

@app.get("/equipment/{equipment_id}", response_model=Equipment)
def read_equipment(equipment_id: int, db: Session = Depends(get_db)):
    db_equipment = db.query(EquipmentDB).filter(EquipmentDB.id == equipment_id).first()
    if db_equipment is None: raise HTTPException(status_code=404, detail="Equipo no encontrado")
    return db_equipment

@app.post("/bookings/", response_model=Booking)
def create_booking(booking: BookingCreate, db: Session = Depends(get_db)):
    db_equipment = db.query(EquipmentDB).filter(EquipmentDB.id == booking.equipment_id).first()
    if not db_equipment: raise HTTPException(status_code=404, detail="El equipo solicitado no existe.")
    if booking.start_date > booking.end_date: raise HTTPException(status_code=400, detail="La fecha de inicio no puede ser posterior a la fecha de fin.")
    
    overlapping = db.query(BookingDB).filter(BookingDB.equipment_id == booking.equipment_id, BookingDB.end_date >= booking.start_date, BookingDB.start_date <= booking.end_date).count()
    if overlapping > 0: raise HTTPException(status_code=409, detail="El equipo no está disponible en las fechas seleccionadas.")

    num_days = (booking.end_date - booking.start_date).days + 1
    total_price = num_days * db_equipment.price_per_day
    db_booking = BookingDB(**booking.dict(), total_price=total_price, status="confirmed")
    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)
    return db_booking

@app.get("/bookings/", response_model=List[Booking])
def read_bookings(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(BookingDB).offset(skip).limit(limit).all()


import requests

# --- Endpoints para el Webhook de Instagram ---
load_dotenv()
VERIFY_TOKEN = os.getenv("INSTAGRAM_VERIFY_TOKEN", "un-token-muy-seguro")
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")

def send_instagram_message(recipient_id: str, message_text: str):
    """Envía un mensaje de texto al usuario de Instagram."""
    if not META_ACCESS_TOKEN:
        print(f"ADVERTENCIA: META_ACCESS_TOKEN no está configurado. Simulando envío a {recipient_id}: {message_text}")
        return

    url = f"https://graph.facebook.com/v18.0/me/messages"
    headers = {'Content-Type': 'application/json'}
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text},
        "messaging_type": "RESPONSE"
    }
    params = {"access_token": META_ACCESS_TOKEN}

    try:
        response = requests.post(url, headers=headers, params=params, json=payload)
        response.raise_for_status()
        print(f"Mensaje enviado exitosamente a {recipient_id}")
    except requests.exceptions.RequestException as e:
        print(f"Error al enviar mensaje: {e.response.text}")

@app.get("/webhook")
def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return Response(content=challenge, media_type="text/plain", status_code=200)
    raise HTTPException(status_code=403, detail="Error de verificación")

@app.post("/webhook")
async def receive_message(request: Request, db: Session = Depends(get_db)):
    body = await request.json()
    print(f"\n--- INCOMING WEBHOOK ---\n{json.dumps(body, indent=2)}\n-----------------------\n")
    try:
        message = body['entry'][0]['messaging'][0]
        sender_id = message['sender']['id']
        
        if 'message' in message and 'text' in message['message']:
            message_text = message['message']['text'].lower()
            response_text = "No entendí tu consulta. Un agente humano te responderá pronto."

            # Lógica de NLP y respuesta aquí...
            if any(keyword in message_text for keyword in ["precio", "costo", "cuánto"]):
                equipment_name_guess = [word for word in message_text.split() if db.query(EquipmentDB).filter(EquipmentDB.name.ilike(f"%{word}%")).first()]
                if equipment_name_guess:
                    equipment = db.query(EquipmentDB).filter(EquipmentDB.name.ilike(f"%{equipment_name_guess[0]}%")).first()
                    response_text = f"¡Hola! El precio de '{equipment.name}' es de ${equipment.price_per_day} por día."
                else:
                    response_text = "Por favor, dime el nombre del equipo para darte el precio."
            elif any(keyword in message_text for keyword in ["disponible", "disponibilidad"]):
                response_text = "Puedes ver la disponibilidad de todos nuestros equipos en tiempo real en el calendario de nuestro sitio web."
            elif any(keyword in message_text for keyword in ["hola", "info", "saludos"]):
                response_text = "¡Hola! Gracias por contactarnos. Puedes ver nuestro catálogo, precios y disponibilidad en nuestro sitio web."

            # Enviar la respuesta
            send_instagram_message(sender_id, response_text)

    except (KeyError, IndexError, TypeError) as e:
        print(f"Error al procesar el webhook: {e}")
        pass
    return Response(status_code=200)

