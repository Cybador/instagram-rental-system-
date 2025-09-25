
import os
import random
from datetime import datetime
import requests

# --- Configuración ---
API_BASE_URL = "http://localhost:8000"
# En un caso real, estos tokens vendrían de variables de entorno
INSTAGRAM_BUSINESS_ACCOUNT_ID = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID")
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")

# --- Lógica del Publicador ---

def get_equipment_from_api(category: str = None) -> list:
    """Obtiene equipos de nuestra API, opcionalmente filtrados por categoría."""
    try:
        response = requests.get(f"{API_BASE_URL}/equipment/")
        response.raise_for_status()
        all_equipment = response.json()
        if category:
            return [eq for eq in all_equipment if eq['category'].lower() == category.lower()]
        return all_equipment
    except requests.exceptions.RequestException as e:
        print(f"Error al conectar con la API local: {e}")
        return []

def generate_caption(equipment: dict) -> str:
    """Genera un texto atractivo usando una plantilla."""
    templates = [
        f"¡Equipo disponible para tu próximo proyecto! Renta nuestro/a {equipment['name']} y lleva tu producción al siguiente nivel. #RentaDeEquipo #{equipment['category'].replace(' ', '')} #ProduccionAudiovisual",
        f"¿Necesitas un/a {equipment['name']}? ¡Lo tenemos! Calidad profesional a tu alcance. Visita nuestro sitio para más detalles. #Cineastas #{equipment['name'].replace(' ', '')}",
        f"Eleva la calidad de tu trabajo con nuestro/a {equipment['name']}. Disponible para renta por día. ¡Reserva ahora! #EquipoProfesional #{equipment['category'].replace(' ', '')}"
    ]
    return random.choice(templates)

def post_to_instagram(image_url: str, caption: str):
    """
    Simula el proceso de publicación en Instagram a través de la API de Meta.
    Este es un proceso de 2 pasos: 1) crear el contenedor, 2) publicar el contenedor.
    """
    print("--- INICIANDO PUBLICACIÓN EN INSTAGRAM ---")
    print(f"Cuenta de Instagram ID: {INSTAGRAM_BUSINESS_ACCOUNT_ID}")
    print(f"URL de la imagen: {image_url}")
    print(f"Texto a publicar: {caption}")

    if not INSTAGRAM_BUSINESS_ACCOUNT_ID or not META_ACCESS_TOKEN:
        print("\nERROR: Las variables de entorno INSTAGRAM_BUSINESS_ACCOUNT_ID y META_ACCESS_TOKEN no están configuradas.")
        print("La publicación no se puede realizar. Este es un paso de simulación.")
        return

    # Paso 1: Subir la imagen y crear el contenedor de medios
    # La API de Instagram requiere una URL pública para la imagen.
    creation_url = f"https://graph.facebook.com/v18.0/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media"
    creation_payload = {
        'image_url': image_url,
        'caption': caption,
        'access_token': META_ACCESS_TOKEN
    }
    try:
        creation_response = requests.post(creation_url, json=creation_payload)
        creation_response.raise_for_status()
        creation_id = creation_response.json()['id']
        print(f"Contenedor de medios creado con ID: {creation_id}")
    except requests.exceptions.RequestException as e:
        print(f"Error al crear el contenedor de medios: {e}")
        print(f"Respuesta del servidor: {e.response.text}")
        return

    # Paso 2: Publicar el contenedor de medios
    publish_url = f"https://graph.facebook.com/v18.0/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media_publish"
    publish_payload = {
        'creation_id': creation_id,
        'access_token': META_ACCESS_TOKEN
    }
    try:
        publish_response = requests.post(publish_url, json=publish_payload)
        publish_response.raise_for_status()
        media_id = publish_response.json()['id']
        print(f"¡ÉXITO! Publicado en Instagram con el ID de medio: {media_id}")
    except requests.exceptions.RequestException as e:
        print(f"Error al publicar el contenedor: {e}")
        print(f"Respuesta del servidor: {e.response.text}")


if __name__ == "__main__":
    # Estrategia de publicación por temas (Plan Intermedio)
    day_of_week = datetime.now().weekday() # Lunes=0, Martes=1, ...
    categories = ["Cámaras", "Lentes", "Iluminación", "Sonido", "Accesorios", "Cámaras", "Lentes"]
    today_category = categories[day_of_week]

    print(f"Hoy es {datetime.now().strftime('%A')}. Categoría del día: {today_category}")

    # Obtener equipos de la categoría de hoy
    equipment_to_post_from = get_equipment_from_api(category=today_category)

    if not equipment_to_post_from:
        print(f"No se encontraron equipos en la categoría '{today_category}'. Intentando con todos los equipos.")
        equipment_to_post_from = get_equipment_from_api()

    if equipment_to_post_from:
        # Elegir un equipo al azar de la lista
        selected_equipment = random.choice(equipment_to_post_from)
        
        # Generar el caption
        caption_text = generate_caption(selected_equipment)
        
        # Simular la publicación
        # La URL de la imagen debe ser accesible públicamente por los servidores de Meta
        image_url = selected_equipment.get('image_url')
        if image_url:
            post_to_instagram(image_url=image_url, caption=caption_text)
        else:
            print(f"El equipo '{selected_equipment['name']}' no tiene una URL de imagen para publicar.")
    else:
        print("No se encontraron equipos en la base de datos para publicar.")
