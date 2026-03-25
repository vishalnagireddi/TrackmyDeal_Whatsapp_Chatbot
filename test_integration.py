import os
from db import init_db, users_collection
from whatsapp_handler import handle_incoming_message
from search_comparison_service import generate_comparison_links

def run_tests():
    print("=== Testing Database Connection ===")
    try:
        init_db()
    except Exception as e:
        print(f"DB Test Failed: {e}")
        
    print("\n=== Testing Meta WhatsApp Handler Logic ===")
    test_number = "1234567890"
    users_collection.delete_one({"phone_number": test_number}) # Clean start
    
    # Simulate Meta Graph API Message Payload for 'Hi'
    meta_hi_payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "from": test_number,
                        "type": "text",
                        "text": {"body": "Hi"}
                    }]
                }
            }]
        }]
    }
    
    # 1. New user sends 'Hi'
    res1 = handle_incoming_message(meta_hi_payload)
    print("Response 1:", res1["response"][:50].encode('ascii', 'ignore').decode(), "...")
    print("Action 1:", res1["action"])
    print("Extracted Phone 1:", res1.get("phone"))
    
    # Simulate Meta Payload for a Link
    meta_link_payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "from": test_number,
                        "type": "text",
                        "text": {"body": "https://www.amazon.in/dp/B0CHX1W1XY"}
                    }]
                }
            }]
        }]
    }

    # 2. User sends Link -> Should trigger PROCESS_NEW_LINK now!
    res2 = handle_incoming_message(meta_link_payload)
    print("\nResponse 2:", res2["response"][:50].encode('ascii', 'ignore').decode(), "...")
    print("Action 2:", res2["action"])
    print("Extracted Phone 2:", res2.get("phone"))
    
    # 3. Simulate "products" command
    meta_products_payload = {
        "entry": [{"changes": [{"value": {"messages": [{"from": test_number, "type": "text", "text": {"body": "products"}}]}}]}]
    }
    res3 = handle_incoming_message(meta_products_payload)
    print("\nResponse 3:", res3["response"].encode('ascii', 'ignore').decode())
    
    # 4. Simulate "exit 1" command
    meta_exit_payload = {
        "entry": [{"changes": [{"value": {"messages": [{"from": test_number, "type": "text", "text": {"body": "exit 1"}}]}}]}]
    }
    res4 = handle_incoming_message(meta_exit_payload)
    print("\nResponse 4:", res4["response"].encode('ascii', 'ignore').decode())

if __name__ == "__main__":
    run_tests()
