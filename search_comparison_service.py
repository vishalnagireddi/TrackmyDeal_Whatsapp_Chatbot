import urllib.parse

def generate_comparison_links(product_title):
    """
    Takes a product title and generates search URLs for major platforms
    so the user can easily compare prices.
    """
    if not product_title:
        return []
        
    encoded_title = urllib.parse.quote_plus(product_title)
    
    comparisons = [
        {"platform": "Amazon", "url": f"https://www.amazon.in/s?k={encoded_title}"},
        {"platform": "Flipkart", "url": f"https://www.flipkart.com/search?q={encoded_title}"},
        {"platform": "Google Shopping", "url": f"https://www.google.com/search?tbm=shop&q={encoded_title}"}
    ]
    
    return comparisons
    
def get_comparison_message(product_title):
    links = generate_comparison_links(product_title)
    if not links:
        return "Could not generate comparison links without a product title."
        
    msg = f"🔍 *Compare Prices for:*\n_{product_title}_\n\n"
    for item in links:
        msg += f"👉 *{item['platform']}*: {item['url']}\n\n"
        
    msg += "Check these links to see if there's a better deal elsewhere!"
    return msg
