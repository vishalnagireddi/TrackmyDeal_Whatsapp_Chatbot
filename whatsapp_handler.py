import os
from db import users_collection, products_collection, price_history_collection
from prediction_service import predict_future_price, get_product_trend_summary
from search_comparison_service import get_comparison_message
import requests

# Meta Configuration
META_WHATSAPP_TOKEN = os.getenv("META_WHATSAPP_TOKEN")
META_PHONE_NUMBER_ID = os.getenv("META_PHONE_NUMBER_ID")

def send_whatsapp_message(to_number, body, media_url=None):
    """Sends an outbound WhatsApp message using Meta Cloud API."""
    if not META_WHATSAPP_TOKEN or not META_PHONE_NUMBER_ID:
        print(f"Mock send to {to_number}: {body}")
        return

    # Meta requires numbers without the '+' sign or 'whatsapp:' prefix
    formatted_number = str(to_number).replace('+', '').replace('whatsapp:', '')

    url = f"https://graph.facebook.com/v21.0/{META_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {META_WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    if media_url:
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": formatted_number,
            "type": "image",
            "image": {
                "link": media_url,
                "caption": body
            }
        }
    else:
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": formatted_number,
            "type": "text",
            "text": {
                "preview_url": True,
                "body": body
            }
        }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        print(f"Sent Meta message to {formatted_number}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending Meta WhatsApp message to {formatted_number}: {e}")
        if e.response is not None:
             print(f"Meta API Error Status: {e.response.status_code}")
             print(f"Meta API Error Details: {e.response.text}")

def parse_meta_message(webhook_data):
    """Extracts sender phone and message text from the noisy Meta webhook JSON."""
    try:
        entry = webhook_data['entry'][0]
        changes = entry['changes'][0]
        value = changes['value']
        
        # Check if it is a message (and not a status update like 'delivered'/'read')
        if 'messages' in value and len(value['messages']) > 0:
            message = value['messages'][0]
            sender_phone = message.get('from')
            
            # Extract text if available
            message_body = ""
            if message.get('type') == 'text':
                message_body = message.get('text', {}).get('body', "")
                
            return sender_phone, message_body
    except (KeyError, IndexError, TypeError):
        pass
    
    return None, None

