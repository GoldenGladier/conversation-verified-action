# Admin Agent

> **Agentic administrative assistant for dental clinics**

Admin Agent is a conversational AI prototype designed to transform natural-language conversations into **verifiable administrative actions**.

The current prototype focuses on appointment scheduling through Telegram. The agent can understand conversational messages, maintain context between messages, check available appointment slots, complete missing information, and request confirmation before executing an action.

## Current Flow

```text
User
  │
  ▼
Telegram
  │
  ▼
Admin Agent
  │
  ├── Intent Detection (OpenAI)
  │
  ├── Conversation Context
  │
  ├── Intent Validation
  │
  ├── Calendar
  │
  └── Verification
        │
        ├── Approve
        └── Reject
```

Example:

```text
User:
¿Qué horarios tienes disponibles mañana?

Agent:
Estos son los horarios disponibles para el 2026-09-12:

• 10:00
• 11:30
• 13:00
• 16:00
• 17:30

¿Cuál horario prefieres?

User:
A las 4

Agent:
Para poder agendar la cita necesito:

• el nombre del paciente

User:
Juan

Agent:
Encontré una posible acción para realizar:

Paciente: Juan
Fecha: 2026-09-12
Hora: 16:00
Duración: 30 minutos

Necesito tu confirmación antes de crear la cita.

[✅ Aprobar] [❌ Rechazar]
```

The appointment is only executed after the user explicitly approves the action.

---

# Features

### Conversational appointment scheduling

The agent does not require all appointment information in a single message.

For example:

```text
Agenda una cita con Juan mañana
```

The agent can identify that the date and patient are known and ask for the missing information.

The conversation can then continue:

```text
A las 4
```

followed by:

```text
30 minutos
```

or, if no duration is specified, the current default duration of **30 minutes** is used.

### Conversation context

The agent maintains the current conversation state and uses previous information to understand follow-up messages.

For example:

```text
¿Qué horarios tienes disponibles mañana?

A las 4

Juan
```

The agent understands that:

- `mañana` refers to the date from the previous message.
- `A las 4` selects the 16:00 slot.
- `Juan` is the patient for the appointment.

### Available slot lookup

The current calendar implementation provides mock availability:

```text
10:00
11:30
13:00
16:00
17:30
```

This is currently implemented as a mock `CalendarTool` and is intended to be replaced by a real calendar integration later.

### Verification before execution

Actions are never executed immediately.

The agent creates a `VerificationRequest` containing:

- Action
- Description
- Payload
- Status
- Creation timestamp
- Resolution timestamp

The user must explicitly approve or reject the request.

---

# Tech Stack

## Backend

- Python
- FastAPI
- OpenAI API
- Pydantic
- Pydantic Settings
- python-telegram-bot
- Pytest

## Current AI model

The `IntentDetector` currently uses:

```text
gpt-5.6-luna
```

through the OpenAI Responses API.

## Frontend

The frontend structure is reserved for a future web interface.

## Database

The current prototype uses in-memory state.

No persistent database is required yet.

---

# Project Structure

```text
admin-agent/
│
├── backend/
│   │
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   │
│   │   ├── agent/
│   │   │   ├── agent.py
│   │   │   ├── action_executor.py
│   │   │   ├── action_intent.py
│   │   │   ├── conversation_service.py
│   │   │   ├── conversation_state.py
│   │   │   ├── intent_detector.py
│   │   │   └── intent_validator.py
│   │   │
│   │   ├── calendar/
│   │   │   └── calendar_tool.py
│   │   │
│   │   ├── patients/
│   │   │
│   │   ├── telegram/
│   │   │   ├── bot.py
│   │   │   └── run.py
│   │   │
│   │   ├── verification/
│   │   │   └── verification_service.py
│   │   │
│   │   └── database/
│   │
│   ├── tests/
│   │
│   ├── requirements.txt
│   ├── .env
│   └── .env.example
│
├── frontend/
│   ├── app/
│   └── components/
│
├── docker-compose.yml
├── README.md
└── .gitignore
```

