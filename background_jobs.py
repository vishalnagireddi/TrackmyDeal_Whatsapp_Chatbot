from db import products_collection, price_history_collection
from scraper_service import scrape_product
from prediction_service import predict_future_price, get_product_trend_summary
from graph_service import generate_price_graph
from whatsapp_handler import send_whatsapp_message
from datetime import datetime, timezone
from bson import ObjectId
import os

def process_new_link_job(url, phone_nm, base_url):
    """Background job that scrapes the URL, updates DB, and sends the stats & graph back."""
    
    # 1. Scrape
    product_data = scrape_product(url)
    if not product_data or not product_data.get('price'):
        send_whatsapp_message(phone_nm, f"Sorry, I couldn't extract the details from that link. The website might be blocking bots.")
        return
        
    price = product_data['price']
    title = product_data.get('title', 'Unknown Product')
    image_url = product_data.get('image')
    
    # 2. Update DB Product
    products_collection.update_one(
        {"url": url},
        {
            "$set": {
                "title": title, 
                "image_url": image_url,
                "price": price,
                "last_updated": datetime.now(timezone.utc)
            },
            "$addToSet": {"users_tracking": {"phone": phone_nm}}
        },
        upsert=True
    )
    
    product = products_collection.find_one({"url": url})
    product_id = product["_id"]
    
    # 3. Add to Price History
    price_history_collection.insert_one({
        "product_id": product_id,
        "price": price,
        "timestamp": datetime.now(timezone.utc)
    })
    
    # Send Initial Info
    info_msg = f"*{title}*\n\nCurrent Price: ₹{price}\n\nI am now tracking this product! You will receive an alert automatically if the price ever drops. ✅"
    # Note: Sending an image message from a script sometimes requires a publicly accessible image URL.
    # The scraping `image_url` is already public from the e-commerce site!
    if image_url:
        send_whatsapp_message(phone_nm, info_msg, media_url=image_url)
    else:
        send_whatsapp_message(phone_nm, info_msg)
        
    # 4. Generate Stats and Graph
    summary = get_product_trend_summary(product_id)
    prediction = predict_future_price(product_id)
    
    stats_msg = f"📊 *Price Stats & Prediction*\n{summary}\n\n{prediction}"
    
    filepath = generate_price_graph(product_id)
    if filepath:
        media_url = f"{base_url}/{filepath}"
        send_whatsapp_message(phone_nm, stats_msg, media_url=media_url)
    else:
        send_whatsapp_message(phone_nm, stats_msg)
