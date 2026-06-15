# Principal Agent Chatbot Frontend

A beautiful React-based frontend for the Principal Agent Python chatbot with a historical, cultural, and technical theme.

## Features

- 🎨 Modern UI with gradient colors and smooth animations
- 💬 Real-time chat interface with message history
- 📱 Responsive design for mobile and desktop
- 🚀 Built with Next.js and Tailwind CSS
- 🎯 Historical, cultural, and technical intelligence chatbot

## Color Scheme

- **Primary Cyan**: #5ce1e6
- **Light Cyan**: #0be1ff
- **Dark Cyan**: #1ea6bc
- **Accent Orange**: #f97821
- **Accent Alt Orange**: #f97921
- **White**: #FFFFFF

## Setup Instructions

### 1. Backend Setup (Python Flask API)

```bash
# Install Python dependencies
pip install flask flask-cors

# Run the Flask API server
python /vercel/share/v0-project/app.py
```

The backend will start at `http://localhost:5000`

### 2. Frontend Setup (Next.js React)

```bash
# Navigate to frontend directory
cd /vercel/share/v0-project/frontend

# Install dependencies
npm install
# or
pnpm install
# or
yarn install

# Run the development server
npm run dev
```

The frontend will start at `http://localhost:3000`

## Usage

1. Open your browser and navigate to `http://localhost:3000`
2. Start chatting with the Principal Agent chatbot
3. Ask questions about history, culture, or technology
4. Use the "Clear" button to start a new conversation

## Project Structure

```
frontend/
├── app/
│   ├── layout.tsx        # Root layout
│   ├── page.tsx          # Home page
│   └── globals.css       # Global styles
├── components/
│   ├── Chatbot.tsx       # Main chatbot container
│   ├── Message.tsx       # Individual message component
│   ├── ChatHeader.tsx    # Header with title and clear button
│   ├── ChatInput.tsx     # Input form component
│   └── WelcomeBanner.tsx # Welcome screen
├── package.json
├── tailwind.config.ts
├── tsconfig.json
└── next.config.js
```

## Environment Variables

The frontend connects to the backend API at `http://localhost:5000`. Make sure the Flask server is running before starting the frontend.

## Technologies

- **Next.js 14** - React framework
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **Axios** - HTTP client
- **React** - UI library

## Notes

- Make sure both servers (Flask backend on port 5000 and Next.js frontend on port 3000) are running
- The frontend will handle CORS requests to the backend automatically
- Session IDs are automatically managed for conversation history
