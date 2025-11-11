# CV Analyzer Backend - Deployment Guide

## Deploy to Render

### Step 1: Create GitHub Repository
1. Create a new repository on GitHub
2. Upload these files:
   - `main.py`
   - `schemas.py`
   - `requirements.txt`
   - `render.yaml`

### Step 2: Deploy on Render
1. Go to https://dashboard.render.com
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Render will auto-detect `render.yaml`
5. Add environment variable:
   - Key: `OPENAI_API_KEY`
   - Value: (your OpenAI API key from `.env`)
6. Click "Create Web Service"

### Step 3: Get API URL
After deployment, you'll get a URL like:
```
https://cv-analyzer-api.onrender.com
```

Use this URL in the frontend!

## Files Required

- ✅ main.py (v12.0.1)
- ✅ schemas.py
- ✅ requirements.txt
- ✅ render.yaml

## Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key (required)

## API Endpoints

- `GET /`: API info
- `POST /analyze-and-rewrite/`: Analyze and improve CV
- `POST /recommend-careers/`: Get career recommendations
- `GET /docs`: Interactive API documentation
