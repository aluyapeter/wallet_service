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

## 🛠 Environment Setup

## 1. Copy the example environment file:

```bash
cp .env.example .env
```

Open .env and fill in your specific credentials (DB, Google, Paystack).

Note: For email testing, use your Gmail App Password.

## 3. Launch the Stack

Run the entire application (Database + API) with one command:

```bash
docker-compose up --build
```

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

| Method | Endpoint                    | Description                                                                                         |
| ------ | --------------------------- | --------------------------------------------------------------------------------------------------- |
| GET    | `/auth/google`              | Login via Google, paste the returned url in another tab to get your access token                    |
| GET    | `/auth/google/callback`     | Handles the callback from Google. Exchanges the code for a token, gets user info, and logs them in. |
| POST   | `/auth/signup`              | Registers a new user, creates their unique wallet, and triggers email verification. Google          |
| POST   | `/auth/verify-email`        | Verifies a user's email address using a One-Time Password (OTP).                                    |
| POST   | `/auth/login`               | Authenticates a user and issues a JWT access token.                                                 |
| GET    | `/auth/profile`             | Returns the authenticated user's profile details.                                                   |
| POST   | `/auth/resend-verification` | Generates a new OTP and sends it if the user is not yet verified.                                   |
| POST   | `/auth/set-pin`             | Sets the initial transaction PIN for the user.                                                      |
| POST   | `/auth/forgot-pin`          | Initiates the transaction PIN reset process by sending an OTP.                                      |
| POST   | `/auth/reset-pin`           | Resets the user's transaction PIN after validating the OTP.                                         |
| POST   | `/auth/forgot-password`     | Initiates the password recovery process by issuing a verification code.                             |
| POST   | `/auth/resset password`     | Resets the user's login password after verifying the One-Time Password (OTP).                       |

## ⚠️ Demo & Testing Note

This project is hosted on a **Free Tier** infrastructure which blocks outgoing SMTP email ports.

**To verify a new account:**

1. Sign up with any email address.
2. If you do not receive the OTP (due to platform restrictions), use the **Master OTP**:
   > **Code:** `000000`
3. This will instantly verify your account and allow you to test the full wallet functionality.
4. This also applies to the `reset-pin` and `reset-password` endpoints where OTP is required.

### 💳 Wallets & Bank

| Method | Endpoint                              | Description                                                                               |
| ------ | ------------------------------------- | ----------------------------------------------------------------------------------------- |
| POST   | `/wallet/deposit`                     | Initiates a deposit via Paystack.                                                         |
| POST   | `/wallet/paystack/webhook`            | Handles updates from Paystack. Verified via HMAC signature.                               |
| POST   | `/wallet/transfer`                    | Internal wallet-to-wallet transfer.                                                       |
| GET    | `/wallet/balance`                     | Returns the current wallet balance.                                                       |
| GET    | `/wallet/transactions`                | Returns a paginated lists of all transactions for the user's wallet. (`?limit=20&skip=0`) |
| POST   | `/wallets/deposit/{reference}/status` | Checks the status of a specific deposit.                                                  |
| POST   | `/wallet/withdraw`                    | Initiates a withdrawal from the user's wallet to an external bank account.                |
| GET    | `/banks/`                             | Helper endpoint to list banks and their codes                                             |
| GET    | `/banks/resolve`                      | Verifies an account number and returns the account name                                   |

### 🔐 Data & Keys

| Method | Endpoint         | Description                                                                              |
| ------ | ---------------- | ---------------------------------------------------------------------------------------- |
| POST   | `/keys/create`   | Generates a new API Key for the authenticated user. Enforces a maximum of 5 active keys. |
| POST   | `/keys/rollover` | Replaces an old/expired key with a new one inheriting the same permissions.              |
| POST   | `/keys/revoke`   | Permanently deactivates a specific API Key. The key will no longer work for any request. |

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

## Performance Benchmarks

Load tested with Locust under 50 concurrent users:

| Endpoint | Median (ms) | 99th Percentile (ms) | RPS |
|----------|-------------|----------------------|-----|
| GET /wallet/balance | 27 | 190 | 9.6 |
| POST /wallet/deposit | 39 | 240 | 2.0 |
| GET /wallet/transactions | 33 | 230 | 1.7 |
| POST /wallet/transfer | 230 | 1100 | 2.2 |
| POST /auth/login | 490 | 840 | — |
| **Aggregated** | **37** | **590** | **15.5** |

> 9,735 total requests · 0% failure rate · 50 concurrent users

<img width="1366" height="768" alt="Screenshot (425)" src="https://github.com/user-attachments/assets/c2ca26a2-dd8e-44e9-9b7c-e830ed15bf79" />

