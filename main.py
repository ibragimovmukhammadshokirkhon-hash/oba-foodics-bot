import asyncio
import os
import requests
from fastapi import FastAPI, Request

app = FastAPI()

FOODICS_TOKEN = "949776_Telegram Order Notifier Bot_prd_token"
TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # @BotFather bergandek token
TELEGRAM_CHAT_ID = "YOUR_CHANNEL_OR_GROUP_ID_HERE"  # Kanal ID'si (-100...)


def send_telegram(text: str):
  url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
  payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
  try:
    requests.post(url, json=payload, timeout=5)
  except Exception as e:
    print(f"Telegram error: {e}")


def register_foodics_webhooks(render_url: str):
  endpoint = "https://api.foodics.com/v5/webhooks"
  headers = {
      "Authorization": f"Bearer {FOODICS_TOKEN}",
      "Content-Type": "application/json",
  }
  events = ["order.created", "order.closed", "payment.created"]

  for event in events:
    payload = {"url": f"{render_url}/webhook", "event": event}
    try:
      res = requests.post(endpoint, json=payload, headers=headers, timeout=5)
      print(f"Webhook {event} status:", res.status_code)
    except Exception as e:
      print(f"Webhook register error ({event}): {e}")


@app.on_event("startup")
async def startup_event():
  render_host = os.getenv("RENDER_EXTERNAL_URL")
  if render_host:
    register_foodics_webhooks(render_host)


@app.post("/webhook")
async def foodics_webhook(request: Request):
  data = await request.json()
  event = data.get("event")
  order = data.get("data", {})

  table = order.get("table", {})
  table_name = table.get("name", "Takeaway / Delivery") if table else "Takeaway"
  order_ref = order.get("reference", "—")
  total_price = order.get("total_price", 0)

  products = order.get("products", [])
  items_text = ""
  for item in products:
    name = item.get("name", "")
    qty = item.get("quantity", 1)
    price = item.get("total_price", 0)
    items_text += f"• <b>{name}</b> — {qty}x ({price} AED)\n"

  if event == "order.created":
    msg = (
        f"🔔 <b>YANGI STOL / BUYURTMA OCHILDI</b>\n\n"
        f"📍 <b>Stol:</b> {table_name}\n"
        f"🧾 <b>Order:</b> #{order_ref}\n\n"
        f"🍽 <b>Tarkibi:</b>\n{items_text}"
    )
    send_telegram(msg)

  elif event in ["order.closed", "payment.created"]:
    msg = (
        f"✅ <b>TO'LOV QILINDI / STOL YOPILDI</b>\n\n"
        f"📍 <b>Stol:</b> {table_name}\n"
        f"🧾 <b>Order:</b> #{order_ref}\n"
        f"💰 <b>Jami to'lov:</b> {total_price} AED\n\n"
        f"🍽 <b>Yeyilgan taomlar:</b>\n{items_text}"
    )
    send_telegram(msg)

  return {"status": "ok"}