def handle_incoming_message(webhook_data):
    """
    State Machine for conversation.
    """
    sender_phone, incoming_msg = parse_meta_message(webhook_data)
    
    if not sender_phone or not incoming_msg:
        # Not a valid message or just a status update, ignore
        return {"response": None, "action": "IGNORE", "phone": sender_phone}

    incoming_msg = incoming_msg.strip()

    # Get or create user
    user = users_collection.find_one({"phone_number": sender_phone})
    if not user:
        user = {"phone_number": sender_phone, "state": "NEW", "pending_product_url": None}
        users_collection.insert_one(user)

    state = user.get("state", "NEW")
    response_msg = ""
    msg_lower = incoming_msg.lower().strip()
    
    # 1. Universal interception for Links
    if "http" in incoming_msg:
        # Reset state and process link
        users_collection.update_one({"phone_number": sender_phone}, {"$set": {"state": "NEW", "pending_product_url": None}})
        return {"response": "Got the link! 🔗 Please wait a moment while I fetch the details and graphs...", "action": "PROCESS_NEW_LINK", "url": incoming_msg, "phone": sender_phone}

    # 2. Universal interception for Greetings
    if msg_lower in ["hi", "hello"]:
        response_msg = "Hello! I am *TrackMyDeal*. Send me a valid product link to start tracking its price."
        users_collection.update_one({"phone_number": sender_phone}, {"$set": {"state": "NEW"}})
        return {"response": response_msg, "action": "REPLY", "phone": sender_phone}

    # 3. Handle AWAITING_PRICE_DROP_CONFIRM state
    if state == "AWAITING_PRICE_DROP_CONFIRM":
        if msg_lower in ['yes', 'ok', 'okay', 'y', 'yup', 'yeah', 'sure']:
            products = list(products_collection.find({"users_tracking.phone": sender_phone}))
            if products:
                response_msg = "📉 *Price Drop Status:*\n\n"
                for prod in products:
                    prod_id = prod["_id"]
                    title = prod.get("title", 'Unknown Product')
                    current_price = prod.get("price")
                    
                    # Get oldest price from history (first time we saw it)
                    oldest_hist = price_history_collection.find_one({"product_id": prod_id}, sort=[("timestamp", 1)])
                    
                    if oldest_hist and current_price is not None:
                        initial_price = oldest_hist.get("price")
                        if initial_price and current_price < initial_price:
                            diff = initial_price - current_price
                            response_msg += f"✅ *Yes!* Your _{title}_ has dropped by *₹{diff}* since you added it! (Initial: ₹{initial_price}, Now: ₹{current_price})\n"
                        elif initial_price and current_price > initial_price:
                            response_msg += f"🔺 The price of _{title}_ has increased (Added at ₹{initial_price}, Now: ₹{current_price}).\n"
                        else:
                            response_msg += f"➖ The _{title}_ is at the same price as when you started (Added at ₹{initial_price or 'Unknown'}, Now: ₹{current_price}).\n"
                    else:
                        response_msg += f"➖ Not enough data yet for _{title}_.\n"
            else:
                response_msg = "You aren't tracking any products yet."
            
            users_collection.update_one({"phone_number": sender_phone}, {"$set": {"state": "NEW"}})
            return {"response": response_msg, "action": "REPLY", "phone": sender_phone}
        else:
             # They said something else, fall through to the invalid check
             state = "NEW" # resetting state for fallthrough

    # 4. Handle "Products" list command
    if msg_lower in ["products", "list"]:
        products = list(products_collection.find({"users_tracking.phone": sender_phone}))
        if products:
            response_msg = "📋 *Your Tracked Products:*\n\n"
            for idx, prod in enumerate(products, 1):
                response_msg += f"{idx}. {prod.get('title', 'Unknown Product')} - ₹{prod.get('price', 'Pending')}\n"
            response_msg += "\nTo stop tracking a product, reply with `exit [number]`. For example: `exit 1`\n\n"
            response_msg += "*Want to know if your product had a price drop?* (Reply 'yes' or 'ok')"
            users_collection.update_one({"phone_number": sender_phone}, {"$set": {"state": "AWAITING_PRICE_DROP_CONFIRM"}})
        else:
            response_msg = "You aren't tracking any products yet. Send me a link to get started!"
            users_collection.update_one({"phone_number": sender_phone}, {"$set": {"state": "NEW"}})
        return {"response": response_msg, "action": "REPLY", "phone": sender_phone}

    # 5. Handle "Exit" command
    if msg_lower.startswith("exit"):
        parts = msg_lower.split()
        if len(parts) == 2 and parts[1].isdigit():
            prod_idx = int(parts[1]) - 1
            products = list(products_collection.find({"users_tracking.phone": sender_phone}))
            if 0 <= prod_idx < len(products):
                prod_to_remove = products[prod_idx]
                products_collection.update_one(
                    {"_id": prod_to_remove["_id"]},
                    {"$pull": {"users_tracking": {"phone": sender_phone}}}
                )
                response_msg = f"Done! I've stopped tracking: {prod_to_remove.get('title', 'that product')} 👋\n\nType 'Products' anytime to see your list."
            else:
                response_msg = "Invalid product number. Text `products` to see the full list."
        else:
             response_msg = "Please specify a number. For example: `exit 1`"
        users_collection.update_one({"phone_number": sender_phone}, {"$set": {"state": "NEW"}})
        return {"response": response_msg, "action": "REPLY", "phone": sender_phone}

    # 6. Fallback (Strict handler)
    response_msg = "I don't get you. Send me your link or type 'Products' to see your tracked items."
    users_collection.update_one({"phone_number": sender_phone}, {"$set": {"state": "NEW"}})
    return {"response": response_msg, "action": "REPLY", "phone": sender_phone}
