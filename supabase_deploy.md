# 🔋 STAFFVIRTUAL Discord Bot - Supabase Deployment Guide

## 🚀 Why Supabase is Perfect for This Project

- **PostgreSQL Database** - Store knowledge base with full-text search
- **Edge Functions** - Run the Discord bot serverlessly  
- **Storage** - Handle document uploads (PDFs, Word docs)
- **Real-time** - Instant updates to knowledge base
- **Cost Effective** - Much cheaper than Google Cloud
- **Easy Setup** - Simpler than traditional cloud platforms

## 📋 Prerequisites

1. **Supabase Account** (free tier available)
2. **GitHub Repository** (already created)
3. **Discord Bot Token**
4. **AI API Keys** (Gemini, OpenAI, or Anthropic)

## 🛠️ Setup Steps

### Step 1: Create Supabase Project

1. Go to [supabase.com](https://supabase.com)
2. Sign up/login
3. Click "New Project"
4. Choose organization and name: `staffvirtual-discord-bot`
5. Choose region closest to your users
6. Generate a strong database password
7. Click "Create new project"

### Step 2: Setup Database Schema

1. In Supabase Dashboard → SQL Editor
2. Copy and paste the contents of `supabase/migrations/20240101000000_initial_schema.sql`
3. Click "Run" to create all tables and functions

### Step 3: Configure Storage

1. Go to Storage in Supabase Dashboard
2. Create a new bucket called `documents`
3. Set it to private (for security)
4. Configure policies for document uploads

### Step 4: Deploy Edge Function

```bash
# Install Supabase CLI
npm install -g supabase

# Login to Supabase
supabase login

# Link your project
supabase link --project-ref YOUR_PROJECT_REF

# Deploy the edge function
supabase functions deploy discord-bot
```

### Step 5: Environment Variables

In Supabase Dashboard → Settings → Environment Variables, add:

```env
DISCORD_BOT_TOKEN=your_discord_bot_token
GEMINI_API_KEY=your_gemini_api_key
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
BRAND_NAME=STAFFVIRTUAL
BRAND_PRIMARY_COLOR=#1888FF
BRAND_SECONDARY_COLOR=#F8F8EB
BRAND_ACCENT_COLOR=#004B8D
```

### Step 6: Update Knowledge Manager for Supabase

The bot needs to be updated to use Supabase instead of local JSON files. Here's what needs to change:

1. **Database Connection** - Use Supabase client
2. **Knowledge Storage** - Store in PostgreSQL tables
3. **Document Storage** - Use Supabase Storage
4. **Search** - Use PostgreSQL full-text search + vector embeddings

## 🔄 Alternative Deployment Options

### Option A: Railway + Supabase (Recommended)
- Deploy bot on Railway (easier Python deployment)
- Use Supabase only for database and storage
- Best of both worlds

### Option B: Render + Supabase  
- Deploy bot on Render
- Use Supabase for data persistence
- Good free tier options

### Option C: Full Supabase (Advanced)
- Use Supabase Edge Functions for everything
- Requires rewriting bot in TypeScript/JavaScript
- Most cost-effective for high usage

## 📊 Database Schema Overview

Our Supabase setup includes:

**Tables:**
- `knowledge_base` - Scraped content and documents
- `uploaded_documents` - Track file uploads
- `scraped_urls` - Track website scraping
- `bot_interactions` - Usage analytics

**Features:**
- Full-text search on content
- Vector embeddings for semantic search
- Automatic timestamps
- Row Level Security (RLS)

## 🔧 Configuration for Railway + Supabase

Since Railway is easier for Python deployment, here's the hybrid approach:

1. **Deploy bot on Railway:**
   - Connect GitHub repo
   - Add environment variables
   - Automatic deployments

2. **Use Supabase for data:**
   - Update `knowledge_manager.py` to use Supabase
   - Store files in Supabase Storage
   - Query database for knowledge search

## 📈 Monitoring & Analytics

Supabase provides:
- Real-time database monitoring
- Query performance metrics
- Storage usage tracking
- Function execution logs

## 💰 Cost Estimation

**Supabase Free Tier:**
- 500MB database
- 1GB file storage
- 2 million edge function invocations
- Perfect for starting out

**Railway Free Tier:**
- $5/month in usage credits
- Great for small Discord bots

**Total:** Essentially free for moderate usage!

## 🚀 Next Steps

1. **Create Supabase project**
2. **Run database migrations**
3. **Update bot code for Supabase integration**
4. **Deploy on Railway**
5. **Test all functionality**

This setup gives you:
- 24/7 uptime
- Persistent knowledge base
- Scalable architecture
- Real-time updates
- Professional monitoring

---

**🎉 Your STAFFVIRTUAL bot will be production-ready with enterprise-grade infrastructure!**
