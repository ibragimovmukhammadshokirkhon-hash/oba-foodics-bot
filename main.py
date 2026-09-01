
import asyncio
import os
import requests
from fastapi import FastAPI, Request

app = FastAPI()

FOODICS_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiI5MGQ1YTcxOC1lMzBkLTQ5ODYtODY4Ni0wNjdlZDBkMzdkMGUiLCJqdGkiOiI2NmFjYjEwNzZiMWVhZThlMDE2ODk5NjhiODVjOGQxODgyODAwNjUwOWE0OTg5NWExNGQyNjFjMmE5YzY1MmJmZDJjYTk2ZWJlNzVlYWZlNSIsImlhdCI6MTc4NzY1OTA3OS42MDQ0MDMsIm5iZiI6MTc4NzY1OTA3OS42MDQ0MDMsImV4cCI6MTk0NTQyNTQ3OS41MjExNzUsInN1YiI6IjlkZWQ4NjBhLTkyZGQtNGU4NS1iYjM1LTMwZjcxOGRlOTgyMCIsInNjb3BlcyI6WyJnZW5lcmFsLnJlYWQiLCJvcmRlcnMubGlzdCJdLCJidXNpbmVzcyI6IjlkZWQ4NjBhLTkzMzQtNDFlYy1iOTY4LWVmMDJkMmEzMDM1YiIsInJlZmVyZW5jZSI6Ijk0OTc3NiJ9.0UAgB9C7V1dblaKrw29yDac8xwuFm7CjOeN6U8GYzXa0rmPRSqb1UVwykvvXUYbeV9Guy9b4Ar2SnDDhOp_2JAW8sDpG2co7b65OElnT3bAMOB-MWlXtwllYmZ2d6-g6X3jmvanlzaqtQ9_VEgsK0NztZgINFuv0NN9eJh3-namzuVLOzm2IB1_bQ7taZxYvenuUPjOuWIh4lupIc1LpYQaxcvhAoNhG-oOfjI7zVBu_fTAxyZ75mXuvSk0We-RVYyELIEetgWxWs_RDBJ4hN4Xr-sZrQ8sdngIYrnCI05gQf0eeKmK1mAMPbbzXEOBsM3ufiEbcRw5QXmywM9LuatdP1WlQXs7lpGeDGpKktygr51xZbywzdH5WL2KKbM3U0jlf9_0zkpbtHTWN5kHpkyMGvPf9eWHmWUzlT4DWHAJOoj9VoEZrTO1_r6Hz_o3HjNRIAcT7ZNnpU-9_l0-tx8b_iOOFGrY2Lz_3WKBK5rMqkKsSoknYwU9AK1LOTF2NBGMV_JXg6BuEI6Fbpgx17mp3Xm4txnTY3hV7Y9uX-f7LKbHnqF0STx5wo2MBxpy3GNCYPEHy9SHhuKBKffMcr3F4HUK2Kz4lIe4XuX5qcp-Odv7yYV_Q9my1D99WudiGm5izDi4yST8iBiEY1sQ2vRVU748hS6XYocqEc1WGrno"
TELEGRAM_BOT_TOKEN = "8853263842:AAGZnt5pUEoH3WdjTKM2AP9fwdzCHgdoKm8"
TELEGRAM_CHAT_ID = "-1004471118381"


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
  events = ["order.created", "order.closed", "payment.created", "order.updated"]

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
  raw_order = data.get("data", {})

  order_id = raw_order.get("id")
  if not order_id:
    return {"status": "no order id"}

  # Foodics API'dan to'liq ma'lumotlarni yuklab olish
  headers = {"Authorization": f"Bearer {FOODICS_TOKEN}"}
  url = f"https://api.foodics.com/v5/orders/{order_id}?include=products,table,user,payments,payments.payment_method"

  order = raw_order
  try:
    res = requests.get(url, headers=headers, timeout=5)
    if res.status_code == 200:
      order = res.json().get("data", {})
  except Exception as e:
    print(f"Order details error: {e}")

  # 1. Order Nomeri
  order_ref = (
      order.get("number")
      or order.get("reference")
      or raw_order.get("reference", "—")
  )

  # 2. Xodim (Xizmatchi / Kassir) Ismi
  user = order.get("user")
  staff_name = (
      user.get("name", "Xodim") if isinstance(user, dict) else "Xodim"
  )

  # 3. Stol nomi
  table = order.get("table")
  if table and isinstance(table, dict):
    table_name = table.get("name", "Dine In")
  else:
    table_name = "Takeaway / Delivery"

  total_price = order.get("total_price", 0)

  # 4. Mahsulotlar Ro'yxati va Narxlari
  products = order.get("products", [])
  items_text = ""
  if products:
    for item in products:
      p_obj = item.get("product", {})
      p_name = (
          p_obj.get("name")
          if isinstance(p_obj, dict)
          else item.get("name", "Mahsulot")
      )
      p_qty = item.get("quantity", 1)
      p_price = item.get("unit_price", item.get("total_price", 0))
      items_text += f"• <b>{p_name}</b> — {p_qty}x ({p_price} AED)\n"
  else:
    items_text = "<i>Mahsulotlar biriktirilmagan</i>\n"

  # 5. To'lov Turi va Summalari
  payments = order.get("payments", [])
  payment_text = ""
  if payments:
    for pay in payments:
      pay_method = pay.get("payment_method", {})
      method_name = (
          pay_method.get("name", "Naqd/Karta")
          if isinstance(pay_method, dict)
          else "To'lov"
      )
      pay_amount = pay.get("amount", 0)
      payment_text += f"💳 <b>{method_name}:</b> {pay_amount} AED\n"
  else:
    payment_text = f"💳 <b>To'lov:</b> {total_price} AED\n"

  # Telegram Xabarnomasi
  if event == "order.created":
    msg = (
        f"🔔 <b>YANGI STOL / BUYURTMA OCHILDI</b>\n\n"
        f"📍 <b>Stol:</b> {table_name}\n"
        f"👤 <b>Xodim:</b> {staff_name}\n"
        f"🧾 <b>Order:</b> #{order_ref}\n\n"
        f"🍽 <b>Tarkibi:</b>\n{items_text}"
    )
    send_telegram(msg)

  elif event in ["order.closed", "payment.created", "order.updated"]:
    msg = (
        f"✅ <b>TO'LOV QILINDI / STOL YOPILDI</b>\n\n"
        f"📍 <b>Stol:</b> {table_name}\n"
        f"👤 <b>Xodim:</b> {staff_name}\n"
        f"🧾 <b>Order:</b> #{order_ref}\n"
        f"💰 <b>Jami to'lov:</b> {total_price} AED\n\n"
        f"💵 <b>To'lov turi:</b>\n{payment_text}\n"
        f"🍽 <b>Yeyilgan taomlar:</b>\n{items_text}"
    )
    send_telegram(msg)

  return {"status": "ok"}
