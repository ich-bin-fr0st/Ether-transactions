import requests
import psycopg2
from psycopg2 import sql
from datetime import datetime
import time
import os
from functools import wraps

# Replace with your Etherscan API endpoint and API key
ETHERSCAN_API_ENDPOINT = "https://api.etherscan.io/api"
ETHERSCAN_API_KEY = "<API>"

# Wallet address
WALLET_ADDRESS = "<wallet>"

# PostgreSQL connection details
PG_HOST = "<host>"
PG_PORT = "5432"
PG_DATABASE = "<Database>"
PG_USER = "<User>"
PG_PASSWORD = os.environ.get('PGPASSWORD',<passwd>)

# Rate limit settings
RATE_LIMIT = 4  # Number of requests per second
LAST_CALL_TIME = [0]  # Use list to allow modification inside inner function

def rate_limited(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        current_time = time.time()
        elapsed_time = current_time - LAST_CALL_TIME[0]
        if elapsed_time < 1 / RATE_LIMIT:
            time.sleep(1 / RATE_LIMIT - elapsed_time)
        LAST_CALL_TIME[0] = time.time()
        return func(*args, **kwargs)
    return wrapper

def get_pg_connection():
    return psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        database=PG_DATABASE,
        user=PG_USER,
        password=PG_PASSWORD,
        sslmode='require'
    )

@rate_limited
def fetch_all_transactions():
    params = {
        "module": "account",
        "action": "txlist",
        "address": WALLET_ADDRESS,
        "startblock": 0,
        "endblock": 99999999,
        "sort": "asc",
        "apikey": ETHERSCAN_API_KEY
    }
    response = requests.get(ETHERSCAN_API_ENDPOINT, params=params)
    data = response.json()
    return data['result']

@rate_limited
def fetch_new_transactions(last_checked_block):
    params = {
        "module": "account",
        "action": "txlist",
        "address": WALLET_ADDRESS,
        "startblock": last_checked_block + 1,
        "endblock": 99999999,
        "sort": "asc",
        "apikey": ETHERSCAN_API_KEY
    }
    response = requests.get(ETHERSCAN_API_ENDPOINT, params=params)
    data = response.json()
    return data['result']

@rate_limited
def get_eth_price(timestamp):
    params = {
        "module": "stats",
        "action": "ethprice",
        "timestamp": timestamp,
        "apikey": ETHERSCAN_API_KEY
    }
    response = requests.get(ETHERSCAN_API_ENDPOINT, params=params)
    data = response.json()
    return float(data['result']['ethusd'])

def save_transaction(transaction):
    try:
        value = int(transaction['value']) / 10**18  # Convert to ETH
        timestamp = int(transaction['timeStamp'])
        eth_price = get_eth_price(timestamp)
        value_usd = value * eth_price

        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql.SQL("""
                        INSERT INTO transactions (timestamp, hash, from_address, to_address, value_eth, value_usd, eth_price)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (hash) DO NOTHING
                    """),
                    (
                        datetime.fromtimestamp(timestamp),
                        transaction['hash'],
                        transaction['from'],
                        transaction['to'],
                        value,
                        value_usd,
                        eth_price
                    )
                )
            conn.commit()
    except Exception as e:
        print(f"Error saving transaction {transaction['hash']}: {e}")

def update_totals(total_inbound_eth, total_outbound_eth, total_inbound_usd, total_outbound_usd):
    try:
        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql.SQL("""
                        INSERT INTO totals (timestamp, total_inbound_eth, total_outbound_eth, total_inbound_usd, total_outbound_usd)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                            timestamp = EXCLUDED.timestamp,
                            total_inbound_eth = EXCLUDED.total_inbound_eth,
                            total_outbound_eth = EXCLUDED.total_outbound_eth,
                            total_inbound_usd = EXCLUDED.total_inbound_usd,
                            total_outbound_usd = EXCLUDED.total_outbound_usd
                    """),
                    (
                        datetime.now(),
                        total_inbound_eth,
                        total_outbound_eth,
                        total_inbound_usd,
                        total_outbound_usd
                    )
                )
            conn.commit()
    except Exception as e:
        print(f"Error updating totals: {e}")

def create_tables():
    try:
        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql.SQL("""
                        CREATE TABLE IF NOT EXISTS transactions (
                            id SERIAL PRIMARY KEY,
                            timestamp TIMESTAMP,
                            hash TEXT UNIQUE,
                            from_address TEXT,
                            to_address TEXT,
                            value_eth REAL,
                            value_usd REAL,
                            eth_price REAL
                        )
                    """)
                )
                cur.execute(
                    sql.SQL("""
                        CREATE TABLE IF NOT EXISTS totals (
                            id INT DEFAULT 1 PRIMARY KEY,
                            timestamp TIMESTAMP,
                            total_inbound_eth REAL,
                            total_outbound_eth REAL,
                            total_inbound_usd REAL,
                            total_outbound_usd REAL
                        )
                    """)
                )
            conn.commit()
    except Exception as e:
        print(f"Error creating tables: {e}")

def main():
    last_checked_block = 0
    total_inbound_eth = 0
    total_outbound_eth = 0
    total_inbound_usd = 0
    total_outbound_usd = 0

    create_tables()

    # Initial fetch
    transactions = fetch_all_transactions()
    for tx in transactions:
        save_transaction(tx)
        eth_value = int(tx['value']) / 10**18
        eth_price = get_eth_price(int(tx['timeStamp']))
        if tx['from'].lower() == WALLET_ADDRESS.lower():
            total_outbound_eth += eth_value
            total_outbound_usd += eth_value * eth_price
        else:
            total_inbound_eth += eth_value
            total_inbound_usd += eth_value * eth_price
    
    if transactions:
        last_checked_block = int(transactions[-1]['blockNumber'])

    # Update totals in the database after initial fetch
    update_totals(total_inbound_eth, total_outbound_eth, total_inbound_usd, total_outbound_usd)

    print(f"Initial sync complete. Last checked block: {last_checked_block}")

    # Continuous monitoring
    while True:
        try:
            new_transactions = fetch_new_transactions(last_checked_block)
            if new_transactions:
                for tx in new_transactions:
                    save_transaction(tx)
                    eth_value = int(tx['value']) / 10**18
                    eth_price = get_eth_price(int(tx['timeStamp']))
                    if tx['from'].lower() == WALLET_ADDRESS.lower():
                        total_outbound_eth += eth_value
                        total_outbound_usd += eth_value * eth_price
                    else:
                        total_inbound_eth += eth_value
                        total_inbound_usd += eth_value * eth_price
                last_checked_block = int(new_transactions[-1]['blockNumber'])

                # Update totals in the database
                update_totals(total_inbound_eth, total_outbound_eth, total_inbound_usd, total_outbound_usd)

                print(f"New transactions processed. Last checked block: {last_checked_block}")
            else:
                print("No new transactions found.")

        except Exception as e:
            print(f"An error occurred: {e}")

        time.sleep(60)  # Adjust sleep time as needed

if __name__ == "__main__":
    main()
