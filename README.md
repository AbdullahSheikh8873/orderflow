# OrderFlow — Event-Driven E-Commerce Order Management System

OrderFlow is a production-style, event-driven Order Management System built with **FastAPI** and **PostgreSQL**, designed to demonstrate a realistic cloud-native architecture on **AWS**.

The application provides customer authentication, product browsing, order placement, order tracking, administration, and asynchronous order processing.

AWS services are used to decouple order creation from background processing:

**FastAPI → PostgreSQL → SQS → Lambda → PostgreSQL → SNS → S3**

The project also includes **Docker**, **Amazon ECR**, **EC2**, **RDS PostgreSQL**, and **Terraform** for infrastructure provisioning and deployment.

---

## 1. Project Overview

When a customer places an order, the API performs the minimum work required to accept the request:

1. Validate the order.
2. Validate and reserve product stock.
3. Save the order in PostgreSQL with `PENDING` status.
4. Publish an order message to Amazon SQS.
5. Return the response to the customer.

The remaining processing happens asynchronously.

The Lambda worker consumes the SQS message and moves the order through:

```text
PENDING → PROCESSING → CONFIRMED
```

The worker then:

* Updates the PostgreSQL order status.
* Publishes an order event to SNS.
* Stores invoice and event documents in S3.
* Writes processing information to S3.
* Uses idempotency checks to prevent duplicate processing.

This architecture keeps the API responsive while moving background work into an event-driven processing pipeline.

---

# 2. Features

## Customers

* Register and log in using JWT authentication.
* View and update profile.
* Browse products.
* View individual product details.
* Place multi-item orders.
* Provide shipping information.
* View order history.
* View order details.
* View order event/audit history.
* Cancel orders while they are still `PENDING`.

## Admins

* Create, update, and delete products.
* Soft-delete products.
* View all customers.
* View all orders.
* Filter orders by status.
* Manually update order status.
* View order events.
* View dashboard statistics.
* View total revenue and order counts.

## Platform

* FastAPI REST API.
* JWT authentication.
* Bcrypt password hashing.
* Role-based authorization.
* SQLAlchemy 2.x ORM.
* Alembic database migrations.
* PostgreSQL database.
* Event-driven AWS architecture.
* SQS-based asynchronous processing.
* Lambda order processor.
* SQS Dead Letter Queue.
* SNS order notifications.
* S3 order documents.
* Structured JSON logging.
* Idempotent order processing.
* Docker containerization.
* Amazon ECR container registry.
* Terraform infrastructure as code.
* Automated AWS infrastructure provisioning and destruction.
* AWS integration can be disabled for local development.

---

# 3. Technology Stack

| Layer                  | Technology                   |
| ---------------------- | ---------------------------- |
| API                    | FastAPI                      |
| Validation             | Pydantic v2                  |
| Server                 | Uvicorn                      |
| ORM                    | SQLAlchemy 2.x               |
| Migrations             | Alembic                      |
| Database               | PostgreSQL                   |
| Authentication         | JWT                          |
| Password Hashing       | bcrypt                       |
| AWS SDK                | boto3                        |
| Frontend               | Jinja2 + HTML/CSS/JavaScript |
| Containerization       | Docker                       |
| Local orchestration    | docker-compose               |
| Container Registry     | Amazon ECR                   |
| Compute                | Amazon EC2                   |
| Database Hosting       | Amazon RDS PostgreSQL        |
| Queue                  | Amazon SQS                   |
| Dead Letter Queue      | Amazon SQS                   |
| Background Processing  | AWS Lambda                   |
| Notifications          | Amazon SNS                   |
| Object Storage         | Amazon S3                    |
| Infrastructure as Code | Terraform                    |
| Testing                | pytest + FastAPI TestClient  |
| AWS Testing            | unittest.mock                |

---

# 4. AWS Architecture

The production architecture used during testing was:

```text
                         ┌─────────────────┐
                         │     Browser      │
                         │    / Client      │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │   EC2 Instance  │
                         │  OrderFlow API   │
                         │    FastAPI       │
                         └────────┬────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
                    ▼                           ▼
             ┌─────────────┐             ┌─────────────┐
             │     RDS     │             │     SQS     │
             │ PostgreSQL  │             │ Order Queue │
             └─────────────┘             └──────┬──────┘
                                                │
                                                ▼
                                         ┌─────────────┐
                                         │   Lambda    │
                                         │    Worker   │
                                         └──────┬──────┘
                                                │
                           ┌────────────────────┼──────────────────┐
                           │                    │                  │
                           ▼                    ▼                  ▼
                    ┌─────────────┐      ┌─────────────┐   ┌─────────────┐
                    │     RDS     │      │     SNS     │   │     S3      │
                    │   Update    │      │ Notifications│   │ Documents   │
                    └─────────────┘      └──────┬──────┘   └─────────────┘
                                                 │
                                                 ▼
                                          ┌─────────────┐
                                          │    Email    │
                                          │ Subscriber  │
                                          └─────────────┘
```

