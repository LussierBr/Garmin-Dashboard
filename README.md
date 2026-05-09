This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.

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
