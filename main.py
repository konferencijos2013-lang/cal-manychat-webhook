from fastapi import FastAPI, Request, HTTPException
import requests
import os
from datetime import datetime

app = FastAPI(title="Cal.com → ManyChat Webhook (Lietuviškai)")

@app.post("/webhook")
async def handle_webhook(request: Request):
    try:
        data = await request.json()
        event_type = data.get("triggerEvent")
        payload = data.get("payload", {})

        print("✅ --- START WEBHOOK ---")
        print(f"📌 Įvykis: {event_type}")

        # PING testas — Cal.com siunčia be payload
        if event_type == "PING":
            print("🏓 Ping testas priimtas")
            return {"success": True, "message": "Ping OK"}

        # Ištraukiam el. paštą
        attendees = payload.get("attendees", [])
        email = attendees[0].get("email") if attendees else None
        if not email:
            print("❌ Nerastas el. paštas")
            raise HTTPException(status_code=400, detail="Missing email")

        # ✅ ManyChat raktas — čia matysime, ar jis įkeltas
        api_key = os.getenv("MANYCHAT_API_KEY", "").strip()
        print(f"🔑 Raktas (pirmi 10 simb.): {api_key[:10]}..." if api_key else "❌ RAKTAS NEĮKELTAS!")

        if not api_key or len(api_key) < 20:
            raise HTTPException(status_code=500, detail="ManyChat API raktas neįkeltas")

        # Formatuojam laiką lietuviškai
        start_time = payload.get("startTime")
        if start_time:
            dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            formatted = dt.astimezone().strftime("%Y %B %d, %H:%M")
        else:
            formatted = "Nenurodyta"

        meeting_link = payload.get("metadata", {}).get("videoCallUrl", "Bus pateikta vėliau")

        # Siunčiam į ManyChat
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        fields = {}
        if event_type == "BOOKING_CREATED":
            fields = {
                "Google_Meet_Nuoroda": meeting_link,
                "Konsultacijos_Statusas": "PATVIRTINTA",
                "Rezervacijos_Data_Laikas_text": formatted
            }
        elif event_type == "BOOKING_CANCELLED":
            fields = {"Konsultacijos_Statusas": "ATSAUKTA"}
        else:
            return {"success": True, "message": f"Ignoruojama: {event_type}"}

        for name, value in fields.items():
            res = requests.post(
                "https://api.manychat.com/v2/subscriber/updateProfile",
                json={"external_id": email, "custom_fields": {name: value}},
                headers=headers
            )
            if res.status_code == 200:
                print(f"✅ ManyChat: {name}")
            else:
                print(f"❌ ManyChat klaida ({name}): {res.status_code} — {res.text}")

        return {"success": True, "message": "✅ Sėkmingai išsiųsta"}

    except Exception as e:
        print(f"💥 Klaida: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