---

# Requirements

Before running the project, install:

- Python 3.11+ recommended
- Git
- A Telegram account
- A Telegram bot
- An OpenAI API key

---

# Installation

## 1. Clone the repository

```bash
git clone <REPOSITORY_URL>
cd admin-agent
```

Replace `<REPOSITORY_URL>` with the GitHub repository URL.

---

## 2. Enter the backend

```bash
cd backend
```

---

## 3. Create a virtual environment

### Windows PowerShell

```powershell
python -m venv .venv
```

Activate it:

```powershell
.venv\Scripts\Activate.ps1
```

If PowerShell prevents script execution, you can use:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then activate the environment again:

```powershell
.venv\Scripts\Activate.ps1
```

You should see:

```text
(.venv)
```

at the beginning of your terminal.

---

## 4. Install dependencies

```powershell
pip install -r requirements.txt
```

---

# Environment Variables

Create a `.env` file inside:

```text
backend/.env
```

Use `.env.example` as a template.

```env
TELEGRAM_BOT_TOKEN=
OPENAI_API_KEY=
```

Add the corresponding credentials.

### Important

**Never commit `.env` to Git.**

The `.gitignore` already excludes environment files.

Each developer should create their own local `.env`.

---

# Creating the Telegram Bot

The current prototype uses Telegram as its communication channel.

To create a bot:

1. Open Telegram.
2. Search for **BotFather**.
3. Start a conversation.
4. Use:

```text
/newbot
```

5. Follow the instructions.
6. BotFather will provide a bot token.
7. Add the token to:

```env
TELEGRAM_BOT_TOKEN=your_token_here
```

Do not commit or share the token publicly.

---

# Running the Application

The backend and Telegram bot currently run as separate processes.

## Terminal 1 — FastAPI

From:

```text
backend/
```

run:

```powershell
uvicorn app.main:app --reload
```

The API should be available locally at:

```text
http://127.0.0.1:8000
```

Health check:

```text
GET /health
```

Expected response:

```json
{
  "status": "ok",
  "service": "admin-agent"
}
```

---

## Terminal 2 — Telegram Bot

Open another terminal.

Navigate to:

```text
backend/
```

Activate the virtual environment:

```powershell
.venv\Scripts\Activate.ps1
```

Then run:

```powershell
python -m app.telegram.run
```

Expected output:

```text
Telegram bot is running...
```

The bot will start polling Telegram for messages.

---

# Testing the Agent

The project can also be tested without Telegram.

From:

```text
backend/
```

with the virtual environment activated:

```powershell
python -c "from app.agent.agent import Agent; a=Agent(); print(a.process_message('Agenda una cita con Juan mañana','test'))"
```

## Test conversational context

```powershell
python -c "from app.agent.agent import Agent; a=Agent(); print(a.process_message('Agenda una cita con Juan mañana','context-test')); print(a.process_message('A las 4','context-test')); print(a.process_message('30 minutos','context-test'))"
```

The final response should request verification.

---

# Testing Availability

The agent can query mock calendar availability.

Example:

```text
¿Qué horarios tienes disponibles mañana?
```

Current mock response:

```text
10:00
11:30
13:00
16:00
17:30
```

The selected slot can then be used as part of the appointment conversation:

```text
¿Qué horarios tienes disponibles mañana?

A las 4

Juan
```

The agent should generate a verification request using:

```text
Patient: Juan
Date: <selected date>
Time: 16:00
Duration: 30 minutes
```

---

# Verification Flow

Every appointment creation goes through the verification system.

```text
User message
     │
     ▼
IntentDetector
     │
     ▼
ActionIntent
     │
     ▼
IntentValidator
     │
     ▼
VerificationService
     │
     ▼
Pending VerificationRequest
     │
     ├───────────────┐
     ▼               ▼
  Approve          Reject
     │               │
     ▼               ▼
ActionExecutor     End
     │
     ▼
CalendarTool
```

