# 🚀 STAFFVIRTUAL Discord Bot - Deployment Guide

## 📋 Prerequisites

1. **Google Cloud Account** with billing enabled
2. **GitHub Account** for code repository
3. **Discord Bot Token** from Discord Developer Portal
4. **AI API Keys** (Gemini, OpenAI, or Anthropic)

## 🔧 Local Setup

1. **Clone and setup:**
   ```bash
   git clone <your-repo-url>
   cd SV-Discord-Bot
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp env_template.txt .env
   # Edit .env with your tokens and API keys
   ```

3. **Test locally:**
   ```bash
   python main.py
   ```

## ☁️ Google Cloud Deployment

### Step 1: Setup Google Cloud Project

```bash
# Install Google Cloud SDK
# https://cloud.google.com/sdk/docs/install

# Login and set project
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Enable required APIs
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable storage.googleapis.com
```

### Step 2: Create Cloud Storage for Knowledge Base

```bash
# Create bucket for persistent data
gsutil mb gs://staffvirtual-bot-data

# Set bucket permissions
gsutil iam ch allUsers:objectViewer gs://staffvirtual-bot-data
```

### Step 3: Deploy with Cloud Build

```bash
# Submit build
gcloud builds submit --config cloudbuild.yaml

# Set environment variables in Cloud Run
gcloud run services update staffvirtual-discord-bot \
  --region=us-central1 \
  --set-env-vars="DISCORD_BOT_TOKEN=your_token_here" \
  --set-env-vars="GEMINI_API_KEY=your_gemini_key" \
  --set-env-vars="OPENAI_API_KEY=your_openai_key" \
  --set-env-vars="ANTHROPIC_API_KEY=your_anthropic_key"
```

### Step 4: Setup Continuous Deployment

1. **Connect GitHub to Cloud Build:**
   - Go to Google Cloud Console > Cloud Build > Triggers
   - Click "Create Trigger"
   - Connect your GitHub repository
   - Set trigger to run on push to main branch

2. **Configure trigger:**
   - Name: `deploy-staffvirtual-bot`
   - Event: Push to a branch
   - Branch: `^main$`
   - Configuration: Cloud Build configuration file
   - Location: `cloudbuild.yaml`

## 🌐 Alternative Deployment Options

### Railway (Easiest)
1. Push code to GitHub
2. Connect Railway to your repo
3. Add environment variables in Railway dashboard
4. Deploy automatically

### Render
1. Push code to GitHub  
2. Create new Web Service on Render
3. Connect your GitHub repo
4. Add environment variables
5. Deploy

### Heroku
```bash
# Install Heroku CLI
heroku create staffvirtual-discord-bot
heroku config:set DISCORD_BOT_TOKEN=your_token
heroku config:set GEMINI_API_KEY=your_key
git push heroku main
```

## 🔐 Environment Variables

Required variables for deployment:

```
DISCORD_BOT_TOKEN=your_discord_bot_token
GEMINI_API_KEY=your_gemini_api_key
OPENAI_API_KEY=your_openai_api_key (optional)
ANTHROPIC_API_KEY=your_anthropic_api_key (optional)
BRAND_NAME=STAFFVIRTUAL
BRAND_PRIMARY_COLOR=#1888FF
BRAND_SECONDARY_COLOR=#F8F8EB
BRAND_ACCENT_COLOR=#004B8D
```

## 📊 Monitoring

### Google Cloud Monitoring
- View logs: `gcloud logs tail`
- Monitor metrics in Cloud Console
- Set up alerts for errors

### Health Checks
The bot includes a health check endpoint for monitoring uptime.

## 🔄 Updates and Maintenance

1. **Code updates:** Push to GitHub main branch (auto-deploys)
2. **Environment variables:** Update in Cloud Run console
3. **Knowledge base:** Persisted in Cloud Storage
4. **Scaling:** Adjust in Cloud Run settings

## 🛠️ Troubleshooting

### Common Issues:

1. **Bot not responding:**
   - Check Discord bot token
   - Verify bot permissions in Discord server
   - Check Cloud Run logs

2. **AI responses failing:**
   - Verify API keys are set correctly
   - Check API quotas and billing
   - Review error logs

3. **Knowledge base not persisting:**
   - Check Cloud Storage bucket permissions
   - Verify storage integration

### Debug Commands:
```bash
# View logs
gcloud logs tail --follow

# Check service status
gcloud run services describe staffvirtual-discord-bot --region=us-central1

# Update service
gcloud run services replace service.yaml --region=us-central1
```

## 💡 Best Practices

1. **Security:** Never commit API keys to Git
2. **Monitoring:** Set up alerts for errors and downtime
3. **Backup:** Regular backups of knowledge base
4. **Updates:** Test changes locally before deploying
5. **Scaling:** Monitor usage and adjust resources as needed

## 📞 Support

For deployment issues:
1. Check the logs first
2. Review this guide
3. Check Google Cloud documentation
4. Contact support if needed

---

**🎉 Your STAFFVIRTUAL Discord Bot is now ready for 24/7 cloud deployment!**