### AWS Region

The project was deployed and tested in:

```text
ap-southeast-1
Singapore
```

---

# 5. AWS Services

## Amazon EC2

The FastAPI application was deployed to an EC2 instance running the Dockerized OrderFlow API.

The production API was exposed on:

```text
Port 8000
```

The API was tested through:

```text
http://<EC2_PUBLIC_IP>:8000
```

Health endpoint:

```text
GET /health
```

Example:

```json
{
  "status": "ok",
  "app": "OrderFlow",
  "environment": "production"
}
```

---

## Amazon RDS PostgreSQL

PostgreSQL was hosted using Amazon RDS.

The application connected to RDS using the `DATABASE_URL` environment variable.

The Lambda function was also configured to communicate with the PostgreSQL database.

---

## Amazon SQS

SQS was used to decouple order creation from order processing.

The main queue was:

```text
orderflow-orders
```

The Dead Letter Queue was:

```text
orderflow-dlq
```

The queue used a redrive policy so repeatedly failing messages could be moved to the DLQ.

---

## AWS Lambda

The order processor Lambda consumed messages from SQS.

Function:

```text
orderflow-order-processor
```

Processing flow:

```text
SQS Message
     ↓
Lambda
     ↓
Find Order
     ↓
PENDING → PROCESSING
     ↓
Business Processing
     ↓
PROCESSING → CONFIRMED
     ↓
SNS Notification
     ↓
S3 Documents
```

The Lambda implementation supports partial batch failure handling so failed messages can be retried without unnecessarily retrying successfully processed messages.

---

## Amazon SNS

SNS was used for order event notifications.

Topic:

```text
orderflow-notifications
```

The application publishes order events such as:

```text
ORDER_PROCESSING
ORDER_CONFIRMED
```

During production testing, SNS email notifications were successfully received.

---

## Amazon S3

S3 was used to store order-related documents.

Bucket used during the AWS deployment:

```text
orderflow-abdullah-2026
```

Objects were stored using:

```text
orders/{year}/{month}/{order_number}/
```

Example:

```text
orders/2026/09/ORD-2026-093599/invoice.json
orders/2026/09/ORD-2026-093599/order-event.json
orders/2026/09/ORD-2026-093599/processing-log.json
```

These documents contain invoice, event, and processing information.

> The production S3 bucket was intentionally deleted after the AWS demonstration/testing was completed to avoid unnecessary AWS charges.

---

## Amazon ECR

The FastAPI Docker image was stored in Amazon ECR.

Repository:

```text
orderflow-api
```

The application image was built locally and pushed to ECR before deployment to EC2.

Example:

```bash
docker build -t orderflow-api .
```

Then the image can be tagged and pushed to ECR.

---

# 6. Terraform Infrastructure

The AWS infrastructure is defined using Terraform.

Terraform configuration is located in:

```text
terraform/
```

The Terraform configuration provisions the required AWS infrastructure including:

* EC2
* RDS PostgreSQL
* S3
* SQS
* SQS DLQ
* Lambda
* SNS
* IAM roles
* IAM policies
* Security groups
* NAT Gateway
* Elastic IP
* Database subnet group
* Lambda event source mapping
* ECR

Terraform allows the complete infrastructure to be recreated without manually configuring every AWS service.

---

## Terraform Workflow

From the Terraform directory:

```bash
cd terraform
```

Initialize Terraform:

```bash
terraform init
```

Check the configuration:

```bash
terraform validate
```

Create a plan:

```bash
terraform plan
```

Apply the infrastructure:

```bash
terraform apply
```

When finished with the AWS environment, destroy it:

```bash
terraform destroy
```

The infrastructure can therefore be created for testing/demo purposes and destroyed afterward to minimize AWS costs.

---

# 7. Local Development

Clone the repository:

```bash
git clone <your-repository-url> orderflow
cd orderflow
```

Create a Python virtual environment if running without Docker:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create the environment file:

```bash
cp .env.example .env
```

Configure the required environment variables.

---

# 8. Docker Setup

OrderFlow can be run locally using Docker.

The project uses `docker-compose`.

Start the application:

```bash
docker-compose up -d --build
```

Check containers:

```bash
docker-compose ps
```

View logs:

```bash
docker-compose logs -f
```

Stop the application:

```bash
docker-compose down
```

The local setup starts:

```text
FastAPI
PostgreSQL
```

The API is available at:

```text
http://localhost:8000
```

Swagger documentation:

```text
http://localhost:8000/docs
```

ReDoc:

```text
http://localhost:8000/redoc
```

---

# 9. Local AWS Mode

The application supports an AWS-disabled mode for local development.

Set:

```env
AWS_DISABLED=true
```

In this mode, AWS operations are not sent to real AWS services.

This allows the application and its business logic to be developed locally without requiring active AWS infrastructure.

For real AWS deployment:

```env
AWS_DISABLED=false
```

The application then uses the configured AWS services through boto3.

---

# 10. Environment Variables

Important configuration variables include:

```env
DATABASE_URL=postgresql+psycopg2://orderflow:orderflow@localhost:5432/orderflow

JWT_SECRET_KEY=change-this-to-a-long-random-secret

AWS_REGION=ap-southeast-1

AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=

S3_BUCKET_NAME=
SQS_QUEUE_URL=
SNS_TOPIC_ARN=

AWS_DISABLED=true
```

For AWS workloads such as EC2 and Lambda, IAM roles should be preferred over static AWS access keys.

---

# 11. Database

OrderFlow uses PostgreSQL.

Main tables:

| Table          | Purpose                       |
| -------------- | ----------------------------- |
| `users`        | Customer and admin accounts   |
| `products`     | Product catalog and inventory |
| `orders`       | Order records and status      |
| `order_items`  | Individual order products     |
| `order_events` | Order audit/event history     |

Database migrations are handled by Alembic.

Run migrations:

```bash
alembic upgrade head
```

Seed demo products:

```bash
python scripts/seed_products.py
```

Create an admin user:

```bash
python scripts/create_admin.py admin@orderflow.com "Admin User" SuperSecret123
```

When running through Docker, project scripts can also be executed inside the API container.

---

# 12. Order State Machine

Order status transitions are controlled by the application state machine.

```text
PENDING
   │
   ├──────────────► CANCELLED
   │
   ▼
PROCESSING
   │
   ├──────────────► FAILED
   │
   ▼
CONFIRMED
   │
   ▼
COMPLETED
```

Invalid transitions are rejected by the application.

The Lambda worker only processes orders that are still in `PENDING` state.

---

# 13. Order Processing Flow

A complete order follows this flow:

```text
Customer
   │
   ▼
FastAPI
   │
   ├── Validate order
   ├── Check stock
   ├── Reserve stock
   └── Save PENDING order
          │
          ▼
       Amazon SQS
          │
          ▼
       AWS Lambda
          │
          ├── Process order
          ├── Update PROCESSING
          ├── Update CONFIRMED
          │
          ├──────────────► Amazon SNS
          │
          └──────────────► Amazon S3
```

This separates the user-facing API request from background processing.

---

# 14. S3 Order Documents

For every processed order, the application can create:

```text
invoice.json
order-event.json
processing-log.json
```

Example:

```text
orders/2026/09/ORD-2026-093599/invoice.json
orders/2026/09/ORD-2026-093599/order-event.json
orders/2026/09/ORD-2026-093599/processing-log.json
```

The S3 documents provide an external record of order processing and events.

---

# 15. Lambda Idempotency

The Lambda processor is designed to handle duplicate messages safely.

The application uses order event/idempotency information to prevent the same event from being processed multiple times.

This is important because distributed messaging systems such as SQS can deliver messages more than once.

The processor also skips orders that are no longer in the expected processing state.

---

# 16. Project Structure

```text
orderflow/
│
├── app/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   │
│   ├── models/
│   ├── schemas/
│   ├── routers/
│   ├── services/
│   ├── repositories/
│   ├── dependencies/
│   ├── core/
│   │
│   ├── aws/
│   │   ├── s3.py
│   │   ├── sqs.py
│   │   └── sns.py
│   │
│   ├── templates/
│   └── static/
│
├── lambda/
│   └── order_processor/
│       ├── handler.py
│       ├── requirements.txt
│       └── services/
│
├── alembic/
│   └── versions/
│
├── tests/
│
├── scripts/
│   ├── create_admin.py
│   ├── seed_products.py
│   └── wait_for_db.py
│
├── terraform/
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   └── ...
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

---

# 17. API Documentation

FastAPI automatically provides interactive API documentation.

Swagger:

```text
GET /docs
```

ReDoc:

```text
GET /redoc
```

Important endpoints:

```text
POST   /api/auth/register
POST   /api/auth/login
GET    /api/auth/me

