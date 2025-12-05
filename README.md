# Insider

Insider is an AI-powered automated trading interface for Polymarket, designed to democratize access to sophisticated prediction market strategies. By integrating real-time news aggregation with advanced Large Language Model (LLM) analysis using Google's Gemini, Insider identifies high-probability trade opportunities based on unfolding global events.

## Table of Contents
- [Architecture Overview](#architecture-overview)
- [Tech Stack](#tech-stack)
- [Setup & Data](#setup--data)
- [Local Development](#local-development)
    - [Prerequisites](#prerequisites)
    - [Backend Setup](#backend-setup)
    - [Frontend Setup](#frontend-setup)

## Architecture Overview

Insider operates on a "News → Insight → Trade" pipeline:

1.  **News Aggregation**: The backend (`/api/news/scan`) fetches real-time global news headlines via Google News RSS.
2.  **AI Analysis**: Google Gemini Pro 1.5 analyzes these headlines to identify relevance to active Polymarket prediction markets.
3.  **Market Mapping**: The LLM maps news events to specific market outcomes (e.g., "Will Bitcoin hit $100k in 2024?").
4.  **Probability Estimation**: The system estimates the probability of the outcome based on the news.
5.  **Kelly Criterion**: The system calculates the optimal bet size ("Edge") using the Kelly Criterion to maximize growth and minimize risk.
6.  **Trade Proposal**: High-value opportunities are presented to the user on the frontend.
7.  **Execution**: Users can execute trades via:
    *   **Demo Mode**: Risk-free simulation with PnL tracking.
    *   **Smart Wallet**: On-chain execution on Base L2 using Coinbase Smart Wallet.

## Tech Stack

*   **Frontend**: Next.js, React, Tailwind CSS, Wagmi, Viem.
*   **Backend**: Python, FastAPI.
*   **AI**: Google Gemini Pro 1.5.
*   **Blockchain**: Base Sepolia Testnet, Coinbase Smart Wallet.

## Setup & Data

### API Keys
You will need a Google Gemini API Key.
Create a `.env` file in the `backend/` directory:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

## Local Development

### Prerequisites
*   Node.js (v18+)
*   Python (v3.10+)
*   Git

### Backend Setup

1.  Navigate to the backend directory:
    ```bash
    cd backend
    ```
2.  Create and activate a virtual environment:
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```
3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
4.  Run the server:
    ```bash
    uvicorn main:app --reload
    ```
    The API will be available at `http://localhost:8000`.

### Frontend Setup

1.  Navigate to the frontend directory:
    ```bash
    cd frontend
    ```
2.  Install dependencies:
    ```bash
    npm install
    ```
3.  Run the development server:
    ```bash
    npm run dev
    ```
    The app will be available at `http://localhost:3000`.

## License
MIT
