# 🏦 Fintech Wallet Service API

A high-performance, async fintech backend built with **FastAPI**, **SQLModel**, and **PostgreSQL**. Features secure authentication, real-time payments via **Paystack**, atomic wallet transfers, and a permission-based API key system.

## 🚀 Features

* **Authentication:** JWT-based User Auth & API Key Auth for services.
* **Wallets:** Automatic wallet creation (NGN currency).
* **Deposits:** Integrated with Paystack (Checkout & Webhooks).
* **Security:** HMAC SHA512 signature verification for webhooks.
* **Transfers:** Atomic, ACID-compliant wallet-to-wallet transactions.
* **Developer API:** Issue, manage, and rollover API keys with specific permissions.
* **Scalability:** Database-agnostic design (Postgres in Prod, SQLite in Test).

## 🛠️ Tech Stack

* **Framework:** FastAPI (Python 3.12+)
* **Database:** PostgreSQL (via Docker)
* **ORM:** SQLModel (SQLAlchemy + Pydantic)
* **Payments:** Paystack API
* **Testing:** Pytest

---

## ⚡ Quick Start

### 1. Prerequisites
* Python 3.10+
* Docker & Docker Compose
* Paystack Account (Test Mode)

### 2. Environment Setup
Create a `.env` file in the root directory:
```ini
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/wallet_db
SECRET_KEY=your_super_secret_jwt_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
PAYSTACK_SECRET_KEY=sk_test_xxxxxxxxxxxxxxxx
```
## 3. Start the Database

We use Docker for the database to ensure isolation.
```bash
docker-compose up -d
```

This starts Postgres on port 5433.

## 4. Run the Application
```bash
# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn app.main:app --reload
```

The API will be live at `http://127.0.0.1:8000`.

## 💳 Payment Webhook Setup (Critical)

Since the app runs locally, Paystack needs a public URL to send transaction updates.

### 1. Start a Tunnel:
- **Option A (SSH)**: `ssh -R 80:localhost:8000 localhost.run`
- **Option B (VS Code)**: Ports Tab -> Forward Port 8000 -> Set Visibility to Public.

### 2. Configure Paystack:
- Go to Paystack Dashboard > Settings > API Keys & Webhooks.
- Set Test Webhook URL to: `https://<YOUR_TUNNEL_URL>/wallet/paystack/webhook`
- Click Save Changes.

## 🧪 Testing

Run the automated test suite to verify logic, security, and transaction atomicity.
```bash
pytest
```

## 📚 API Documentation

Interactive Swagger documentation is available at `/docs`.

### Key Endpoints

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| POST | /wallet/deposit | Initialize Paystack deposit | deposit |
| POST | /wallet/transfer | Send money to another user | transfer |
| GET | /wallet/balance | Check current balance | read |
| POST | /keys/create | Generate a permanent API Key | Auth |
| POST | /keys/rollover | Rotate a compromised key | Auth |