GET    /api/products
GET    /api/products/{id}

POST   /api/products
PUT    /api/products/{id}
DELETE /api/products/{id}

POST   /api/orders
GET    /api/orders
GET    /api/orders/{id}
GET    /api/orders/{id}/events
POST   /api/orders/{id}/cancel

PATCH  /api/orders/{id}/status

GET    /api/admin/dashboard
GET    /api/admin/orders
GET    /api/admin/users
GET    /api/admin/products
GET    /api/admin/events
```

Authenticated API requests use:

```text
Authorization: Bearer <JWT>
```

Authorization is enforced at the service/API layer rather than relying only on frontend restrictions.

---

# 18. Testing

Run the test suite:

```bash
pytest -q
```

The test suite covers:

* User registration
* Login
* JWT authentication
* Profile access
* Duplicate email validation
* Password validation
* Product CRUD
* Admin authorization
* Product price validation
* Order creation
* Stock decrement
* Insufficient stock handling
* Unknown product handling
* Order cancellation
* Stock restoration
* Order state transitions
* Cross-customer access protection
* Admin dashboard
* Order filtering
* User/event management
* AWS integration mocks
* Lambda order processing
* Idempotent duplicate processing
* Non-PENDING order handling
* Lambda error paths

AWS calls can be mocked during tests, so the test suite does not require an active AWS environment.

---

# 19. Production Deployment

The demonstrated AWS deployment used the following workflow:

```text
Local Development
       │
       ▼
Docker Build
       │
       ▼
Amazon ECR
       │
       ▼
EC2
       │
       ▼
FastAPI Application
       │
       ├────────► RDS PostgreSQL
       │
       └────────► SQS
                     │
                     ▼
                  Lambda
                  /     \
                 /       \
               SNS       S3
```

The infrastructure itself was managed using Terraform.

Typical deployment workflow:

```bash
cd terraform

terraform init
terraform validate
terraform plan
terraform apply
```

After infrastructure deployment, the API container image can be built and pushed to ECR.

The EC2 instance then runs the OrderFlow API container.

---

# 20. Production Validation

The AWS deployment was successfully tested end-to-end.

The validation included:

* FastAPI health check.
* Browser-based application access.
* User authentication.
* Product listing.
* Order creation.
* PostgreSQL persistence.
* SQS message delivery.
* Lambda order processing.
* Order status transition.
* SNS notification delivery.
* S3 document creation.
* ECR container image deployment.

A successful order reached:

```text
PENDING
   ↓
PROCESSING
   ↓
CONFIRMED
```

Example successful order:

```text
ORD-2026-093599
```

The order successfully generated:

```text
invoice.json
order-event.json
processing-log.json
```

in S3.

SNS confirmation notifications were also successfully received during testing.

---

# 21. AWS Cost Management

Because this project was created for development, learning, and demonstration purposes, the AWS infrastructure was destroyed after the production demonstration was completed.

Terraform was used to remove the infrastructure:

```bash
terraform destroy
```

The S3 bucket used for the demonstration had versioning enabled. Before destroying the bucket, all object versions and delete markers were removed.

The final infrastructure cleanup completed successfully.

The Terraform state was also verified:

```bash
terraform state list
```

No managed resources remained in the Terraform state.

The S3 bucket was additionally verified as deleted.

This approach avoids leaving billable AWS resources running when the project is not being demonstrated.

---

# 22. Troubleshooting

| Problem                             | Possible Cause                                                        |
| ----------------------------------- | --------------------------------------------------------------------- |
| Orders remain `PENDING`             | Lambda/SQS event source is not processing messages                    |
| Messages accumulate in SQS          | Lambda processing failure                                             |
| Messages move to DLQ                | Lambda repeatedly failed to process the message                       |
| Lambda cannot connect to PostgreSQL | VPC/security group/database connectivity issue                        |
| API cannot connect to RDS           | Incorrect `DATABASE_URL` or security group configuration              |
| S3 documents are not created        | Incorrect bucket configuration or IAM permission                      |
| SNS notification not received       | Incorrect topic/subscription configuration                            |
| Docker API does not start           | PostgreSQL may not be ready or environment configuration is incorrect |
| `401 Unauthorized`                  | JWT configuration or authentication token issue                       |
| Alembic migration fails             | Incorrect database URL or database connectivity                       |
| AWS calls are not happening locally | `AWS_DISABLED=true`                                                   |
| ECR push fails                      | AWS authentication or repository configuration issue                  |

---

# 23. Security Considerations

The project follows several production-oriented security practices:

* Passwords are hashed using bcrypt.
* JWT authentication is used for API authentication.
* Role-based authorization protects administrative endpoints.
* AWS credentials should not be hard-coded.
* IAM roles are preferred for EC2 and Lambda.
* `.env` files should not be committed.
* AWS resources should use least-privilege IAM policies where possible.
* S3 public access should remain disabled.
* Database access should be restricted through security groups.
* Secrets should be stored securely in real production environments.

Never commit real credentials such as:

```text
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
JWT_SECRET_KEY
DATABASE_PASSWORD
```

to GitHub.

---

# 24. What This Project Demonstrates

OrderFlow demonstrates a complete cloud-native development workflow:

```text
Application Development
        ↓
