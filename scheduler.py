import time
from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from db import products_collection, price_history_collection
from scraper_service import scrape_product
from whatsapp_handler import send_whatsapp_message

scheduler = BackgroundScheduler()

def track_prices():
    print(f"[{datetime.now(timezone.utc)}] Running price tracking job...")
    products = list(products_collection.find({}))
    
    for product in products:
        url = product.get("url")
        users_tracking = product.get("users_tracking", [])
        if not users_tracking:
            continue
            
        print(f"Scraping {url}...")
        data = scrape_product(url)
        current_price = data.get("price")
        
        if current_price is None:
            print(f"Could not extract price for {url}")
            continue
            
        # Optional: Save base metadata if it wasn't there
        if not product.get("title") and data.get("title"):
             products_collection.update_one({"_id": product["_id"]}, {"$set": {"title": data["title"], "image_url": data.get("image")}})
             
        product_title = product.get("title") or data.get("title") or "Your Tracked Product"
        product_id = product["_id"]
        
        # Get the historical lowest price BEFORE we insert the current price
        lowest_historical_doc = price_history_collection.find_one(
            {"product_id": product_id},
            sort=[("price", 1)]
        )
        
        lowest_price = float('inf')
        if lowest_historical_doc:
            lowest_price = lowest_historical_doc.get("price", float('inf'))
            
        # Log to price history
        price_history_collection.insert_one({
            "product_id": product_id,
            "url": url,
            "price": current_price,
            "timestamp": datetime.now(timezone.utc)
        })
        
        # Check alerts (if current price is strictly less than the lowest historical)
        if current_price < lowest_price and lowest_price != float('inf'):
            for user in users_tracking:
                phone = user.get("phone")
                msg = f"🚨 *PRICE DROP!* {product_title} is now *₹{current_price}*! (Was ₹{lowest_price})\n\nBuy it here: {url}"
                send_whatsapp_message(phone, msg)
                
        time.sleep(2) # be nice to sites

def daily_summary():
    print(f"[{datetime.now(timezone.utc)}] Running daily summary job...")
    products = list(products_collection.find({}))
    
    from graph_service import generate_price_graph
    import requests
    import os
    
    # Dynamically find the public URL (ngrok locally or Render cloud)
    base_url = os.getenv("RENDER_EXTERNAL_URL")
    if not base_url:
        try:
            resp = requests.get("http://127.0.0.1:4040/api/tunnels", timeout=2)
            if resp.status_code == 200:
                tunnels = resp.json().get('tunnels', [])
                for t in tunnels:
                    if t['public_url'].startswith("https"):
                        base_url = t['public_url']
                        break
        except Exception:
            pass

    # We will send 1 combined text digest, PLUS an individual graph image message for each product
    users_with_products = {}
    user_graphs = {}
    
    for product in products:
        title = product.get("title", "A Product")
        url = product.get("url")
        product_id = product["_id"]
        
        latest_doc = price_history_collection.find_one(
            {"product_id": product_id},
            sort=[("timestamp", -1)]
        )
        latest_price = latest_doc.get("price") if latest_doc else "Unknown"
        
        # Generate the graph silently
        filepath = generate_price_graph(product_id)
        media_url = f"{base_url}/{filepath}" if (base_url and filepath) else None
        
        for user in product.get("users_tracking", []):
            phone = user.get("phone")
            
            # Setup digest list
            if phone not in users_with_products:
                users_with_products[phone] = []
                user_graphs[phone] = []
                
            users_with_products[phone].append(f"- {title} : ₹{latest_price}")
            
            # Queue the graph to be sent
            if media_url:
                user_graphs[phone].append({
                    "msg": f"📈 Latest Trend for: {title}",
                    "media_url": media_url
                })
            
    for phone, item_strings in users_with_products.items():
        if item_strings:
            summary_list = "\n".join(item_strings)
            msg = f"🌅 *Daily TrackMyDeal Summary*\n\nHere are the current prices for products you are tracking:\n\n{summary_list}"
            # 1. Send text digest first
            send_whatsapp_message(phone, msg)
            
            # 2. Blast all the graphs
            for graph_obj in user_graphs.get(phone, []):
                send_whatsapp_message(phone, graph_obj['msg'], media_url=graph_obj['media_url'])
                time.sleep(1) # Be nice to Meta API

def start_scheduler():
    # Schedule job to run every 3 hours
    scheduler.add_job(func=track_prices, trigger="interval", hours=3, id="track_prices_job")
    # Add daily job at 9:00 AM India time
    scheduler.add_job(func=daily_summary, trigger="cron", hour=9, minute=0, id="daily_summary_job")
    scheduler.start()
    print("Scheduler started. Prices tracked every 3 hours, daily summary at 9:00 AM.")

    # Run once immediately on start for testing/development
    # track_prices()
