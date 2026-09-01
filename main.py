
import asyncio
import os
import requests
from fastapi import FastAPI, Request

app = FastAPI()

FOODICS_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiI5MGQ1YTcxOC1lMzBkLTQ5ODYtODY0Ni0wNjdlZDBkMzdkMGUiLCJqdGkiOiI2NmFjYjEwNzZiMWVhZThlMDE2ODk5NjhiODVjOGQxODgyODAwNjUwOWE0OTg5NWExNGQyNjFjMmE5YzY1MmJmZDJjYTk2ZWJlNzVlYWZlNSIsImlhdCI6MTc4NzY1OTA3OS42MDQ0MDMsIm5iZiI6MTc4NzY1OTA3OS42MDQ0MDMsImV4cCI6MTk0NTQyNTQ3OS41MjExNzUsInN1YiI6IjlkZWQ4NjBhLTkyZGQtNGU4NS1iYjM1LTMwZjcxOGRlOTgyMCIsInNjb3BlcyI6WyJnZW5lcmFsLnJlYWQiLCJvcmRlcnMubGlzdCJdLCJidXNpbmVzcyI6IjlkZWQ4NjBhLTkzMzQtNDFlYy1iOTY4LWVmMDJkMmEzMDM1YiIsInJlZmVyZW5jZSI6Ijk0OTc3NiJ9.0UAgB9C7V1dblaKrw29yDac8xwuFm7CjOeN6U8GYzXa0rmPRSqb1UVwykvvXUYbeV9Guy9b4Ar2SnDDhOp_2JAW8sDpG2co7b65OElnT3bAMOB-MWlXtwllYmZ2d6-g6X3jmvanlzaqtQ9_VEgsK0NztZgINFuv0NN9eJh3-namzuVLOzm2IB1_bQ7taZxYvenuUPjOuWIh4lupIc1LpYQaxcvhAoNhG-oOfjI7zVBu_fTAxyZ75mXuvSk0We-RVYyELIEetgWxWs_RDBJ4hN4Xr-sZrQ8sdngIYrnCI05gQf0eeKmK1mAMPbbzXEOBsM3ufiEbcRw5QXmywM9LuatdP1WlQXs7lpGeDGpKktygr51xZbywzdH5WL2KKbM3U0jlf9_0zkpbtHTWN5kHpkyMGvPf9eWHmWUzlT4DWHAJOoj9VoEZrTO1_r6Hz_o3HjNRIAcT7ZNnpU-9_l0-tx8b_iOOFGrY2Lz_3WKBK5rMqkKsSoknYwU9AK1LOTF2NBGMV_JXg6BuEI6Fbpgx17mp3Xm4txnTY3hV7Y9uX-f7LKbHnqF0STx5wo2MBxpy3GNCYPEHy9SHhuKBKffMcr3F4HUK2Kz4lIe4XuX5qcp-Odv7yYV_Q9my1D99WudiGm5izDi4yST8iBiEY1sQ2vRVU748hS6XYocqEc1WGrno"
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


def format_time(time_str):
    """Foodics vaqt formatini chiroyli ko'rinishga keltirish"""
    if not time_str:
        return "Noma'lum"
    return str(time_str).split(".")[0].replace("T", " ")


@app.post("/webhook")
async def foodics_webhook(request: Request):
    data = await request.json()
    event = data.get("event")
    order = data.get("data", {})

    table = order.get("table", {})
    if isinstance(table, dict):
        table_name = table.get("name", "Takeaway / Delivery")
    else:
        table_name = "Takeaway"

    order_ref = order.get("reference", "—")
    total_price = order.get("total_price", 0)

    # Vaqtlarni ajratib olish va formatlash
    created_at = format_time(order.get("created_at"))
    updated_at = format_time(order.get("updated_at") or order.get("closed_at"))

    if event == "order.created":
        msg = (
            f"🔔 <b>YANGI STOL OCHILDI</b>\n\n"
            f"📍 <b>Stol:</b> {table_name}\n"
            f"🧾 <b>Order:</b> #{order_ref}\n\n"
            f"🕒 <b>Ochilgan vaqti:</b> {created_at}"
        )
        send_telegram(msg)

    elif event in ["order.closed", "payment.created"]:
        msg = (
            f"✅ <b>TO'LOV QILINDI / STOL YOPILDI</b>\n\n"
            f"📍 <b>Stol:</b> {table_name}\n"
            f"🧾 <b>Order:</b> #{order_ref}\n"
            f"💰 <b>Jami to'lov:</b> {total_price} AED\n\n"
            f"🕒 <b>Ochilgan vaqti:</b> {created_at}\n"
            f"🏁 <b>Yopilgan vaqti:</b> {updated_at}"
        )
        send_telegram(msg)

    return {"status": "ok"}