FastAPI + PostgreSQL
        ↓
Docker
        ↓
Amazon ECR
        ↓
EC2 Deployment
        ↓
RDS PostgreSQL
        ↓
SQS
        ↓
Lambda
        ↓
SNS
        ↓
S3
        ↓
Terraform Infrastructure as Code
        ↓
Infrastructure Cleanup
```

The project demonstrates more than a basic CRUD application. It shows how a real-world order processing system can be separated into synchronous API operations and asynchronous event-driven workloads.

---

# 25. Key Learning Areas

This project provides practical experience with:

* FastAPI
* REST APIs
* PostgreSQL
* SQLAlchemy
* Alembic
* JWT authentication
* Docker
* Docker Compose
* AWS EC2
* AWS RDS
* AWS SQS
* AWS Lambda
* AWS SNS
* AWS S3
* Amazon ECR
* IAM
* Security Groups
* VPC networking
* NAT Gateway
* Terraform
* Infrastructure as Code
* Event-driven architecture
* Asynchronous processing
* Dead Letter Queues
* Idempotent processing
* Cloud deployment
* AWS resource cleanup
* Cost-conscious cloud management

---

# 26. Project Status

The OrderFlow application was successfully:

* Developed locally.
* Containerized with Docker.
* Deployed to AWS.
* Connected to Amazon RDS PostgreSQL.
* Integrated with SQS.
* Processed using AWS Lambda.
* Integrated with SNS.
* Persisted documents to S3.
* Stored as a Docker image in ECR.
* Provisioned using Terraform.
* Tested end-to-end.
* Demonstrated through the web application.
* Successfully cleaned up after demonstration.

The AWS infrastructure is currently **destroyed**, while the complete project source code and Terraform configuration remain available for future deployment.

---

# 27. Final Architecture

```text
                    ┌──────────────────────┐
                    │       Customer       │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │     FastAPI / EC2    │
                    │    OrderFlow API      │
                    └──────────┬───────────┘
                               │
                    ┌──────────┴──────────┐
                    │                     │
                    ▼                     ▼
             ┌─────────────┐       ┌─────────────┐
             │ RDS Postgres│       │     SQS     │
             └─────────────┘       └──────┬──────┘
                                          │
                                          ▼
                                   ┌─────────────┐
                                   │   Lambda    │
                                   │Order Worker │
                                   └──────┬──────┘
                                          │
                         ┌────────────────┼────────────────┐
                         │                │                │
                         ▼                ▼                ▼
                  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
                  │ RDS Update  │  │     SNS     │  │     S3      │
                  └─────────────┘  └──────┬──────┘  └─────────────┘
                                          │
                                          ▼
                                   ┌─────────────┐
                                   │ Notifications│
                                   └─────────────┘
```

---

## Conclusion

OrderFlow was built to demonstrate a realistic event-driven order management architecture using modern Python development practices and AWS cloud services.

The project combines:

**FastAPI + PostgreSQL + Docker + AWS + Terraform + Event-Driven Architecture**

while maintaining a clear separation between the user-facing API and asynchronous background processing.

The infrastructure can be recreated using Terraform when required and destroyed after demonstrations to avoid unnecessary cloud costs.
