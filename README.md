# 🏦 Fintech Wallet Service API (Mini-Bank Core)

A production-grade, async fintech backend built with **FastAPI**, **SQLModel**, and **PostgreSQL**. This system acts as a "Mini-Bank" core, featuring secure authentication, Step-Up security (PINs), real-time deposits, external bank withdrawals, and professional database migrations.

## 🚀 Features

### Core Banking

- **Wallets:** Automatic NGN wallet creation for every user.
- **Deposits:** Real-time funding via **Paystack** (Standard Checkout & Webhook verification).
- **Transfers:** Atomic, ACID-compliant internal money movement between users.
- **Withdrawals:** Automated payouts to external Nigerian bank accounts (Resolution + Transfer).
- **Transaction History:** Optimized, paginated transaction logs for high-volume users.

### Security & Identity

- **Authentication:** OAuth2 (Google) & JWT-based session management.
- **Step-Up Security:** **4-digit Transaction PIN** required for all outgoing funds (Hashed via Argon2).
- **API Security:** Permission-based API Keys for third-party integrations.
- **Integrity:** HMAC SHA512 signature verification for all payment webhooks.

### Engineering & DevOps

- **Containerization:** Fully Dockerized stack (API + Database) for consistent deployment.
- **Migrations:** Database schema version control using **Alembic**.
- **Observability:** Structured logging for debugging and audit trails.
- **Testing:** Comprehensive Pytest suite covering security gates and concurrency.

---

## 🛠️ Tech Stack

- **Language:** Python 3.11+
- **Framework:** FastAPI
- **Database:** PostgreSQL 15 (Dockerized)
- **ORM:** SQLModel (SQLAlchemy + Pydantic)
- **Migrations:** Alembic
- **Cryptography:** Pwdlib (Argon2), Passlib
- **Payments:** Paystack API
- **Infrastructure:** Docker & Docker Compose

---

## ⚡ Quick Start (Docker)

The application is fully containerized. You do not need to install Python or Postgres locally to run this.

### 1. Prerequisites

- Docker Desktop & Docker Compose
- Paystack Account (Test Mode)

### 2. Environment Setup

Create a `.env` file in the root directory:

````ini
# Database (Localhost allows access from outside container)
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/wallet_db
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=wallet_db

# Security
SECRET_KEY=your_super_secret_jwt_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# OAuth (Google)
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback

# Payments (Paystack)
PAYSTACK_SECRET_KEY=sk_test_xxxxxxxxxxxxxxxx


## 3. Launch the Stack

Run the entire application (Database + API) with one command:

```bash
docker-compose up --build
````

- **API:** http://localhost:8000
- **Swagger UI:** http://localhost:8000/docs
- **Database:** Port 5433 (Exposed for tools like DBeaver)

## 4. Apply Migrations

Once the container is running, initialize the database schema:

```bash
docker-compose exec web alembic upgrade head
```

## 💳 Payment Webhooks (Localhost)

To test deposits locally, Paystack must be able to reach your machine.

**Start a Tunnel:**

```bash
ssh -R 80:localhost:8000 localhost.run
```

Copy the HTTPS URL generated (e.g., `https://random-id.localhost.run`).

**Configure Paystack:**

1. Go to Paystack Dashboard > Settings > API Keys & Webhooks
2. Set Test Webhook URL to: `https://<YOUR_TUNNEL_URL>/wallet/paystack/webhook`
3. Click Save Changes

## 📚 API Documentation

### 🔐 Auth & Security

| Method | Endpoint        | Description                              |
| ------ | --------------- | ---------------------------------------- |
| POST   | `/auth/set-pin` | Set a 4-digit security PIN for transfers |
| GET    | `/auth/google`  | Login via Google                         |

### 🏦 Banking Operations

| Method | Endpoint           | Description                               |
| ------ | ------------------ | ----------------------------------------- |
| GET    | `/banks`           | List all supported Nigerian banks & codes |
| GET    | `/banks/resolve`   | Verify an account number (KYC check)      |
| POST   | `/wallet/withdraw` | Send money to an external bank account    |
| POST   | `/wallet/deposit`  | Initialize a deposit via Paystack         |
| POST   | `/wallet/transfer` | Send money to another user (Requires PIN) |

### 📊 Data & Keys

| Method | Endpoint               | Description                                        |
| ------ | ---------------------- | -------------------------------------------------- |
| GET    | `/wallet/transactions` | Paginated transaction history (`?limit=20&skip=0`) |
| GET    | `/wallet/balance`      | Check current wallet balance                       |
| POST   | `/keys/create`         | Generate a developer API Key                       |

## 🧪 Testing

The project uses Pytest for automated testing.

To run tests inside the container (Recommended):

```bash
docker-compose exec web pytest
```

**Key Test Suites:**

- `tests/test_transaction_pin.py`: Verifies PIN security lifecycle
- `tests/test_pagination.py`: Verifies data scaling
- `tests/test_wallet.py`: Verifies basic transfers

## 📦 Deployment (Manual/EC2)

1. Clone repository to server
2. Set up `.env` file with production secrets
3. Run `docker-compose up -d --build`
4. Run migrations `docker-compose exec web alembic upgrade head`
