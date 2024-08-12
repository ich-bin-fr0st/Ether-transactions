# Ethereum Wallet Transaction Tracker

This Python script monitors transactions for a specified Ethereum wallet address, fetches historical and new transactions, and stores them in a PostgreSQL database. It also calculates and updates total inbound and outbound amounts in both ETH and USD.

## Features

- Fetches all historical transactions for a given Ethereum wallet address
- Continuously monitors for new transactions
- Stores transaction details in a PostgreSQL database
- Calculates and updates total inbound and outbound amounts
- Implements rate limiting to comply with Etherscan API usage guidelines
- Uses environment variables for sensitive information

## Prerequisites

- Python 3.6+
- PostgreSQL database
- Etherscan API key

## Installation

1. Clone this repository or download the script.
2. Install required Python packages:

```
pip install requests psycopg2
```

3. Set up your PostgreSQL database and note down the connection details.

## Configuration

1. Replace the placeholder values in the script with your actual data:
   - `ETHERSCAN_API_KEY`: Your Etherscan API key
   - `WALLET_ADDRESS`: The Ethereum wallet address you want to monitor
   - `PG_HOST`: PostgreSQL host address
   - `PG_PORT`: PostgreSQL port (default is 5432)
   - `PG_DATABASE`: PostgreSQL database name
   - `PG_USER`: PostgreSQL username
   - `PG_PASSWORD`: PostgreSQL password (or use environment variable)

2. Set the `PGPASSWORD` environment variable with your PostgreSQL password:

```
export PGPASSWORD=your_postgres_password
```

## Usage

Run the script using Python:

```
python eth_wallet_tracker.py
```

The script will:
1. Create necessary tables in the PostgreSQL database if they don't exist.
2. Fetch all historical transactions for the specified wallet.
3. Store transaction details in the database.
4. Continuously monitor for new transactions and update the database.
5. Update total inbound and outbound amounts in both ETH and USD.

## Database Schema

The script creates two tables in the PostgreSQL database:

1. `transactions`: Stores individual transaction details
   - `id`: Serial primary key
   - `timestamp`: Transaction timestamp
   - `hash`: Unique transaction hash
   - `from_address`: Sender's address
   - `to_address`: Recipient's address
   - `value_eth`: Transaction amount in ETH
   - `value_usd`: Transaction amount in USD
   - `eth_price`: ETH price in USD at the time of the transaction

2. `totals`: Stores aggregate totals
   - `id`: Primary key (always 1)
   - `timestamp`: Last update timestamp
   - `total_inbound_eth`: Total inbound amount in ETH
   - `total_outbound_eth`: Total outbound amount in ETH
   - `total_inbound_usd`: Total inbound amount in USD
   - `total_outbound_usd`: Total outbound amount in USD

## Error Handling

The script includes basic error handling and will print error messages to the console. For production use, consider implementing more robust error handling and logging.

## Rate Limiting

The script implements a simple rate limiting mechanism to comply with Etherscan API usage guidelines. Adjust the `RATE_LIMIT` variable if needed.

## License

[MIT License](https://opensource.org/licenses/MIT)

## Disclaimer

This script is for educational purposes only. Use at your own risk. Always ensure you comply with Etherscan's terms of service and API usage guidelines.
