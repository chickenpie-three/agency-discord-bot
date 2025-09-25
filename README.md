# Marketing Agency AI Hub

A powerful Discord bot that serves as a complete marketing agency hub with AI-powered content creation, project management, and ClickUp integration.

## 🚀 Features

* **📁 File Upload & Analysis**: Upload .md files and get AI-powered project analysis
* **🚀 Dynamic Project Channels**: Automatically create Discord channels for new projects
* **📋 ClickUp Integration**: Seamless task and project management
* **🎨 AI Content Creation**: Blog posts, social media, campaigns with Nano Banana images
* **🤖 Conversational AI**: Natural language project management and task creation
* **📊 Analytics & Insights**: Performance tracking and optimization recommendations
* **🎯 Complete Workflows**: From file upload to campaign execution

## 🛠️ Setup Instructions

### Prerequisites

* Python 3.8 or higher
* Discord Bot Token
* Gemini API Key (for AI and image generation)
* ClickUp API Key (for project management)

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Configuration

Copy `env_template.txt` to `.env` and configure your settings:

```bash
cp env_template.txt .env
```

Edit `.env` with your credentials:

```env
# Discord Bot Configuration
DISCORD_BOT_TOKEN=your_discord_bot_token_here
AGENCY_NAME=Marketing Pro AI

# AI Configuration
GEMINI_API_KEY=your_gemini_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# ClickUp Integration
CLICKUP_API_KEY=your_clickup_api_key_here
CLICKUP_TEAM_ID=your_clickup_team_id_here
```

### 3. Discord Bot Setup

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to "Bot" section and create a bot
4. Copy the bot token to your `.env` file
5. Enable the following bot permissions:
   * Send Messages
   * Use Slash Commands
   * Embed Links
   * Attach Files
   * Read Message History
   * Manage Channels (for project channel creation)

### 4. Invite Bot to Server

Generate an invite link with the required permissions:

```
https://discord.com/api/oauth2/authorize?client_id=YOUR_BOT_CLIENT_ID&permissions=274877976576&scope=bot%20applications.commands
```

### 5. Run the Bot

```bash
python main.py
```

## 🎯 Usage

### Available Commands

#### `/upload` - Upload and Analyze Files

Upload .md or .txt files to create new projects with AI analysis.

```
/upload file:project-brief.md
```

#### `/project` - Create New Projects

Create new project channels with ClickUp integration.

```
/project project_name:"Q1 Marketing Campaign" description:"Complete marketing campaign for Q1"
```

#### `/content` - Content Creation

Generate blog posts, social media content, and campaigns with AI images.

```
/content content_type:blog topic:"AI Marketing Trends" keywords:"AI marketing, automation" include_image:True
```

#### `/clickup` - Task Management

Manage ClickUp tasks and projects.

```
/clickup action:list
/clickup action:create task_name:"Create blog post" description:"Write about AI trends"
```

#### `/help` - Show All Commands

Display all available commands and their usage.

## 🤖 AI-Powered Features

### File Analysis
- Upload project briefs, requirements, or specifications
- Get comprehensive AI analysis with actionable insights
- Automatic project channel creation
- ClickUp task generation suggestions

### Content Creation
- **Blog Posts**: SEO-optimized, comprehensive articles
- **Social Media**: Platform-specific content with hashtags
- **Campaigns**: Complete marketing campaign strategies
- **Images**: AI-generated visuals with Nano Banana

### Project Management
- **Dynamic Channels**: Automatic Discord channel creation
- **ClickUp Integration**: Seamless task and project sync
- **Timeline Tracking**: Deadline monitoring and notifications
- **Team Collaboration**: Role-based access and assignments

## 🎨 Image Generation

Powered by Gemini 2.5 Flash Image (Nano Banana):
- Professional marketing visuals
- Brand-consistent imagery
- Campaign-specific graphics
- Social media assets

## 📊 Analytics & Insights

- Performance data analysis
- ROI calculation and reporting
- Trend identification
- Actionable optimization recommendations

## 🔧 Advanced Configuration

### Custom AI Models

To use different AI models, update the `COMPLETION_MODEL` in your `.env`:

```env
# For OpenAI
COMPLETION_MODEL=gpt-4o

# For Gemini
COMPLETION_MODEL=gemini-2.0-flash-exp
```

### ClickUp Setup

1. Get your ClickUp API key from [ClickUp Settings](https://app.clickup.com/settings/apps)
2. Find your Team ID in ClickUp URL or API
3. Add both to your `.env` file

### WordPress Integration (Optional)

For automatic blog posting:

```env
WP_SITE_URL=https://yourwordpresssite.com
WP_USERNAME=your_wordpress_username
WP_APP_PASSWORD=your_wordpress_app_password
```

## 🐛 Troubleshooting

### Common Issues

1. **Bot not responding**: Check if bot token is correct and bot is online
2. **API errors**: Verify your AI model API keys are valid
3. **Permission errors**: Ensure bot has required Discord permissions
4. **ClickUp errors**: Verify ClickUp API key and Team ID
5. **File upload issues**: Check file format (.md, .txt supported)

### Logs

Check console output for detailed error messages and debugging information.

## 🚀 Deployment

### Railway Deployment

1. Connect your GitHub repository to Railway
2. Set environment variables in Railway dashboard
3. Deploy automatically on push

### Docker Deployment

```bash
docker build -t marketing-agency-bot .
docker run -d --env-file .env marketing-agency-bot
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

* [AutoAgent](https://github.com/HKUDS/AutoAgent) - The powerful LLM agent framework
* [Discord.py](https://github.com/Rapptz/discord.py) - Discord API wrapper for Python
* [Google Gemini](https://ai.google.dev/) - AI and image generation capabilities

---

**Made with ❤️ for marketing agencies and teams**

## About

Complete marketing agency hub with AI-powered content creation, project management, and ClickUp integration. Upload files, create projects, generate content, and manage campaigns all from Discord.