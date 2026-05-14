# ghosted

> talk to your cloud like you talk to a person.

ghosted is an AI-powered AWS operations platform. type what you want in plain english — spin up EC2 instances, manage S3 buckets, deploy across regions — and ghosted handles the rest. no console clicking. no CLI memorization. just say it.

![React](https://img.shields.io/badge/React_18-TypeScript-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-Python_3.11-green) ![AWS](https://img.shields.io/badge/AWS-boto3-orange)

## what it does

- **natural language AWS** — type "launch a t3.medium in us-west-2" and it happens
- **EC2 everything** — list, create, start, stop, reboot, terminate, multi-region deploy
- **S3 everything** — buckets, objects, uploads, downloads, config
- **zero hardcoded credentials** — connects through IAM AssumeRole with your own role ARN
- **deployment dashboard** — real-time view of your EC2 fleet with one-click actions
- **one-click IAM setup** — CloudFormation template launches the required role in seconds

## stack

| layer | tech |
|---|---|
| frontend | React 18, TypeScript, Material UI |
| backend | Python 3.11, FastAPI, Pydantic, boto3 |
| AI | OpenAI GPT-4o for command interpretation |
| infra | Docker Compose, CloudFormation |

## quickstart

```bash
# clone
git clone https://github.com/smirsh72/ghosted.git
cd ghosted

# env files
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# add your OpenAI key to backend/.env

# backend
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
backend/.venv/bin/uvicorn main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload

# frontend (new terminal)
cd frontend && npm install && npm start
```

or just:

```bash
docker compose up --build
```

frontend at `localhost:3000`, backend at `localhost:8000`.

## how it works

1. enter your AWS Role ARN, External ID, and region in the UI
2. ghosted assumes that role via STS — no keys stored, no keys needed
3. type a command like "show me all running instances" or "create a bucket called logs-prod"
4. GPT-4o parses intent → ghosted executes via boto3 → results show up in chat

## project layout

```
backend/
  main.py              # app setup, middleware, routers
  routes/              # API endpoints (chat, ec2, s3)
  services/            # AI processing, AWS integrations, memory
frontend/
  src/                 # React app — config flow, chat, deployments dashboard
cloudformation/        # IAM role template
docker-compose.yml     # local full-stack runner
Makefile               # install/build/test shortcuts
```

## requirements

- Python 3.11+
- Node.js 18+
- an AWS account with an IAM role ghosted can assume
- an OpenAI API key

## security

- credentials flow through STS AssumeRole — nothing hardcoded, nothing stored
- `.env` files are gitignored
- the IAM role you deploy is scoped to only what ghosted needs

## license

MIT
