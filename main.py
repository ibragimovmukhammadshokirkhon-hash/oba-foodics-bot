import asyncio
import os
import requests
from fastapi import FastAPI, Request

app = FastAPI()

FOODICS_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiI1MGQ1YTQxTC0xMzBkLTQSODYTODY4Ni0wNjRkM2RkMGUiLCJqdGkiOiI2NmFjYjEwNzI1NWNFJjEwMDE2MDKsNjhi0OVJ0GQxODAxNjUwWE00OTg1T0D0ODY0IiwiaWp0IjoxMDE2MDU2Q2QkOiI2NmFjYjEwNzI1NWNFJjEwMDE2MDKsNjhi0OVJ0GQxODAx"
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
    """Fetch complete details: table, user (staff), products, and payments"""
    url = f"https://api.foodics.com/v5/orders/{order_id}?include=products,table,user,payments,payments.payment_method"
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

    order = get_order_details(order_id)
    if not order:
        order = raw_order

    order_num = order.get("number") or order.get("reference") or order_id
    order_status = order.get("status") # 1: Active, 2: Void, 3: Closed, 4: Paid

    # Waiter / Cashier Name
    user = order.get("user")
    staff_name = user.get("name", "Staff") if isinstance(user, dict) else "Staff"

    # Table
    table = order.get("table")
    if table and isinstance(table, dict):
        table_name = table.get("name", "Dine In")
    else:
        table_name = "Takeaway / Delivery"

    total_price = order.get("total_price", 0)

    # Products List
    products = order.get("products", [])
    items_text = ""
    if products:
        for item in products:
            p_obj = item.get("product", {})
            p_name = p_obj.get("name") if isinstance(p_obj, dict) else item.get("name", "Item")
            p_qty = item.get("quantity", 1)
            p_price = item.get("unit_price", item.get("total_price", 0))
            items_text += f"• <b>{p_name}</b> — {p_qty}x ({p_price} AED)\n"
    else:
        items_text = "<i>No items attached</i>\n"

    # Payment Methods
    payments = order.get("payments", [])
    payment_text = ""
    if payments:
        for pay in payments:
            pay_method = pay.get("payment_method", {})
            method_name = pay_method.get("name", "Cash/Card") if isinstance(pay_method, dict) else "Payment"
            pay_amount = pay.get("amount", 0)
            payment_text += f"💳 <b>{method_name}:</b> {pay_amount} AED\n"
    else:
        payment_text = f"💳 <b>Payment:</b> {total_price} AED\n"

    # 1. New Order / Table Opened Event
    if event == "order.created":
        msg = (
            f"🔔 <b>NEW ORDER / TABLE OPENED</b>\n\n"
            f"📍 <b>Table:</b> {table_name}\n"
            f"👤 <b>Opened by:</b> {staff_name}\n"
            f"🧾 <b>Order:</b> #{order_num}\n\n"
            f"🍽 <b>Items:</b>\n{items_text}"
        )
        send_telegram(msg)

    # 2. Order Updated Event (Triggers when Order is Paid / Closed)
    elif event == "order.updated":
        # Status 3 = Closed, Status 4 = Paid, or if payments exist
        if order_status in [3, 4] or payments:
            msg = (
                f"✅ <b>ORDER PAID / CLOSED</b>\n\n"
                f"📍 <b>Table:</b> {table_name}\n"
                f"👤 <b>Closed by:</b> {staff_name}\n"
                f"🧾 <b>Order:</b> #{order_num}\n"
                f"💰 <b>Total Amount:</b> {total_price} AED\n\n"
                f"💵 <b>Payment Details:</b>\n{payment_text}\n"
                f"🍽 <b>Ordered Items:</b>\n{items_text}"
            )
            send_telegram(msg)

    return {"status": "ok"}
