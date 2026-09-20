import json, os

CACHE_DIR = os.path.join(os.path.dirname(__file__), 'data_cache')

user_fleet = ['BTC', 'ETH', 'TAO', 'BNB', 'UNI', 'AAVE', 'LINK', 'NEAR']
# Let's check ONDO data in data_cache or fetch it if needed!
print("Files in data_cache:")
for f in os.listdir(CACHE_DIR):
    if 'ONDO' in f or 'ondo' in f.lower():
        print("Found:", f)
