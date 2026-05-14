# Ghosted Cloud AI

Ghosted Cloud AI is a full-stack AWS operations assistant. The React frontend provides a terminal-style chat experience, and the FastAPI backend interprets natural-language commands, assumes a user-provided AWS IAM role, and performs supported EC2 and S3 actions through boto3.

## Features

- Natural-language AWS command processing with OpenAI-assisted interpretation.
- Secure AWS access through IAM Role ARN, External ID, and Region submitted from the UI.
- EC2 workflows for listing, creating, starting, stopping, rebooting, terminating, and multi-region deployment.
- S3 workflows for listing buckets, creating/deleting buckets, listing contents, uploading/downloading files, deleting objects, and bucket configuration.
- Deployment dashboard for viewing EC2 instances and triggering common instance actions.
- Docker Compose setup for local full-stack development.

## Tech Stack

- Frontend: React 18, TypeScript, Material UI, Create React App.
- Backend: Python 3.11, FastAPI, Pydantic, boto3, OpenAI SDK.
- Infrastructure helpers: Docker, Docker Compose, CloudFormation templates.

## Project Structure

```text
.
├── backend/                # FastAPI API, AI processing, AWS service integrations
│   ├── main.py             # Application setup, middleware, health check, routers
│   ├── routes/             # API route modules
│   ├── services/           # AI, AWS, and conversation-memory services
│   └── requirements.txt    # Python dependencies
├── frontend/               # React TypeScript application
│   ├── public/             # Static assets and IAM role templates
│   └── src/                # App, config flow, sidebar, deployments page, styles
├── cloudformation/         # IAM/CloudFormation templates
├── docker-compose.yml      # Local full-stack runner
├── Makefile                # Common install/build/test helpers
└── README.md
```

## Prerequisites

- Python 3.11+
- Node.js 18+
- npm
- AWS account with an IAM role that the app can assume
- OpenAI API key

## Local Setup

1. Copy environment examples:

```bash
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

2. Add your OpenAI API key to `backend/.env`.

3. Install backend dependencies:

```bash
python3 -m venv backend/.venv
backend/.venv/bin/pip install --upgrade pip
backend/.venv/bin/pip install -r backend/requirements.txt
```

4. Install frontend dependencies:

```bash
cd frontend
npm install
```

## Running Locally

Start the backend:

```bash
cd backend
../backend/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Start the frontend in another terminal:

```bash
cd frontend
npm start
```

Open `http://localhost:3000`, enter your AWS Role ARN, External ID, and Region, then use the chat or deployments view.

## Docker

```bash
docker compose up --build
```

The frontend runs at `http://localhost:3000` and the backend at `http://localhost:8000`.

## Verification

```bash
python3 -m compileall backend
cd frontend
npm run build
npm test
```

## Security Notes

- Do not commit `.env` files or API keys.
- If a real key was ever committed or shared, rotate it before making the repository public.
- AWS credentials are not hardcoded; the app expects role-based access through STS AssumeRole.
