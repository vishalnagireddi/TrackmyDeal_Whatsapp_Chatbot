import os
from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
from db import init_db
from scheduler import start_scheduler

load_dotenv()

app = Flask(__name__)

# Initialize MongoDB and Scheduler safely
try:
    print("Initializing components...")
    with app.app_context():
        init_db()
        os.makedirs(os.path.join(app.root_path, 'static', 'graphs'), exist_ok=True)
    
    # Start background price tracking
    start_scheduler()
    print("All components initialized successfully.")
except Exception as e:
    print(f"CRITICAL ERROR during app initialization: {e}")
    import traceback
    traceback.print_exc()

@app.route("/", methods=["GET"])
def health_check():
    return jsonify({"status": "TrackMyDeal Backend is running!"}), 200

from whatsapp_handler import handle_incoming_message, send_whatsapp_message

@app.route("/webhook", methods=["GET", "POST"])
def meta_webhook():
    # Setup webhook verification (GET)
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        
        # Check if a token and mode were sent
        if mode and token:
            # Check the mode and token sent are correct
            if mode == "subscribe" and token == os.getenv("META_VERIFY_TOKEN", "trackmydeal_verify"):
                print("WEBHOOK_VERIFIED")
                return challenge, 200
            else:
                return "Forbidden", 403
        return "Not Implemented", 400

    # Handling incoming messages (POST)
    if request.method == "POST":
        webhook_data = request.json
        print("Received webhook call from Meta")
        
        # Meta expects a 200 OK fast
        result = handle_incoming_message(webhook_data)
        
        if result.get("action") == "IGNORE":
             return "OK", 200
             
        phone_nm = result.get("phone")
             
        # Check if we need to do background scraping
        if result.get("action") == "PROCESS_NEW_LINK":
            send_whatsapp_message(phone_nm, result["response"])
            
            # Extract base_url for our custom graph serving later
            base_url = request.host_url.rstrip("/")
            
            import threading
            from background_jobs import process_new_link_job
            threading.Thread(target=process_new_link_job, args=(result["url"], phone_nm, base_url)).start()
            
            return "OK", 200
            
        elif result.get("action") == "GENERATE_GRAPH":
            from graph_service import generate_price_graph
            from bson import ObjectId
            
            product_id_str = result.get("product_id")
            filepath = generate_price_graph(ObjectId(product_id_str))
            
            if filepath:
                base_url = request.host_url.rstrip("/")
                media_url = f"{base_url}/{filepath}"
                send_whatsapp_message(phone_nm, result["response"], media_url=media_url)
                return "OK", 200
            else:
                send_whatsapp_message(phone_nm, "Not enough historical data to generate a graph yet.")
                return "OK", 200
            
        send_whatsapp_message(phone_nm, result["response"])
        return "OK", 200

@app.route('/static/graphs/<filename>')
def serve_graph(filename):
    return send_from_directory(os.path.join(app.root_path, 'static', 'graphs'), filename)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
