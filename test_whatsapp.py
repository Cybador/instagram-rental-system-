
import requests
import json

# Tu API Key de prueba de 360dialog
API_KEY = "T7RHYX_sandbox"

# ATENCIÓN: Reemplaza esta cadena con tu número de WhatsApp
# Debe estar en formato internacional, con el signo + y el código de país.
# Ejemplo: "+5215512345678"
RECIPIENT_NUMBER = "+525560750993"

# La URL del sandbox de 360dialog
URL = "https://waba-sandbox.360dialog.io/v1/messages"

headers = {
    "D360-API-KEY": API_KEY,
    "Content-Type": "application/json"
}

data = {
    "to": RECIPIENT_NUMBER,
    "type": "text",
    "text": {
        "body": "Hola desde la API de Gemini! Si recibes esto, la conexión funciona. 🎉"
    }
}

# Validar que el número de teléfono ha sido reemplazado
if RECIPIENT_NUMBER == "TU_NUMERO_DE_WHATSAPP":
    print("Error: Por favor, abre el archivo 'test_whatsapp.py' y reemplaza 'TU_NUMERO_DE_WHATSAPP' con tu número de teléfono real.")
else:
    print("Enviando mensaje a:", RECIPIENT_NUMBER)
    response = requests.post(URL, data=json.dumps(data), headers=headers)
    
    print("\nRespuesta del servidor:")
    print("Status Code:", response.status_code)
    print("Response Body:", response.json())

