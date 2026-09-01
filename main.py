
import asyncio
import os
import requests
from fastapi import FastAPI, Request

app = FastAPI()

FOODICS_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiI5MGQ1YTcxOC1lMzBkLTQ5ODYtODY4Ni0wNjdlZDBkMzdkMGUiLCJqdGkiOiI2NmFjYjEwNzZiMWVhZThlMDE2ODk5NjhiODVjOGQxODgyODAwNjUwOWE0OTg5NWExNGQyNjFjMmE5YzY1MmJmZDJjYTk2ZWJlNzVlYWZlNSIsImlhdCI6MTc4NzY1OTA3OS42MDQ0MDMsIm5iZiI6MTc4NzY1OTA3OS42MDQ0MDMsImV4cCI6MTk0NTQyNTQ3OS41MjExNzUsInN1YiI6IjlkZWQ4NjBhLTkyZGQtNGU4NS1iYjM1LTMwZjcxOGRlOTgyMCIsInNjb3BlcyI6WyJnZW5lcmFsLnJlYWQiLCJvcmRlcnMubGlzdCJdLCJidXNpbmVzcyI6IjlkZWQ4NjBhLTkzMzQtNDFlYy1iOTY4LWVmMDJkMmEzMDM1YiIsInJlZmVyZW5jZSI6Ijk0OTc3NiJ9.0UAgB9C7V1dblaKrw29yDac8xwuFm7CjOeN6U8GYzXa0rmPRSqb1UVwykvvXUYbeV9Guy9b4Ar2SnDDhOp_2JAW8sDpG2co7b65OElnT3bAMOB-MWlXtwllYmZ2d6-g6X3jmvanlzaqtQ9_VEgsK0NztZgINFuv0NN9eJh3-namzuVLOzm2IB1_bQ7taZxYvenuUPjOuWIh4lupIc1LpYQaxcvhAoNhG-oOfjI7zVBu_fTAxyZ75mXuvSk0We-RVYyELIEetgWxWs_RDBJ4hN4Xr-sZrQ8sdngIYrnCI05gQf0eeKmK1mAMPbbzXEOBsM3ufiEbcRw5QXmywM9LuatdP1WlQXs7lpGeDGpKktygr51xZbywzdH5WL2KKbM3U0jlf9_0zkpbtHTWN5kHpkyMGvPf9eWHmWUzlT4DWHAJOoj9VoEZrTO1_r6Hz_o3HjNRIAcT7ZNnpU-9_l0-tx8b_iOOFGrY2Lz_3WKBK5rMqkKsSoknYwU9AK1LOTF2NBGMV_JXg6BuEI6Fbpgx17mp3Xm4txnTY3hV7Y9uX-f7LKbHnqF0STx5wo2MBxpy3GNCYPEHy9SHhuKBKffMcr3F4HUK2Kz4lIe4XuX5qcp-Odv7yYV_Q9my1D99WudiGm5izDi4yST8iBiEY1sQ2vRVU748hS6XYocqEc1WGrno"
TELEGRAM_BOT_TOKEN = "8853263842:AAGZnt5pUEoH3WdjTKM2AP9fwdzCHgdoKm8"
TELEGRAM_CHAT_ID = "-1004471118381"

headers = {
    "Authorization": f"Bearer {FOODICS_TOKEN}",
    "Content-Type": "application/json"
}

def send_telegram(text: str):
    """Send formatted notification message to Telegram Channel"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        res = requests.post(url, json=payload, timeout=5)
        print("Telegram API HTTP Status:", res.status_code)
    except Exception as e:
        print(f"Telegram Delivery Error: {e}")

def get_order_details(order_id: str):
    """Fetch complete order details (table, staff, items, payments) via Foodics API v5"""
    url = f"https://api.foodics.com/v5/orders/{order_id}?include=table,user,products,payments,payments.payment_method"
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            return res.json().get("data", {})
    except Exception as e:
        print(f"Foodics API Fetch Error: {e}")
    return {}

def format_time(time_str):
    """Format ISO timestamp to readable string (YYYY-MM-DD HH:MM:SS)"""
    if not time_str:
        return "—"
    return str(time_str).split(".")[0].replace("T", " ")

@app.post("/webhook")
async def foodics_webhook(request: Request):
    try:
        data = await request.json()
        event = data.get("event")
        raw_order = data.get("data", {})

        order_id = raw_order.get("id")
        if not order_id:
            return {"status": "no order id"}

        # Fetch full order details from Foodics API
        order = get_order_details(order_id)
        if not order:
            order = raw_order

        # 1. Order Number
        order_ref = order.get("number") or order.get("reference") or raw_order.get("reference", "—")

        # 2. Staff / Cashier / Waiter
        user = order.get("user")
        staff_name = user.get("name", "Staff") if isinstance(user, dict) else "Staff"

        # 3. Table
        table = order.get("table")
        if isinstance(table, dict) and table.get("name"):
            table_name = table.get("name")
        else:
            table_name = "Takeaway / Delivery"

        # 4. Total Amount
        total_price = order.get("total_price", 0)

        # 5. Timestamps
        created_at = format_time(order.get("created_at"))
        closed_at = format_time(order.get("closed_at") or order.get("updated_at"))

        # 6. Ordered Items List
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

        # 7. Payment Breakdown
        payments = order.get("payments", [])
        payment_text = ""
        if payments:
            for pay in payments:
                pay_method = pay.get("payment_method", {})
                method_name = pay_method.get("name", "Cash / Card") if isinstance(pay_method, dict) else "Payment"
                pay_amount = pay.get("amount", 0)
                payment_text += f"💳 <b>{method_name}:</b> {pay_amount} AED\n"
        else:
            payment_text = f"💳 <b>Payment:</b> {total_price} AED\n"

        # Telegram Notifications Template (English)
        if event == "order.created":
            msg = (
                f"🔔 <b>NEW ORDER / TABLE OPENED</b>\n\n"
                f"📍 <b>Table:</b> {table_name}\n"
                f"👤 <b>Opened by:</b> {staff_name}\n"
                f"🧾 <b>Order:</b> #{order_ref}\n"
                f"🕒 <b>Opened at:</b> {created_at}\n\n"
                f"🍽 <b>Items:</b>\n{items_text}"
            )
            send_telegram(msg)

        elif event in ["order.closed", "payment.created", "order.updated"]:
            msg = (
                f"✅ <b>ORDER PAID / CLOSED</b>\n\n"
                f"📍 <b>Table:</b> {table_name}\n"
                f"👤 <b>Closed by:</b> {staff_name}\n"
                f"🧾 <b>Order:</b> #{order_ref}\n"
                f"💰 <b>Total Amount:</b> {total_price} AED\n"
                f"🕒 <b>Opened at:</b> {created_at}\n"
                f"🏁 <b>Closed at:</b> {closed_at}\n\n"
                f"💵 <b>Payment Details:</b>\n{payment_text}\n"
                f"🍽 <b>Ordered Items:</b>\n{items_text}"
            )
            send_telegram(msg)

    except Exception as err:
        print(f"Webhook Processing Error: {err}")

    return {"status": "ok"}
