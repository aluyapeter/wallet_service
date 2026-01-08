import redis
import time

# 1. Connect to Redis (localhost because we are running this script outside Docker)
# If this fails, make sure 'docker-compose up' is running!
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

print("--- 1. The Basics ---")
r.set("my_name", "Peter")
print(f"My name in Redis is: {r.get('my_name')}")

print("\n--- 2. The Self-Destruct (TTL) ---")
r.set("secret_code", "007", ex=3) # Expires in 3 seconds
print(f"Code right now: {r.get('secret_code')}")

print("Sleeping for 4 seconds...")
time.sleep(4)

print(f"Code after 4 seconds: {r.get('secret_code')}") # Should be None

print("\n--- 3. Simulation: Idempotency ---")
key = "txn_12345"

# First Try
if r.get(key):
    print("Duplicate request! returning cached response.")
else:
    print("New request! Processing money...")
    r.set(key, "Transfer Successful", ex=10)

# Second Try (Duplicate)
if r.get(key):
    print("Duplicate request! returning cached response.")
else:
    print("New request! Processing money...")