The Telegram interface represents the verification request with two buttons:

```text
[✅ Aprobar] [❌ Rechazar]
```

---

# Current Architecture

The project is intentionally divided into independent components.

## Agent

`app/agent/agent.py`

Coordinates the overall process:

- Receives user messages.
- Retrieves conversation state.
- Builds context.
- Detects intent.
- Merges conversational information.
- Validates required fields.
- Creates verification requests.
- Executes approved actions.

## Intent Detector

`app/agent/intent_detector.py`

Uses the OpenAI API to transform natural language into a structured `ActionIntent`.

Currently supported actions:

```text
CREATE_CALENDAR_EVENT
GET_AVAILABLE_SLOTS
```

## Conversation Service

`app/agent/conversation_service.py`

Maintains the current conversational state.

The current implementation stores conversations in memory.

This means that restarting the application clears the conversation state.

## Calendar Tool

`app/calendar/calendar_tool.py`

Currently provides a mock calendar implementation.

It can:

- Return available slots.
- Create mock calendar events.

A real Google Calendar integration can later replace this implementation.

## Verification Service

`app/verification/verification_service.py`

Manages pending actions and their lifecycle:

```text
PENDING
   │
   ├── APPROVED
   │
   └── REJECTED
```

## Action Executor

`app/agent/action_executor.py`

Executes approved actions.

Currently it supports:

```text
CREATE_CALENDAR_EVENT
```

---

# Important Development Notes

## Conversation state is currently in memory

The prototype does not use a database for conversations or verification requests.

Restarting the application will clear:

- Conversation state
- Pending verification requests
- Mock calendar state

This is intentional for the current prototype.

---

## Calendar is currently a mock

No real calendar events are currently created.

`CalendarTool` simulates calendar operations so that the agent architecture can be developed before integrating an external calendar provider.

---

## Telegram is only the current communication adapter

The core agent is not designed around Telegram.

The intended architecture is:

```text
              Admin Agent
                   │
             Conversation
                   │
          ┌────────┼────────┐
          │        │        │
       Telegram  WhatsApp   Web
          │        │        │
          └────────┼────────┘
                   │
                  Agent
```

This allows another communication channel to be added later without rewriting the core agent logic.

---

# Development Roadmap

The current prototype is focused on proving the core concept.

Potential next steps:

- [ ] Improve conversational state management
- [ ] Add patient management
- [ ] Add appointment cancellation
- [ ] Add appointment rescheduling
- [ ] Add more administrative actions
- [ ] Improve verification workflow
- [ ] Add persistent database
- [ ] Replace mock calendar with Google Calendar
- [ ] Add real calendar conflict validation
- [ ] Add web interface
- [ ] Add additional communication channels
- [ ] Improve automated tests
- [ ] Add production deployment configuration

---

# Git Workflow

Before starting development:

```powershell
git pull
```

Create a branch for your work:

```powershell
git checkout -b feature/my-feature
```

After making changes:

```powershell
git status
git add .
git commit -m "Add my feature"
git push -u origin feature/my-feature
```

Create a Pull Request on GitHub when the feature is ready.

---

# Security

Never commit:

```text
.env
API keys
Telegram bot tokens
credentials
private certificates
```

Before pushing changes, verify:

```powershell
git status
```

Make sure `.env` is not listed as a file to commit.

---

# Project Goal

The long-term goal of Admin Agent is not simply to build a chatbot that schedules appointments.

The goal is to build an **administrative agent capable of understanding conversations and converting them into verifiable actions**.

For example:

```text
Conversation
     ↓
Understand intent
     ↓
Identify required information
     ↓
Use external tools
     ↓
Propose an action
     ↓
Human verification
     ↓
Execute action
```

The agent should eventually be able to assist with multiple administrative workflows while keeping a human in control of consequential actions.

---

# Team

Hackathon project — **Admin Agent**

Built for the **Agents, Everywhere: Bots, Channels, & More — Global Hackathon**.
