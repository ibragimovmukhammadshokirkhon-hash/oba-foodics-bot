import asyncio
import os
import requests
from fastapi import FastAPI, Request

app = FastAPI()

FOODICS_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiI1MGQ1YTQxTC0xMzBkLTQSODYTODY0Ni0wNjRkM2RkMGUiLCJqdGkiOiI2NmFjYjEwNzI1NWNFJjEwMDE2MDKsNjhi0OVJ0GQxODAxNjUwWE00OTg1T0D0ODY0IiwiaWp0IjoxMDE2MDU2Q2QkOiI2NmFjYjEwNzI1NWNFJjEwMDE2MDKsNjhi0OVJ0GQxODAx" # O'zingizning to'liq tokeningiz
TELEGRAM_BOT_TOKEN = "8853263842:AAGZnt5pUEoH3WdjTKM2AP9fwdzCHgdoKm8"
TELEGRAM_CHAT_ID = "-1004471118381"

headers = {
    "Authorization": f"Bearer {FOODICS_TOKEN}",
    "Content-Type": "application/json"
}

def send_telegram(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Telegram error: {e}")

def get_order_details(order_id: str):
    """Foodics API'dan buyurtmaning to'liq ma'lumotlarini (stol va mahsulotlar) tortib olish"""
    url = f"https://api.foodics.com/v5/orders/{order_id}?include=products,table"
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            return res.json().get("data", {})
    except Exception as e:
        print(f"Order fetch error: {e}")
    return {}

@app.post("/webhook")
async def foodics_webhook(request: Request):
    data = await request.json()
    event = data.get("event")
    raw_order = data.get("data", {})
    
    order_id = raw_order.get("id")
    if not order_id:
        return {"status": "no order id"}

    # To'liq buyurtma tafsilotlarini API orqali olish
    order = get_order_details(order_id)
    if not order:
        order = raw_order

    # Order ID / Number
    order_num = order.get("number") or order.get("reference") or order_id
    
    # Stol ma'lumoti
    table = order.get("table")
    if table and isinstance(table, dict):
        table_name = table.get("name", "Dine In")
    else:
        table_name = "Takeaway / Delivery"

    total_price = order.get("total_price", 0)

    # Mahsulotlar ro'yxati
    products = order.get("products", [])
    items_text = ""
    if products:
        for item in products:
            # Ba'zida mahsulot nomi nested ob'ekt ichida bo'ladi
            p_obj = item.get("product", {})
            p_name = p_obj.get("name") if isinstance(p_obj, dict) else item.get("name", "Mahsulot")
            p_qty = item.get("quantity", 1)
            p_price = item.get("unit_price", item.get("total_price", 0))
            items_text += f"• <b>{p_name}</b> — {p_qty}x ({p_price} AED)\n"
    else:
        items_text = "<i>Mahsulotlar biriktirilmagan</i>\n"

    if event == "order.created":
        msg = (
            f"🔔 <b>YANGI STOL / BUYURTMA OCHILDI</b>\n\n"
            f"📍 <b>Stol:</b> {table_name}\n"
            f"🧾 <b>Order:</b> #{order_num}\n\n"
            f"🍽 <b>Tarkibi:</b>\n{items_text}"
        )
        send_telegram(msg)

    elif event in ["order.closed", "payment.created"]:
        msg = (
            f"✅ <b>TO'LOV QILINDI / STOL YOPILDI</b>\n\n"
            f"📍 <b>Stol:</b> {table_name}\n"
            f"🧾 <b>Order:</b> #{order_num}\n"
            f"💰 <b>Jami to'lov:</b> {total_price} AED\n\n"
            f"🍽 <b>Yeyilgan taomlar:</b>\n{items_text}"
        )
        send_telegram(msg)

    return {"status": "ok"}
