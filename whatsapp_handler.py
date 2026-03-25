import os
from db import users_collection, products_collection
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
    
    # Universal command interception
    msg_lower = incoming_msg.lower().strip()
    if msg_lower in ["products", "list", "hi", "hello"] or msg_lower.startswith("exit"):
         state = "PROCESS_COMMANDS"

    if state == "NEW":
        response_msg = "Hello! I am *TrackMyDeal*. Send me a valid product link to start tracking its price."
        users_collection.update_one({"phone_number": sender_phone}, {"$set": {"state": "WAITING_FOR_LINK"}})
        
    elif state == "WAITING_FOR_LINK":
        if "http" in incoming_msg:
            # immediately acknowledge and transition back to NEW so they can add another link right after
            users_collection.update_one({"phone_number": sender_phone}, {"$set": {"state": "NEW", "pending_product_url": None}})
            return {"response": "Got the link! 🔗 Please wait a moment while I fetch the details and graphs...", "action": "PROCESS_NEW_LINK", "url": incoming_msg, "phone": sender_phone}
        else:
            response_msg = "That doesn't look like a valid link. Please send a valid product URL."

    if state == "PROCESS_COMMANDS":
        msg_lower = incoming_msg.lower().strip()
        if msg_lower == "products" or msg_lower == "list":
            products = list(products_collection.find({"users_tracking.phone": sender_phone}))
            if products:
                response_msg = "📋 *Your Tracked Products:*\n\n"
                for idx, prod in enumerate(products, 1):
                    response_msg += f"{idx}. {prod.get('title', 'Unknown Product')}\n"
                response_msg += "\nTo stop tracking a product, reply with `exit [number]`. For example: `exit 1`"
            else:
                response_msg = "You aren't tracking any products yet. Send me a link to get started!"
        elif msg_lower.startswith("exit"):
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
                    response_msg = f"Done! I've stopped tracking: {prod_to_remove.get('title', 'that product')} 👋"
                else:
                    response_msg = "Invalid product number. Text `products` to see the full list."
            else:
                 response_msg = "Please specify a number. For example: `exit 1`"
        elif "stats" in msg_lower or "predict" in msg_lower:
            response_msg = "The 'stats' and 'predict' tools now process automatically when you submit a new URL! Try pasting a new link to see."
        elif msg_lower.startswith("graph"):
            parts = msg_lower.split()
            products = list(products_collection.find({"users_tracking.phone": sender_phone}))
            if not products:
                response_msg = "You aren't tracking any products yet."
            else:
                prod_idx = 0 # Default to first product if they just type "graph"
                if len(parts) == 2 and parts[1].isdigit():
                    prod_idx = int(parts[1]) - 1
                
                if 0 <= prod_idx < len(products):
                    product = products[prod_idx]
                    return {"response": f"Here is the latest trend graph for {product.get('title', 'your product')}:", "action": "GENERATE_GRAPH", "product_id": str(product['_id']), "phone": sender_phone}
                else:
                    response_msg = "Invalid product number. Text `products` to see your list."
        elif "compare" in msg_lower:
             response_msg = "Comparison engine triggers automatically when a link is sent."
        elif msg_lower == "hi" or msg_lower == "hello":
             response_msg = "Hello! I am *TrackMyDeal*. Send me a product link anytime to track its price."
             users_collection.update_one({"phone_number": sender_phone}, {"$set": {"state": "WAITING_FOR_LINK"}})
        else:
             if not response_msg:
                 response_msg = "I'm not sure what you mean. Send 'Hi' to start tracking, or 'products' to view your tracked list."
             users_collection.update_one({"phone_number": sender_phone}, {"$set": {"state": "NEW"}})

    return {"response": response_msg, "action": "REPLY", "phone": sender_phone}
