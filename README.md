# OrderFlow — Event-Driven Order Management System

OrderFlow is an order management system built with FastAPI and PostgreSQL. Order creation is separated from background processing using AWS: the API accepts the order, and a Lambda worker processes it asynchronously. The whole infrastructure is created with Terraform.

```
FastAPI → PostgreSQL → SQS → Lambda → PostgreSQL → SNS → S3
```

## Demo

▶ Demo video: https://github.com/user-attachments/assets/2428ded4-e5d1-4bb6-b26c-278e85b17b87

> The AWS infrastructure was destroyed with `terraform destroy` after testing to avoid extra cost. The video shows the full working system, and Terraform can recreate it at any time.

## Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI, Pydantic v2, Uvicorn |
| Database | PostgreSQL (Amazon RDS), SQLAlchemy 2.x, Alembic |
| Auth | JWT, bcrypt, role-based access (customer / admin) |
| Messaging | Amazon SQS + Dead Letter Queue, Amazon SNS |
| Processing | AWS Lambda |
| Storage | Amazon S3 |
| Containers | Docker, docker-compose, Amazon ECR |
| Compute | Amazon EC2 |
| Infrastructure as Code | Terraform |
| Testing | pytest, FastAPI TestClient, unittest.mock |

## Architecture

![OrderFlow architecture](docs/architecture.png)

```
Browser → EC2 (FastAPI in Docker)
              ├──► RDS PostgreSQL
              └──► SQS (orderflow-orders) ──► Lambda worker
                                                 ├──► RDS (update status)
                                                 ├──► SNS (email notification)
                                                 └──► S3 (invoice + event documents)

Failed messages ──► SQS Dead Letter Queue
```

Region: `ap-southeast-1` (Singapore)

## How an Order Is Processed

1. The customer places an order through the API.
2. The API validates the order, checks and reserves stock, and saves it as `PENDING`.
3. The API sends a message to SQS and returns the response right away.
4. Lambda reads the message and moves the order `PENDING → PROCESSING → CONFIRMED`.
5. Lambda publishes the event to SNS (email notification).
6. Lambda stores `invoice.json`, `order-event.json` and `processing-log.json` in S3.

Why this design:
- **SQS** keeps the API fast. Slow work happens in the background.
- **Dead Letter Queue** catches messages that keep failing, so they are not lost.
- **Idempotency checks** stop the same message from being processed twice (SQS can deliver a message more than once).
- **Partial batch failure handling** retries only the failed messages in a batch.

## Features

**Customers:** register and log in (JWT), browse products, place multi-item orders, view order history and order events, cancel orders while `PENDING`.

**Admins:** manage products, view all customers and orders, filter orders by status, update order status, view dashboard statistics and revenue.

**Platform:** structured JSON logging, Alembic migrations, order state machine (invalid transitions are rejected), AWS can be turned off for local development (`AWS_DISABLED=true`).

## Order State Machine

```
PENDING ──► PROCESSING ──► CONFIRMED ──► COMPLETED
   │             │
   ▼             ▼
CANCELLED      FAILED
```

## Terraform Infrastructure

The `terraform/` folder creates: VPC networking (with NAT Gateway and Elastic IP), EC2, RDS PostgreSQL, SQS and DLQ, Lambda with SQS event source mapping, SNS, S3, ECR, IAM roles and policies, and security groups.

```bash
cd terraform
terraform init
terraform validate
terraform plan
terraform apply

# when finished
terraform destroy
```

> Note: the NAT Gateway and EC2 cost money while running. Destroy the environment when you are not using it.

## Run Locally (Docker)

```bash
git clone https://github.com/AbdullahSheikh8873/orderflow.git
cd orderflow
cp .env.example .env        # fill in your own values
docker-compose up -d --build
```

- API: http://localhost:8000
- Swagger docs: http://localhost:8000/docs

Run migrations and seed demo data:

```bash
alembic upgrade head
python scripts/seed_products.py
python scripts/create_admin.py admin@example.com "Admin User" <your-password>
```

## Environment Variables

```env
DATABASE_URL=postgresql+psycopg2://<user>:<password>@localhost:5432/orderflow
JWT_SECRET_KEY=<long-random-secret>
AWS_REGION=ap-southeast-1
S3_BUCKET_NAME=<your-bucket-name>
SQS_QUEUE_URL=<your-queue-url>
SNS_TOPIC_ARN=<your-topic-arn>
AWS_DISABLED=true
```

On EC2 and Lambda, use IAM roles instead of static AWS keys. Never commit `.env`, `*.tfstate` or `*.tfvars`.

## Main API Endpoints

```
POST   /api/auth/register
POST   /api/auth/login
GET    /api/products
POST   /api/orders
GET    /api/orders
GET    /api/orders/{id}/events
POST   /api/orders/{id}/cancel
PATCH  /api/orders/{id}/status        (admin)
GET    /api/admin/dashboard           (admin)
```

Full list: `/docs` (Swagger).

## Tests

```bash
pytest -q
```

Covers authentication, product and order flows, stock handling, order state transitions, cross-customer access protection, admin features, and Lambda processing including duplicate messages and error paths. AWS calls are mocked, so no AWS account is needed to run the tests.

## Project Structure

```
orderflow/
├── app/              # FastAPI app (routers, services, models, aws/)
├── lambda/order_processor/   # Lambda worker
├── alembic/          # migrations
├── terraform/        # infrastructure as code
├── scripts/          # create_admin, seed_products
├── tests/
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## Troubleshooting

| Problem | Likely cause |
|---|---|
| Orders stay `PENDING` | Lambda is not receiving messages from SQS |
| Messages go to the DLQ | Lambda failed repeatedly on that message |
| Lambda cannot reach PostgreSQL | VPC or security group problem |
| S3 documents missing | Wrong bucket name or IAM permission |
| No SNS email | Subscription not confirmed or wrong topic |

## What I Learned

- Building an event-driven design with SQS, Lambda, SNS and S3
- Dead Letter Queues and idempotent processing
- Writing AWS infrastructure as code with Terraform
- VPC networking, security groups and IAM roles
- Deploying a Dockerized app with ECR and EC2
- Managing AWS cost by destroying resources after testing

## Author

Abdullah Sheikh — [GitHub](https://github.com/AbdullahSheikh8873)
