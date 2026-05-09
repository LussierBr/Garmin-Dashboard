# GarminAnalytics Dashboard 🏃‍♂️📊

A full-stack, hybrid web application designed to securely extract, visualize, and analyze health data using the Garmin Connect API. This project features a Generative UI AI agent for dynamic data exploration and a secure admin environment for predictive health modeling.

## 🏗 Architecture Overview

This application utilizes a decoupled architecture to handle complex data extraction and modern React rendering:

* **Frontend:** Next.js (App Router), React, Tailwind CSS, Recharts, Vercel AI SDK.
* **Backend:** Python, FastAPI, `garminconnect`, `scikit-learn`.
* **Database:** MongoDB.

## ✨ Core Features

The application is split into three distinct access zones:

1.  **7-Day Guest Snapshot:** A fast, temporary-session dashboard where users can log in with Garmin credentials to see interactive visualizations of their last 7 days of Health Stats (Stress, Steps, Body Battery). **Data is cached in memory/MongoDB and wiped after the session.**
2.  **AI Data Agent (Generative UI):** Powered by the Vercel AI SDK. Users can prompt the AI (e.g., *"Graph my stress vs. steps"*), and the LLM dynamically generates and renders custom Recharts components directly in the chat interface.
3.  **Admin Forecasting Vault:** A secured, private dashboard analyzing 6+ months of historical personal data. Utilizes Python-based Scikit-Learn regression models to forecast recovery and sleep metrics.

## 🚀 Getting Started

### Prerequisites
* Node.js (v18+)
* Python (3.10+)
* MongoDB Instance (Local or Atlas)

### Environment Setup

You will need to create a `.env.local` file in the root directory with the following structure:

```env
# Database
MONGODB_URI=your_mongodb_connection_string

# AI Provider (Choose your preferred provider)
OPENAI_API_KEY=your_api_key
# or GOOGLE_GENERATIVE_AI_API_KEY=your_api_key

# Admin Security
ADMIN_PASSPHRASE=your_secure_passphrase

# Garmin Credentials (For Admin/Demo backfill only)
GARMIN_EMAIL=your_email
GARMIN_PASSWORD=your_password