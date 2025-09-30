import discord
from discord.ext import commands
import asyncio
import logging
import os
from dotenv import load_dotenv
import io
import json
import tempfile
import re
import requests
from datetime import datetime, timedelta
import aiofiles
import uuid
from urllib.parse import urlparse
import asyncio
import signal
import sys
import traceback
import time
from aiohttp import web
# Voice meeting imports (simplified)
from concurrent.futures import ThreadPoolExecutor
import threading

# Reconnect FIX - when disconnected or restarted
class ResumeHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        bot.add_listener(self.on_resumed, "on_resumed")
        bot.add_listener(self.on_disconnect, "on_disconnect")
        self.last_sync_time = 0
        self.sync_cooldown = 300  # 5 minutes cooldown between syncs
        self.daily_sync_count = 0
        self.daily_sync_reset_time = 0

    def can_sync_commands(self):
        """Check if we can sync commands without hitting rate limits"""
        current_time = time.time()
        
        # Reset daily counter if it's a new day
        if current_time - self.daily_sync_reset_time > 86400:  # 24 hours
            self.daily_sync_count = 0
            self.daily_sync_reset_time = current_time
        
        # Check daily limit (200 commands per day)
        if self.daily_sync_count >= 190:  # Leave some buffer
            logger.warning(f"⚠️ Daily sync limit reached ({self.daily_sync_count}/200). Skipping sync.")
            return False
        
        # Check cooldown period
        if current_time - self.last_sync_time < self.sync_cooldown:
            logger.info(f"⏳ Sync cooldown active. Next sync in {self.sync_cooldown - (current_time - self.last_sync_time):.0f}s")
            return False
        
        return True

    async def on_resumed(self):
        print("🔄 Bot resume event detected! Checking command status...")
        try:
            # Re-login if needed
            if not self.bot.is_ready():
                await self.bot.login(os.getenv("DISCORD_TOKEN"))
                print("✅ Reconnect login successful.")
            
            # Check if commands are already working
            try:
                # Test if commands are accessible without syncing
                command_count = len(self.bot.tree.get_commands())
                if command_count > 0:
                    print(f"✅ Commands already available: {command_count} commands")
                    logger.info(f"✅ Commands already available: {command_count} commands")
                    return
            except Exception:
                pass  # Commands might not be accessible, continue with sync check
            
            # Only sync if we can do so safely
            if self.can_sync_commands():
                try:
                    synced = await self.bot.tree.sync()
                    self.last_sync_time = time.time()
                    self.daily_sync_count += 1
                    print(f"✅ Commands re-synced after resume: {len(synced)} commands available")
                    logger.info(f"✅ Commands re-synced after resume: {len(synced)} commands available")
                except Exception as sync_error:
                    if "429" in str(sync_error) or "rate limit" in str(sync_error).lower():
                        print(f"⚠️ Rate limited - commands may still work. Error: {sync_error}")
                        logger.warning(f"⚠️ Rate limited - commands may still work. Error: {sync_error}")
                    else:
                        print(f"❌ Command sync failed after resume: {sync_error}")
                        logger.error(f"❌ Command sync failed after resume: {sync_error}")
            else:
                print("⏳ Skipping command sync due to rate limits - commands should still work")
                logger.info("⏳ Skipping command sync due to rate limits - commands should still work")
            
            # Verify bot is ready
            if self.bot.is_ready():
                print("✅ Bot fully operational")
                logger.info("✅ Bot fully operational")
            else:
                print("⚠️ Bot reconnected but not fully ready")
                logger.warning("⚠️ Bot reconnected but not fully ready")
                
        except Exception as e:
            print(f"❌ Resume failed: {e}")
            logger.error(f"❌ Resume failed: {e}")

    async def on_disconnect(self):
        print("⚠️ Bot disconnected - will attempt to restore commands on reconnect")
        logger.warning("⚠️ Bot disconnected - will attempt to restore commands on reconnect")
    
    async def on_error(self, event, *args, **kwargs):
        """Handle Discord client errors"""
        logger.error(f"Discord client error in event {event}: {args}")
        import traceback
        logger.error(f"Error traceback: {traceback.format_exc()}")

# Simplified Voice Meeting System (without discord.sinks)
class SimpleMeetingTracker:
    """Simple meeting tracker without audio recording"""
    
    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.participants = set()
        self.join_times = {}
        self.activity_log = []
        
    def track_user_join(self, user):
        """Track when a user joins the voice channel"""
        self.participants.add(user.name)
        self.join_times[user.name] = datetime.now()
        self.activity_log.append({
            'user': user.name,
            'action': 'joined',
            'timestamp': datetime.now().strftime("%H:%M:%S")
        })
        logger.info(f"Meeting participant joined: {user.name}")
        
    def track_user_leave(self, user):
        """Track when a user leaves the voice channel"""
        if user.name in self.participants:
            self.participants.discard(user.name)
            self.activity_log.append({
                'user': user.name,
                'action': 'left',
                'timestamp': datetime.now().strftime("%H:%M:%S")
            })
            logger.info(f"Meeting participant left: {user.name}")
    
    def add_manual_note(self, note, user="System"):
        """Add a manual note to the meeting log"""
        self.activity_log.append({
            'user': user,
            'action': 'note',
            'text': note,
            'timestamp': datetime.now().strftime("%H:%M:%S")
        })
    
    def get_meeting_summary(self):
        """Get a summary of meeting activity"""
        return {
            'participants': list(self.participants),
            'activity_log': self.activity_log,
            'total_participants': len(self.join_times)
        }

# AI Libraries with Nano Banana support
try:
    from google import genai
    from google.genai import types
    NANO_BANANA_AVAILABLE = True
except ImportError:
    try:
        import google.generativeai as genai
        types = None
        NANO_BANANA_AVAILABLE = False
    except ImportError:
        genai = None
        types = None
        NANO_BANANA_AVAILABLE = False

try:
    import openai
except ImportError:
    openai = None

try:
    from PIL import Image
except ImportError:
    Image = None

# Knowledge management
from knowledge_manager import KnowledgeManager

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

class CreativeStudioBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix='!studio ',
            intents=intents,
            description='Creative Studio AI - Unlimited Creative Expression & Artistic Content Hub'
        )
        
        # Creative Studio configuration
        def parse_color(color_str, default):
            try:
                if not color_str or color_str.strip() == '':
                    return int(default.replace('#', ''), 16)
                color_clean = color_str.replace('#', '').strip()
                return int(color_clean, 16) if len(color_clean) == 6 else int(default.replace('#', ''), 16)
            except (ValueError, AttributeError):
                return int(default.replace('#', ''), 16)
        
        self.studio_config = {
            'name': os.getenv('STUDIO_NAME', 'Creative Studio AI'),
            'primary_color': parse_color(os.getenv('STUDIO_PRIMARY_COLOR'), '#8b5cf6'),   # Creative Purple
            'secondary_color': parse_color(os.getenv('STUDIO_SECONDARY_COLOR'), '#f3f4f6'), # Soft Gray
            'accent_color': parse_color(os.getenv('STUDIO_ACCENT_COLOR'), '#ec4899'),     # Vibrant Pink
            'warning_color': parse_color(os.getenv('STUDIO_WARNING_COLOR'), '#f59e0b'),   # Warm Orange
            'error_color': parse_color(os.getenv('STUDIO_ERROR_COLOR'), '#ef4444'),       # Error Red
            'creative_colors': {
                'Content Creation': '#8b5cf6',      # Purple - Imagination
                'Visual Arts': '#ec4899',           # Pink - Creativity
                'Storytelling': '#f59e0b',          # Orange - Warmth
                'Design': '#06b6d4',                # Cyan - Innovation
                'Music & Audio': '#10b981',         # Green - Harmony
                'Photography': '#6366f1',           # Indigo - Depth
                'Writing': '#84cc16',               # Lime - Fresh Ideas
                'Animation': '#f97316'              # Orange - Energy
            },
            'style_guidelines': (
                "Bold, innovative, and artistically driven creative studio aesthetic. "
                "Unlimited creative expression with no corporate constraints. "
                "Experimental, boundary-pushing, and authentically artistic. "
                "Freedom to explore any creative direction or style. "
                "Inspiring, imaginative, and genuinely creative."
            ),
            'voice_tone': (
                "Creative, inspiring, and authentically artistic. "
                "Unlimited imagination with no corporate boundaries. "
                "Bold, experimental, and genuinely creative. "
                "Passionate about art, creativity, and self-expression. "
                "Always pushing creative boundaries and exploring new ideas."
            ),
            'tagline': "Unlimited Creative Expression. Art Without Boundaries. Pure Imagination.",
            'core_values': [
                "Creative Freedom Over Constraints",
                "Artistic Expression Without Limits",
                "Imagination First, Rules Second",
                "Innovation Through Pure Creativity",
                "Authentic Artistic Vision"
            ]
        }
        
        self.ai_clients = self._initialize_ai_clients()
        self.knowledge_manager = KnowledgeManager()
        
        # ClickUp integration
        self.clickup_config = {
            'api_key': os.getenv('CLICKUP_TOKEN') or os.getenv('CLICKUP_API_KEY'),
            'team_id': os.getenv('CLICKUP_TEAM_ID'),
            'base_url': 'https://api.clickup.com/api/v2'
        }
        
        # Project management
        self.active_projects = {}
        self.project_channels = {}
        
        # Stability monitoring
        self.start_time = datetime.now()
        self.error_count = 0
        self.max_errors = 10
        
        # UAT Testing SOPs - Marketing Agency Specific
        self.uat_sops = {
            "1. Branding Consistency": [
                "Logo loads correctly (favicon + header logo)",
                "Color codes match brand guidelines (HEX values)",
                "Fonts match brand rules (headings vs. body)",
                "Buttons and CTAs styled consistently",
                "Brand voice and tone maintained across content"
            ],
            "2. Page & Layout Verification": [
                "All navigation links (header/footer) point to correct pages",
                "Homepage sections (hero, featured content, feeds) render without errors",
                "Core pages exist (Home, Categories, Article template, Contact, Legal)",
                "Responsive design check: Desktop → Tablet → Mobile layouts align correctly",
                "No overlapping elements or broken layouts"
            ],
            "3. Content Integrity": [
                "Article/category pages load without 404s",
                "Content matches SEO-friendly URL structure",
                "RSS feeds display fresh articles (not broken)",
                "Images load correctly with alt text present",
                "Internal links → No broken or redirecting loops",
                "External links → Verify reachable"
            ],
            "4. Plugin & Feature Functionality": [
                "Forms: Submit test entries → verify data captured + GHL tagging",
                "RSS feeds: Populate with correct content",
                "Ads: Ad Cash zones display correctly (header, sidebar, inline)",
                "Affiliate links: Redirect through management plugin (e.g., Pretty Links)",
                "SMTP email: Test site emails send successfully"
            ],
            "5. SEO & Analytics": [
                "Yoast SEO fields populated (title, description, keyphrase)",
                "Meta description ≤ 160 chars",
                "Sitemap accessible at /sitemap_index.xml",
                "Google Analytics (GA4) firing events (pageviews, conversions)",
                "Google Tag Manager tags working (forms, buttons, opt-ins)"
            ],
            "6. Performance & Security": [
                "SSL certificate active (HTTPS enforced)",
                "Page speed check (LCP, FID, CLS from Core Web Vitals)",
                "No insecure content warnings (mixed HTTP/HTTPS)",
                "Security plugins (Wordfence/iThemes) installed & active",
                "Cookie consent banner appears + functions properly"
            ],
            "7. Monetization": [
                "Ads visible on correct zones (home, category, article)",
                "No broken ad tags or empty containers",
                "Affiliate CTA buttons/links function",
                "Newsletter opt-ins trigger correct welcome sequence",
                "Revenue tracking and conversion funnels working"
            ],
            "8. Social & Integrations": [
                "Social media icons → point to correct branded accounts",
                "Embedded social feeds (if any) display without error",
                "Forms → check data reaches GoHighLevel CRM",
                "Emails → verify autoresponder sequence fires",
                "Third-party integrations functioning properly"
            ]
        }
        
        # Agency DNA for marketing excellence
        self.studio_dna = """
        Creative Studio AI — Unlimited Creative Expression Hub
        
        Studio Profile:
        - Mission: Unleash unlimited creative potential through AI-powered artistic expression, free from corporate constraints.
        - Vision: Become the ultimate creative companion for artists, creators, and anyone seeking authentic artistic expression.
        - Ideal Creators: Artists, writers, designers, musicians, filmmakers, content creators, and anyone with creative vision.
        - Creative Focus: Pure artistic expression, experimental content, boundary-pushing creativity, and authentic self-expression.
        
        Creative Portfolio:
        1) Visual Arts & Design
           - AI-generated artwork in any style or medium
           - Experimental visual concepts and artistic exploration
           - Custom illustrations, digital art, and creative imagery
           - Artistic photography and visual storytelling
        
        2) Writing & Storytelling
           - Creative writing in any genre or style
           - Poetry, fiction, screenplays, and experimental literature
           - Personal essays, creative non-fiction, and artistic expression
           - Unconventional narratives and boundary-pushing stories
        
        3) Content Creation
           - Social media content with artistic flair
           - Creative blog posts and articles
           - Experimental content formats and styles
           - Authentic, non-corporate messaging and communication
        
        4) Creative Projects
           - Art direction and creative concept development
           - Experimental multimedia projects
           - Creative campaign ideas and artistic concepts
           - Unconventional creative solutions and approaches
        
        5) Artistic Collaboration
           - Creative brainstorming and ideation
           - Artistic feedback and creative direction
           - Experimental creative techniques and methods
           - Pure creative expression without commercial constraints
        
        AI-Powered Creative Capabilities:
        - Unlimited creative content generation
        - Artistic image creation with Nano Banana integration
        - Creative writing in any style or genre
        - Experimental and boundary-pushing content creation
        - Pure artistic expression without corporate influence
        
        Creative Identity:
        - Palette: Creative Purple (#8b5cf6), Vibrant Pink (#ec4899), Warm Orange (#f59e0b)
        - Style: Bold, innovative, artistically driven, experimental
        - Voice: Creative, inspiring, authentically artistic, boundary-pushing
        - Approach: Pure creativity, unlimited imagination, artistic freedom
        
        Key Differentiators:
        - Complete creative freedom without corporate constraints
        - AI-powered artistic expression with unlimited possibilities
        - Experimental and boundary-pushing creative approaches
        - Authentic artistic vision and genuine creativity
        - Natural language interaction for complex creative projects
        
        Creative Success Metrics:
        - Artistic expression and creative fulfillment
        - Creative project completion and artistic satisfaction
        - Creative boundary exploration and artistic growth
        - Authentic creative expression and artistic vision
        - Creative inspiration and artistic development
        """
    
    def _initialize_ai_clients(self):
        """Initialize AI clients with Nano Banana support"""
        clients = {}
        gemini_key = os.getenv('GEMINI_API_KEY')
        
        if gemini_key and genai:
            try:
                if NANO_BANANA_AVAILABLE and types:
                    clients['nano_banana'] = genai.Client(api_key=gemini_key)
                    logger.info("Nano Banana client initialized!")
                else:
                    genai.configure(api_key=gemini_key)
                    clients['gemini'] = genai.GenerativeModel('gemini-1.5-flash')
                    logger.info("Gemini client initialized")
            except Exception as e:
                logger.error(f"Gemini init error: {e}")
        
        openai_key = os.getenv('OPENAI_API_KEY')
        if openai_key and openai:
            try:
                clients['openai'] = openai.OpenAI(api_key=openai_key)
                logger.info("OpenAI client initialized")
            except Exception as e:
                logger.error(f"OpenAI init error: {e}")
        
        return clients
    
    async def _clickup_request(self, endpoint: str, method: str = 'GET', data: dict = None):
        """Make ClickUp API requests"""
        if not self.clickup_config['api_key']:
            return None
        
        headers = {
            'Authorization': self.clickup_config['api_key'],
            'Content-Type': 'application/json'
        }
        
        url = f"{self.clickup_config['base_url']}/{endpoint}"
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=data)
            elif method == 'PUT':
                response = requests.put(url, headers=headers, json=data)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"ClickUp API error: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"ClickUp request error: {e}")
            return None
    
    async def get_clickup_tasks(self, list_id: str = None, assignee: str = None):
        """Get ClickUp tasks"""
        endpoint = f"team/{self.clickup_config['team_id']}/task"
        params = []
        if list_id:
            params.append(f"list_ids[]={list_id}")
        if assignee:
            params.append(f"assignees[]={assignee}")
        
        if params:
            endpoint += "?" + "&".join(params)
        
        return await self._clickup_request(endpoint)
    
    async def create_clickup_task(self, list_id: str, name: str, description: str = "", assignee: str = None, due_date: str = None):
        """Create a new ClickUp task"""
        data = {
            "name": name,
            "description": description,
            "list_id": list_id
        }
        
        if assignee:
            data["assignees"] = [assignee]
        if due_date:
            data["due_date"] = due_date
        
        return await self._clickup_request(f"list/{list_id}/task", 'POST', data)
    
    async def create_clickup_list(self, folder_id: str, name: str, description: str = ""):
        """Create a new ClickUp list"""
        data = {
            "name": name,
            "description": description
        }
        
        return await self._clickup_request(f"folder/{folder_id}/list", 'POST', data)
    
    async def analyze_uploaded_file(self, file_content: str, filename: str):
        """Analyze uploaded file and extract actionable insights"""
        try:
            prompt = f"""
            Analyze this uploaded file: {filename}
            
            File Content:
            {file_content}
            
            Please provide:
            1. **Project Summary**: What is this project about?
            2. **Key Requirements**: What are the main deliverables and requirements?
            3. **Timeline**: Any deadlines or milestones mentioned?
            4. **Stakeholders**: Who are the key people involved?
            5. **Action Items**: What specific tasks need to be created?
            6. **Campaign Ideas**: If this is marketing-related, what campaigns could be created?
            7. **Content Opportunities**: What content pieces could be generated?
            8. **Wireframe Suggestions**: If applicable, what wireframes or designs are needed?
            
            Format your response as a structured analysis that can be used to create ClickUp tasks and Discord project channels.
            """
            
            return await self._get_ai_response(prompt, "Project Analysis Expert")
        except Exception as e:
            logger.error(f"File analysis error: {e}")
            return f"Error analyzing file: {str(e)}"
    
    async def create_project_channel(self, guild, project_name: str, project_data: dict):
        """Create a dedicated Discord channel for a project"""
        try:
            # Clean project name for channel
            channel_name = re.sub(r'[^a-z0-9\-_]', '', project_name.lower().replace(' ', '-'))
            if len(channel_name) > 50:
                channel_name = channel_name[:50]
            
            # Create text channel
            channel = await guild.create_text_channel(
                name=f"project-{channel_name}",
                topic=f"Project: {project_name} | Created: {datetime.now().strftime('%Y-%m-%d')}"
            )
            
            # Create project info embed
            embed = discord.Embed(
                title=f"🚀 Project: {project_name}",
                description="New project channel created with AI analysis",
                color=self.studio_config['primary_color']
            )
            
            embed.add_field(
                name="📋 Project Summary",
                value=project_data.get('summary', 'Analysis in progress...'),
                inline=False
            )
            
            embed.add_field(
                name="⏰ Timeline",
                value=project_data.get('timeline', 'To be determined'),
                inline=True
            )
            
            embed.add_field(
                name="👥 Stakeholders",
                value=project_data.get('stakeholders', 'To be identified'),
                inline=True
            )
            
            embed.add_field(
                name="📝 Next Steps",
                value="1. Review AI analysis\n2. Create ClickUp tasks\n3. Set up project timeline\n4. Assign team members",
                inline=False
            )
            
            await channel.send(embed=embed)
            
            # Store project info
            project_id = str(uuid.uuid4())
            self.active_projects[project_id] = {
                'name': project_name,
                'channel_id': channel.id,
                'data': project_data,
                'created_at': datetime.now(),
                'status': 'active'
            }
            
            self.project_channels[channel.id] = project_id
            
            return channel, project_id
            
        except Exception as e:
            logger.error(f"Channel creation error: {e}")
            return None, None
    
    async def analyze_website(self, url: str):
        """Analyze a website for UAT testing"""
        try:
            # Validate URL
            parsed_url = urlparse(url)
            if not parsed_url.scheme:
                url = f"https://{url}"
            
            # Headers to mimic a real browser and avoid 406 errors
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0'
            }
            
            # Basic website analysis with browser headers
            response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
            response.raise_for_status()
            
            # Extract basic info
            content = response.text
            title_match = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE | re.DOTALL)
            title = title_match.group(1).strip() if title_match else "No title found"
            
            # Check for common elements
            has_forms = bool(re.search(r'<form', content, re.IGNORECASE))
            has_images = bool(re.search(r'<img', content, re.IGNORECASE))
            has_scripts = bool(re.search(r'<script', content, re.IGNORECASE))
            has_css = bool(re.search(r'<style|<link.*css', content, re.IGNORECASE))
            
            # Check HTTPS
            is_https = url.startswith('https://')
            
            # Basic performance check
            load_time = response.elapsed.total_seconds()
            
            return {
                "url": url,
                "title": title,
                "status_code": response.status_code,
                "load_time": load_time,
                "is_https": is_https,
                "has_forms": has_forms,
                "has_images": has_images,
                "has_scripts": has_scripts,
                "has_css": has_css,
                "content_length": len(content)
            }
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 406:
                return {"error": f"Website blocked automated requests (406 Not Acceptable). This site may require manual testing or have anti-bot protection."}
            elif e.response.status_code == 403:
                return {"error": f"Website access forbidden (403). This site may block automated requests or require authentication."}
            elif e.response.status_code == 404:
                return {"error": f"Website not found (404). Please check the URL is correct."}
            else:
                return {"error": f"HTTP Error {e.response.status_code}: {str(e)}"}
        except requests.exceptions.RequestException as e:
            return {"error": f"Network error: {str(e)}"}
        except Exception as e:
            return {"error": f"Analysis error: {str(e)}"}
    
    async def generate_uat_report(self, website_data: dict, custom_notes: str = ""):
        """Generate comprehensive UAT testing report following 8-step workflow"""
        try:
            prompt = f"""
            Generate a comprehensive UAT (User Acceptance Testing) report for this website following the 8-step bot workflow:
            
            Website Data:
            - URL: {website_data.get('url', 'N/A')}
            - Title: {website_data.get('title', 'N/A')}
            - Status Code: {website_data.get('status_code', 'N/A')}
            - Load Time: {website_data.get('load_time', 'N/A')} seconds
            - HTTPS: {'✅' if website_data.get('is_https') else '❌'}
            - Has Forms: {'✅' if website_data.get('has_forms') else '❌'}
            - Has Images: {'✅' if website_data.get('has_images') else '❌'}
            - Has Scripts: {'✅' if website_data.get('has_scripts') else '❌'}
            - Has CSS: {'✅' if website_data.get('has_css') else '❌'}
            - Content Length: {website_data.get('content_length', 'N/A')} characters
            
            Custom Notes: {custom_notes if custom_notes else 'None provided'}
            
            Please provide a detailed UAT report following this 8-step workflow:
            
            **STEP 1: Site Crawl & Page Detection**
            - Detect missing/broken pages (404/500 errors)
            - Verify core pages exist (Home, Categories, Articles, Contact, Legal)
            - Check for broken internal links and redirects
            
            **STEP 2: Branding Rules Validation**
            - Validate colors, logos, fonts against brand guidelines
            - Check HEX color codes and font consistency
            - Verify favicon and header logo loading
            
            **STEP 3: Layout Tests (Mobile-First)**
            - Screen-size rendering: Desktop → Tablet → Mobile
            - No overlapping elements or broken layouts
            - Responsive design verification
            
            **STEP 4: Automated SEO Scan**
            - Verify titles, meta descriptions (≤160 chars)
            - Check sitemap accessibility (/sitemap_index.xml)
            - SEO-friendly URL structure validation
            
            **STEP 5: Form Submission Test**
            - Push dummy data, confirm GHL tagging
            - Verify data reaches GoHighLevel CRM
            - Test SMTP email functionality
            
            **STEP 6: Analytics Ping Test**
            - Confirm GA4 + GTM tags fire correctly
            - Verify pageviews and conversion tracking
            - Check event tracking for forms and buttons
            
            **STEP 7: Ad & Affiliate Check**
            - Confirm ad tags render in correct zones
            - Verify affiliate links redirect properly
            - Check monetization elements function
            
            **STEP 8: Security & Compliance**
            - SSL certificate and HTTPS enforcement
            - Cookie consent banner functionality
            - GDPR compliance verification
            
            For each of the 8 SOP categories, provide:
            - ✅ **PASS** - What's working well
            - ⚠️ **WARNING** - Areas that need attention  
            - ❌ **FAIL** - Critical issues that must be fixed
            - 📝 **RECOMMENDATIONS** - Specific improvement suggestions
            
            Focus on marketing agency priorities: branding consistency, conversion optimization, analytics tracking, and monetization elements.
            
            Format as a professional UAT report with clear sections and actionable insights for marketing teams.
            """
            
            return await self._get_ai_response(prompt, "Marketing UAT Testing Expert", max_length=3000)
            
        except Exception as e:
            logger.error(f"UAT report generation error: {e}")
            self.error_count += 1
            return f"Error generating UAT report: {str(e)}"
    
    def track_error(self, error_msg: str):
        """Track errors and handle cleanup if too many occur"""
        self.error_count += 1
        logger.error(f"Error #{self.error_count}: {error_msg}")
        
        if self.error_count >= self.max_errors:
            logger.critical(f"Too many errors ({self.error_count}), considering restart...")
            # Could implement auto-restart logic here if needed
    
    def cleanup_memory(self):
        """Clean up memory and reset error count"""
        try:
            # Clear old project data if too many
            if len(self.active_projects) > 50:
                # Keep only recent projects
                sorted_projects = sorted(self.active_projects.items(), 
                                       key=lambda x: x[1].get('created_at', datetime.min), 
                                       reverse=True)
                self.active_projects = dict(sorted_projects[:25])
                logger.info("Cleaned up old project data")
            
            # Reset error count periodically
            if self.error_count > 0:
                self.error_count = max(0, self.error_count - 1)
                
        except Exception as e:
            logger.error(f"Memory cleanup error: {e}")
    
    def get_uptime(self):
        """Get bot uptime"""
        return datetime.now() - self.start_time
    
    async def _generate_nano_banana_image(self, prompt: str, style: str = "professional"):
        """Generate images using Nano Banana with Modern Weave™ branding"""
        try:
            if 'nano_banana' not in self.ai_clients:
                return {"success": False, "error": "Nano Banana not available"}
            
            # Style-specific configurations
            style_configs = {
                "professional": {
                    "tone": "clean, corporate, business-focused",
                    "colors": "Professional Blue (#2563eb), Success Green (#10b981), Neutral Grays",
                    "mood": "serious, trustworthy, authoritative"
                },
                "creative": {
                    "tone": "artistic, innovative, visually striking",
                    "colors": "Vibrant colors, creative gradients, bold contrasts",
                    "mood": "energetic, inspiring, dynamic"
                },
                "casual": {
                    "tone": "friendly, approachable, relaxed",
                    "colors": "Warm colors, soft tones, inviting palette",
                    "mood": "welcoming, comfortable, accessible"
                },
                "minimalist": {
                    "tone": "simple, clean, uncluttered",
                    "colors": "Monochrome, single accent color, lots of white space",
                    "mood": "calm, focused, elegant"
                },
                "modern": {
                    "tone": "contemporary, sleek, cutting-edge",
                    "colors": "Modern gradients, tech-inspired colors, metallic accents",
                    "mood": "innovative, forward-thinking, sophisticated"
                },
                "vintage": {
                    "tone": "retro, nostalgic, classic",
                    "colors": "Muted tones, sepia, aged colors",
                    "mood": "nostalgic, timeless, authentic"
                }
            }
            
            config = style_configs.get(style.lower(), style_configs["professional"])
            
            branded_prompt = f"""
            Create a {style} creative studio image:
            
            Subject: {prompt}
            Style: {style} - {config['tone']}
            Color Palette: {config['colors']}
            Mood: {config['mood']}
            Design System: Bold, innovative, artistically driven with unlimited creative expression
            Photography Style: Bright, artistic, showing creative processes and artistic collaboration
            Layout: Creative hierarchy, artistic composition, experimental design
            Quality: Artistic-grade, suitable for creative projects and artistic expression
            
            Focus on visual elements that convey creative expertise and artistic studio services.
            Adapt the visual style to match the {style} aesthetic while maintaining artistic quality.
            Embrace creative freedom, artistic expression, and boundary-pushing visual concepts.
            """
            
            response = self.ai_clients['nano_banana'].models.generate_content(
                model="gemini-2.5-flash-image-preview",
                contents=[branded_prompt]
            )
            
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'inline_data') and part.inline_data is not None:
                    image_data = part.inline_data.data
                    
                    if Image:
                        image = Image.open(io.BytesIO(image_data))
                        
                        # For logo generation, ensure transparent background
                        if any(keyword in prompt.lower() for keyword in ['logo', 'icon', 'wordmark', 'combination']):
                            # Convert to RGBA if not already
                            if image.mode != 'RGBA':
                                image = image.convert('RGBA')
                            
                            # Create a new image with transparent background
                            transparent_image = Image.new('RGBA', image.size, (0, 0, 0, 0))
                            
                            # Paste the original image onto transparent background
                            transparent_image.paste(image, (0, 0), image)
                            image = transparent_image
                        
                        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
                        image.save(temp_file.name, 'PNG', optimize=True)
                        
                        return {
                            "success": True,
                            "image_path": temp_file.name,
                            "description": "Professional marketing agency image generated with transparent background",
                            "model": "gemini-2.5-flash-image-preview"
                        }
            
            return {"success": False, "error": "No image data received"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _extract_seo_keywords(self, content: str):
        """Extract and analyze SEO keywords from content"""
        try:
            # Enhanced keyword extraction for marketing agencies
            words = re.findall(r'\b[a-zA-Z]{3,}\b', content.lower())
            
            # Marketing agency-specific keywords
            industry_keywords = [
                'marketing strategy', 'content creation', 'social media marketing', 'digital marketing',
                'brand development', 'campaign management', 'SEO optimization', 'paid advertising',
                'email marketing', 'lead generation', 'conversion optimization', 'marketing automation',
                'analytics and reporting', 'customer acquisition', 'brand awareness', 'marketing ROI',
                'content marketing', 'influencer marketing', 'performance marketing', 'growth hacking'
            ]
            
            found_keywords = []
            for keyword in industry_keywords:
                if keyword.replace(' ', '') in ' '.join(words) or keyword in content.lower():
                    found_keywords.append(keyword)
            
            return found_keywords[:15]  # Return top 15
        except:
            return ['marketing strategy', 'content creation', 'digital marketing']
    
    async def _get_ai_response(self, prompt, system_context="", use_knowledge=True, max_length=None):
        """Get AI response with enhanced marketing agency context"""
        try:
            enhanced_prompt = f"""
            {self.studio_dna}
            
            Your Expert Role: {system_context}
            
            User Request: {prompt}
            
            Creative Studio Guidelines:
            1. Apply unlimited creative expression with no corporate constraints
            2. Use inspiring, artistic language that sparks imagination
            3. Lead with creative vision and artistic possibilities; explore boundaries
            4. Emphasize artistic expression and creative fulfillment
            5. Position as pure creative companion for authentic artistic expression
            6. Include creative inspiration, artistic techniques, and experimental approaches
            7. For content, aim for authentic, boundary-pushing creative pieces
            8. Use creative colors and artistic branding appropriately
            9. Maintain creative yet inspiring tone
            10. Always include artistic vision and creative possibilities
            
            Create expert-level creative content that positions our studio as the ultimate creative expression companion.
            """
            
            # Try Nano Banana first
            if 'nano_banana' in self.ai_clients:
                try:
                    response = self.ai_clients['nano_banana'].models.generate_content(
                        model="gemini-2.0-flash-exp",
                        contents=[enhanced_prompt]
                    )
                    result = response.candidates[0].content.parts[0].text
                    return result[:max_length] + "..." if max_length and len(result) > max_length else result
                except Exception as e:
                    logger.error(f"Nano Banana text error: {e}")
            
            # Try legacy Gemini
            if 'gemini' in self.ai_clients:
                try:
                    response = self.ai_clients['gemini'].generate_content(enhanced_prompt)
                    result = response.text
                    return result[:max_length] + "..." if max_length and len(result) > max_length else result
                except Exception as e:
                    logger.error(f"Gemini error: {e}")
            
            # Try OpenAI
            if 'openai' in self.ai_clients:
                try:
                    response = self.ai_clients['openai'].chat.completions.create(
                        model="gpt-4",
                        messages=[
                            {"role": "system", "content": self.brand_dna + "\n" + system_context},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=4000  # Increased for longer content
                    )
                    result = response.choices[0].message.content
                    return result[:max_length] + "..." if max_length and len(result) > max_length else result
                except Exception as e:
                    logger.error(f"OpenAI error: {e}")
            
            return "❌ No AI service available."
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    def _add_to_knowledge_base(self, title: str, content: str):
        """Add to knowledge base"""
        try:
            if not hasattr(self, 'knowledge_base'):
                self.knowledge_base = {"manual_entries": {}, "scraped_content": {}}
            self.knowledge_base["manual_entries"][title] = {"content": content, "type": "manual"}
            return True
        except:
            return False
        
    async def setup_hook(self):
        logger.info("Setting up Creative Studio AI...")
        
        # Debug: Check commands before sync
        local_commands = self.tree.get_commands()
        logger.info(f"Local commands before sync: {len(local_commands)}")
        for cmd in local_commands:
            logger.info(f"  - /{cmd.name}: {cmd.description}")
        
        # Sync commands directly (skip clearing to avoid issues)
        try:
            # Sync commands directly
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} marketing agents")
            
            # Log all synced commands
            for cmd in synced:
                logger.info(f"✅ Synced command: /{cmd.name}")
                
        except Exception as e:
            logger.error(f"Command sync error: {e}")
            # Try to sync anyway
            try:
                synced = await self.tree.sync()
                logger.info(f"Fallback sync completed: {len(synced)} commands")
            except Exception as e2:
                logger.error(f"Fallback sync failed: {e2}")
    
    async def on_ready(self):
        logger.info(f'{self.user} connected! Creative Studio AI active')
        logger.info(f"AI services: {list(self.ai_clients.keys())}")
        logger.info(f"Nano Banana: {NANO_BANANA_AVAILABLE}")
        logger.info(f"ClickUp integration: {'✅' if self.clickup_config['api_key'] else '❌'}")
        
        # Force command sync on ready (only if needed)
        try:
            # Check if commands are already available
            command_count = len(self.tree.get_commands())
            if command_count == 0:
                synced = await self.tree.sync()
                logger.info(f"✅ Commands synced on ready: {len(synced)} commands available")
            else:
                logger.info(f"✅ Commands already available on ready: {command_count} commands")
        except Exception as e:
            if "429" in str(e) or "rate limit" in str(e).lower():
                logger.warning(f"⚠️ Rate limited on ready - commands may still work: {e}")
            else:
                logger.error(f"Ready sync error: {e}")
        
        # Add ResumeHandler for reconnection handling
        try:
            await self.add_cog(ResumeHandler(self))
            logger.info("✅ ResumeHandler cog loaded for reconnection handling")
        except Exception as e:
            logger.error(f"Failed to load ResumeHandler: {e}")
        
        # Start command health monitoring task
        self.loop.create_task(self.command_health_monitor())
        
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="Marketing Agency operations"))
    
    async def on_message(self, message):
        """Handle messages for debugging"""
        if message.author.bot:
            return
        
        # Debug command visibility
        if message.content.startswith('!debug'):
            await message.channel.send(f"Bot is online! Commands should be available. Try `/help` or `/sync`")
        
        # Check if bot can see the message
        if message.content.startswith('!ping'):
            await message.channel.send("Pong! Bot is responding to messages.")

    async def command_health_monitor(self):
        """Monitor command health and re-sync if needed"""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                
                # Only run health check if bot is ready
                if not self.is_ready():
                    continue
                
                # Check if commands are still synced by testing tree access
                try:
                    # Try to access the command tree - if this fails, commands might be broken
                    command_count = len(self.tree.get_commands())
                    if command_count == 0:
                        logger.warning("⚠️ No commands found in tree - checking if we can sync")
                        
                        # Get the ResumeHandler to check sync limits
                        resume_handler = None
                        for cog in self.cogs.values():
                            if isinstance(cog, ResumeHandler):
                                resume_handler = cog
                                break
                        
                        # Only sync if we can do so safely
                        if resume_handler and resume_handler.can_sync_commands():
                            try:
                                synced = await self.tree.sync()
                                resume_handler.last_sync_time = time.time()
                                resume_handler.daily_sync_count += 1
                                logger.info(f"✅ Commands re-synced by health monitor: {len(synced)} commands")
                            except Exception as sync_error:
                                if "429" in str(sync_error) or "rate limit" in str(sync_error).lower():
                                    logger.warning(f"⚠️ Rate limited during health check - commands may still work: {sync_error}")
                                else:
                                    logger.error(f"❌ Health monitor sync failed: {sync_error}")
                        else:
                            logger.info("⏳ Skipping health monitor sync due to rate limits")
                    else:
                        logger.debug(f"✅ Command health check passed: {command_count} commands available")
                        
                except Exception as health_error:
                    logger.error(f"❌ Command health check failed: {health_error}")
                    # Don't attempt to re-sync on health check failure to avoid rate limits
                    logger.info("⏳ Skipping sync after health check failure to avoid rate limits")
                        
            except Exception as e:
                logger.error(f"❌ Command health monitor error: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying

    # ===== CLICKUP WEBHOOK AUTOMATION =====
    
    async def handle_clickup_webhook(self, webhook_data):
        """Handle ClickUp webhook and create Discord channel for new tasks"""
        try:
            event = webhook_data.get('event')
            
            # Only process task creation events
            if event != "taskCreated":
                logger.info(f"Ignoring ClickUp event: {event}")
                return
            
            task_data = webhook_data.get('task_id')
            if not task_data:
                logger.error("No task data in ClickUp webhook")
                return
            
            # Get task details from ClickUp API
            task_details = await self.get_clickup_task_details(task_data)
            if not task_details:
                logger.error(f"Could not get task details for task {task_data}")
                return
            
            # Create Discord channel for the task
            channel = await self.create_channel_from_clickup_task(task_details)
            if channel:
                logger.info(f"Created Discord channel {channel.name} for ClickUp task {task_details.get('name', 'Unknown')}")
            
        except Exception as e:
            logger.error(f"ClickUp webhook error: {e}")
    
    async def get_clickup_task_details(self, task_id):
        """Get task details from ClickUp API"""
        try:
            if not self.clickup_config["api_key"]:
                logger.error("ClickUp API key not configured")
                return None
            
            headers = {
                "Authorization": self.clickup_config["api_key"],
                "Content-Type": "application/json"
            }
            
            response = requests.get(
                f"{self.clickup_config['base_url']}/task/{task_id}",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"ClickUp API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting ClickUp task details: {e}")
            return None
    
    async def create_channel_from_clickup_task(self, task_details):
        """Create Discord channel from ClickUp task"""
        try:
            # Extract task information
            task_name = task_details.get('name', 'Unknown Task')
            task_id = task_details.get('id', '')
            task_description = task_details.get('description', '')
            task_url = task_details.get('url', '')
            
            # Create clean channel name
            channel_name = re.sub(r"[^a-zA-Z0-9s-]", "", task_name.lower())
            channel_name = re.sub(r"s+", "-", channel_name)
            channel_name = channel_name[:50]  # Discord channel name limit
            
            # Find projects category or create it
            guild = None
            for g in self.guilds:
                guild = g
                break
            
            if not guild:
                logger.error("No guild found for bot")
                return None
            
            # Find or create "Projects" category
            projects_category = None
            for category in guild.categories:
                if category.name.lower() == "projects":
                    projects_category = category
                    break
            
            if not projects_category:
                projects_category = await guild.create_category("Projects")
                logger.info("Created Projects category")
            
            # Create the channel
            channel = await guild.create_text_channel(
                name=channel_name,
                category=projects_category,
                topic=f"ClickUp Task: {task_name} | ID: {task_id}"
            )
            
            # Create welcome message with task details
            embed = discord.Embed(
                title=f"🚀 New Project: {task_name}",
                description=task_description[:1000] if task_description else "No description provided",
                color=self.studio_config["primary_color"],
                url=task_url if task_url else None
            )
            
            embed.add_field(
                name="📋 ClickUp Task",
                value=f"**ID:** {task_id}n**Link:** [View in ClickUp]({task_url})" if task_url else f"**ID:** {task_id}",
                inline=False
            )
            
            embed.add_field(
                name="🎯 Next Steps",
                value="• Review task requirementsn• Assign team membersn• Set project timelinen• Begin work!",
                inline=False
            )
            
            embed.set_footer(text="Automatically created from ClickUp task")
            embed.timestamp = datetime.now()
            
            await channel.send(embed=embed)
            
            # Store in active projects
            project_id = str(uuid.uuid4())
            self.active_projects[project_id] = {
                "name": task_name,
                "channel_id": channel.id,
                "clickup_task_id": task_id,
                "created_at": datetime.now(),
                "status": "active"
            }
            
            self.project_channels[channel.id] = project_id
            
            return channel
            
        except Exception as e:
            logger.error(f"Error creating Discord channel from ClickUp task: {e}")
            return None

    # ===== VOICE MEETING ASSISTANT =====
    
    async def start_voice_meeting(self, voice_channel):
        """Start voice meeting tracking"""
        try:
            logger.info(f"Attempting to join voice channel: {voice_channel.name}")
            
            # Join the voice channel
            voice_client = await voice_channel.connect()
            logger.info("Successfully connected to voice channel")
            
            # Store voice client reference
            self.voice_client = voice_client
            
            # Initialize meeting data
            self.meeting_start_time = datetime.now()
            self.is_recording = True
            logger.info("Meeting data initialized")
            
            # Create meeting tracker
            self.meeting_tracker = SimpleMeetingTracker(self)
            logger.info("Meeting tracker created")
            
            # Track initial participants in the voice channel
            try:
                if hasattr(voice_channel, 'members') and voice_channel.members:
                    for member in voice_channel.members:
                        if not member.bot:  # Don't track bots
                            self.meeting_tracker.track_user_join(member)
                            logger.info(f"Tracked initial participant: {member.name}")
                else:
                    logger.info("No initial participants in voice channel")
            except Exception as e:
                logger.error(f"Error tracking initial participants: {e}")
                # Continue anyway - this is not critical
            
            self.meeting_tracker.add_manual_note("Meeting started - Bot joined voice channel")
            
            logger.info(f"Started voice meeting in {voice_channel.name}")
            logger.info("🎤 Voice meeting tracking active!")
            return True
            
        except Exception as e:
            logger.error(f"Error starting voice meeting: {e}")
            logger.error(f"Exception type: {type(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    
    async def stop_voice_meeting(self):
        """Stop voice meeting and generate minutes"""
        try:
            self.is_recording = False
            
            # Add final note to meeting tracker
            if hasattr(self, 'meeting_tracker'):
                self.meeting_tracker.add_manual_note("Meeting ended - Bot left voice channel")
            
            # Disconnect from voice channel
            if hasattr(self, 'voice_client') and self.voice_client:
                await self.voice_client.disconnect()
                self.voice_client = None
            
            # Generate meeting minutes
            minutes = await self.generate_meeting_minutes()
            
            logger.info("Voice meeting stopped and minutes generated")
            return minutes
            
        except Exception as e:
            logger.error(f"Error stopping voice meeting: {e}")
            return None
    
    async def generate_meeting_minutes(self):
        """Generate professional meeting minutes from meeting tracker"""
        try:
            duration = datetime.now() - self.meeting_start_time if hasattr(self, 'meeting_start_time') else timedelta(minutes=0)
            
            # Get meeting summary from tracker
            meeting_summary = None
            if hasattr(self, 'meeting_tracker'):
                meeting_summary = self.meeting_tracker.get_meeting_summary()
            
            if not meeting_summary or not meeting_summary['activity_log']:
                # Generate basic meeting minutes
                return f"""
# 🎯 Meeting Minutes - {datetime.now().strftime('%Y-%m-%d %H:%M')}

**Duration:** {str(duration).split('.')[0]}
**Status:** Voice channel session completed

## 📝 Summary:
Meeting session in voice channel completed successfully. 

*Note: This was a voice channel session. For detailed transcription, enhanced audio processing will be added in future updates.*

## 🎯 Next Steps:
- Follow up on discussed items
- Schedule next meeting if needed
- Review action items

---
*Generated by Creative Studio AI Voice Assistant*
"""
            
            # Create activity log
            activity_text = ""
            participants = meeting_summary['participants']
            
            for entry in meeting_summary['activity_log']:
                if entry['action'] == 'joined':
                    activity_text += f"**[{entry['timestamp']}]** {entry['user']} joined the meeting\n"
                elif entry['action'] == 'left':
                    activity_text += f"**[{entry['timestamp']}]** {entry['user']} left the meeting\n"
                elif entry['action'] == 'note':
                    activity_text += f"**[{entry['timestamp']}]** {entry.get('text', 'Meeting note')}\n"
            
            # Use AI to generate professional meeting analysis
            analysis_prompt = f"""
            Create professional meeting minutes for a marketing agency voice meeting:
            
            Meeting Duration: {str(duration).split('.')[0]}
            Participants: {', '.join(participants)}
            Total Participants: {meeting_summary['total_participants']}
            
            Meeting Activity Log:
            {activity_text}
            
            Based on this voice meeting session, create comprehensive meeting minutes that focus on:
            1. Executive Summary - What was the main purpose and outcome of this meeting?
            2. Key Discussion Points - What topics were likely discussed during this {str(duration).split('.')[0]} session?
            3. Decisions Made - What decisions were probably reached during the meeting?
            4. Action Items - What follow-up tasks should be assigned based on this meeting?
            5. Next Steps - What are the recommended next actions for the team?
            
            Since this was a voice meeting, provide intelligent analysis of what was likely discussed based on:
            - Meeting duration ({str(duration).split('.')[0]})
            - Number of participants ({len(participants)})
            - Meeting context (marketing agency)
            
            Make it professional, actionable, and focused on business outcomes rather than just attendance tracking.
            """
            
            ai_minutes = await self._get_ai_response(
                analysis_prompt,
                "You are a professional meeting secretary creating minutes for a marketing agency voice meeting.",
                max_length=1500
            )
            
            # Combine AI analysis with activity log
            return f"""
# 🎯 Meeting Minutes - {datetime.now().strftime('%Y-%m-%d %H:%M')}

**Duration:** {str(duration).split('.')[0]}
**Participants:** {', '.join(participants)}
**Total Attendees:** {meeting_summary['total_participants']}

{ai_minutes}

---

## 📝 Meeting Activity Log:
{activity_text}

---
*Generated by Creative Studio AI Voice Assistant*
"""
            
        except Exception as e:
            logger.error(f"Error generating meeting minutes: {e}")
            return "Error generating meeting minutes. Please try again."

# ===== BOT INSTANCE CREATION =====
# Create bot instance first so commands can reference it
bot = CreativeStudioBot()

# ===== CLICKUP WEBHOOK SERVER =====

async def clickup_webhook_handler(request):
    """Handle incoming ClickUp webhooks"""
    try:
        # Verify the request
        if request.method != "POST":
            return web.Response(status=405, text="Method not allowed")
        
        # Get webhook data
        webhook_data = await request.json()
        logger.info(f"Received ClickUp webhook: {webhook_data.get('event', 'unknown')}")
        
        # Process the webhook
        await bot.handle_clickup_webhook(webhook_data)
        
        return web.Response(status=200, text="OK")
        
    except Exception as e:
        logger.error(f"Webhook handler error: {e}")
        return web.Response(status=500, text="Internal server error")

def start_webhook_server():
    """Start the webhook server in a separate thread"""
    try:
        app = web.Application()
        app.router.add_post("/webhook/clickup", clickup_webhook_handler)
        
        # Health check endpoint
        async def health_check(request):
            return web.Response(text="ClickUp Webhook Server is running!")
        
        app.router.add_get("/", health_check)
        app.router.add_get("/health", health_check)
        
        # Get port from environment or use default
        port = int(os.getenv("WEBHOOK_PORT", "8080"))
        
        logger.info(f"Starting ClickUp webhook server on port {port}")
        
        # Start server with better error handling
        web.run_app(
            app, 
            host="0.0.0.0", 
            port=port,
            access_log=None,  # Disable access logs to reduce noise
            print=lambda x: None  # Disable startup message
        )
        
    except Exception as e:
        logger.error(f"Webhook server error: {e}")
        import traceback
        logger.error(f"Webhook server traceback: {traceback.format_exc()}")

def run_webhook_server():
    """Run webhook server in background thread"""
    webhook_thread = threading.Thread(target=start_webhook_server, daemon=True)
    webhook_thread.start()
    logger.info("ClickUp webhook server started in background")

# ===== ENTERPRISE CONTENT CREATION =====

# Test command to verify registration
@bot.tree.command(name="ping", description="🏓 Test command to verify bot is working")
async def cmd_ping(interaction: discord.Interaction):
    """Simple ping command to test if commands are working"""
    await interaction.response.send_message("🏓 Pong! Bot is working and commands are registered!")

@bot.tree.command(name="ask", description="🤖 Ask the AI assistant anything - natural language queries")
async def cmd_ask(interaction: discord.Interaction, query: str):
    """Natural language AI assistant for marketing tasks"""
    try:
        await interaction.response.defer(thinking=True)
        
        # Analyze the query and determine the best response
        analysis_prompt = f"""
        Analyze this marketing query and provide a helpful response:
        Query: "{query}"
        
        You are a marketing agency AI assistant. Provide actionable advice, insights, or suggestions.
        If the user is asking for content creation, strategy, analytics, or project management help, provide detailed guidance.
        
        Be conversational, professional, and focus on marketing excellence.
        """
        
        response = await bot._get_ai_response(
            analysis_prompt,
            "You are a professional marketing consultant and AI assistant for a marketing agency.",
            max_length=1500
        )
        
        embed = discord.Embed(
            title="🤖 AI Marketing Assistant",
            description=response,
            color=bot.studio_config["accent_color"]
        )
        
        embed.add_field(
            name="💡 Need More Help?",
            value="Use specific commands like `/content`, `/strategy`, `/analytics`, or `/project` for detailed assistance",
            inline=False
        )
        
        embed.set_footer(text="AI-Powered Marketing Excellence • Creative Studio AI")
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Ask command error: {e}")
        await interaction.followup.send(f"❌ Error processing your query: {str(e)}")

@bot.tree.command(name="blog", description="📝 Create creative blog posts with artistic expression")
async def cmd_blog(interaction: discord.Interaction, topic: str, keywords: str = "", style: str = "creative", target_audience: str = "artists and creators", include_image: bool = True):
    """Create creative blog posts"""
    await interaction.response.defer(thinking=True)
    
    try:
        system_context = """
        You are a creative writer and artistic content creator for a creative studio.
        
        Your expertise includes:
        - Creative writing and storytelling
        - Artistic expression and creative vision
        - Authentic content creation without corporate constraints
        - Creative audience engagement and artistic connection
        - Multi-platform creative content adaptation
        
        Create blog content that is:
        - Creative and authentically artistic
        - Naturally engaging with artistic flair
        - Inspiring and creatively fulfilling for readers
        - Aligned with pure creative expression
        - Designed to spark imagination and artistic inspiration
        """
        
        enhanced_prompt = f"""
        Create comprehensive blog post for our creative studio about: {topic}
        Target Keywords: {keywords if keywords else 'creative expression, artistic content, creative writing, artistic inspiration'}
        Writing Style: {style}
        Target Audience: {target_audience}
        
        CONTENT REQUIREMENTS:
        
        1. LENGTH: 1500-3000 words (adjust based on style and audience)
        2. TARGET AUDIENCE: {target_audience}
        3. WRITING STYLE: {style} - adapt tone, complexity, and approach accordingly
        4. CREATIVE STUDIO BRAND INTEGRATION:
           - Creative yet inspiring tone
           - Artistic expression-focused messaging
           - Creative insights with unlimited imagination
           - Authentic creative expertise positioning
        
        5. CREATIVE CONTENT STRATEGY:
           - Primary keyword in title, first 100 words, and conclusion
           - Secondary keywords naturally integrated throughout
           - Long-tail creative keywords (artistic expression, creative inspiration, artistic vision)
           - Meta title and description optimized for creative search intent
           - Header structure optimized for creative discovery
           - Internal linking opportunities to creative studio service pages
        
        6. CREATIVE CONTENT STRUCTURE:
           - Creative Introduction (artistic vision and inspiration upfront)
           - Creative Context and Artistic Challenges
           - Creative Analysis (artistic expression and creative constraints)
           - Creative Studio Solution Framework (artistic offerings, creative engagement models)
           - Creative Differentiation (vs traditional agencies, corporate approaches)
           - Creative Implementation Methodology (artistic process, creative governance, artistic standards)
           - Creative Impact Analysis and Artistic Case
           - Creative Case Study or Success Story (with artistic metrics)
           - Creative Recommendations and Next Steps
           - Creative Call-to-Action (artistic collaboration, creative exploration, artistic fit assessment)
        
        7. CREATIVE PROOF POINTS TO INCLUDE:
           - Specific creative metrics and artistic impact data
           - Creative quality and artistic excellence standards
           - Creative timeline and artistic development processes
           - Creative standards and artistic integrity frameworks
           - Creative team composition and artistic collaboration structures
        
        Create inspiring, creative content that positions our creative studio as the ultimate artistic expression companion.
        """
        
        # Generate comprehensive content
        logger.info(f"Generating creative content: {topic}")
        content_result = await bot._get_ai_response(enhanced_prompt, system_context)
        
        # Extract creative SEO keywords
        seo_keywords = await bot._extract_seo_keywords(content_result)
        
        # Generate creative studio image
        image_result = None
        if include_image and NANO_BANANA_AVAILABLE:
            image_prompt = f"{style} creative studio header image for article about {topic}. Target audience: {target_audience}. Creative layout, artistic aesthetic, creative photography. {style} visual suitable for {target_audience}."
            image_result = await bot._generate_nano_banana_image(image_prompt, style)
        
        # Create creative studio embed
        embed = discord.Embed(
            title="📝 Creative Content Created!",
            description=f"**Type:** Blog Post\n**Topic:** {topic}\n**Style:** {style}\n**Audience:** {target_audience}\n**Length:** {len(content_result)} characters\n**Artistically Optimized:** ✅",
            color=bot.studio_config['primary_color']
        )
        
        # Add creative SEO analysis
        if seo_keywords:
            embed.add_field(
                name="🔍 Creative SEO Keywords",
                value=", ".join(seo_keywords[:10]),
                inline=False
            )
        
        # Create comprehensive creative content file
        seo_analysis = f"""
## Creative SEO Analysis
- **Content Length:** {len(content_result)} characters (Creative standard: 1500+ words)
- **Target Audience:** {target_audience}
- **Primary Keywords:** {keywords if keywords else 'Creative expression and artistic content'}
- **Extracted Keywords:** {', '.join(seo_keywords)}
- **Brand System:** Creative studio integrated
- **Competitive Positioning:** Unlimited creative expression and artistic freedom
- **Optimization Status:** ✅ Creative SEO Optimized

## Creative Studio Brand Integration
- **Voice:** Creative yet inspiring, artistic expression-focused
- **Positioning:** Unlimited creative expression companion
- **Approach:** Pure creativity with unlimited imagination
- **Governance:** Artistic integrity, creative freedom-driven delivery
- **Image Pairing:** {'✅ Creative studio image generated' if image_result and image_result.get('success') else '❌ Image generation not available'}

## Creative Messaging Framework
- Art-first, creativity-backed content
- AI-enhanced creativity vs traditional approaches
- Creative expression optimization and artistic fulfillment focus
- Creative expertise as artistic differentiator
- Modern creative visual identity integration
        """
        
        full_content = f"# Creative Studio Blog Post: {topic}\n\n{seo_analysis}\n\n## Creative Content\n\n{content_result}"
        
        # Create downloadable creative file
        file_buffer = io.BytesIO(full_content.encode('utf-8'))
        file = discord.File(file_buffer, filename=f"Creative_Studio_Blog_Post_{topic.replace(' ', '_')}.md")
        
        # Smart preview handling for creative content
        if len(content_result) > 1000:
            embed.add_field(name="📋 Creative Summary", value=content_result[:1000], inline=False)
            if len(content_result) > 2000:
                embed.add_field(name="📋 Content Preview", value=content_result[1000:2000], inline=False)
                embed.add_field(name="📄 Complete Creative Content", value="See attached file for full article with creative analysis", inline=False)
            else:
                embed.add_field(name="📋 Content Continuation", value=content_result[1000:], inline=False)
        else:
            embed.add_field(name="📋 Complete Content", value=content_result, inline=False)
        
        # Send with professional marketing image
        if image_result and image_result.get('success') and image_result.get('image_path'):
            image_file = discord.File(image_result['image_path'], filename=f"Marketing_Agency_{topic.replace(' ', '_')}.png")
            embed.set_thumbnail(url=f"attachment://Marketing_Agency_{topic.replace(' ', '_')}.png")
            embed.add_field(name="🎨 Marketing Image", value="Professional marketing header image generated and attached", inline=False)
            
            await interaction.followup.send(embed=embed, files=[file, image_file])
            
            try:
                os.unlink(image_result['image_path'])
            except:
                pass
        else:
            await interaction.followup.send(embed=embed, file=file)
            
    except Exception as e:
        logger.error(f"Enterprise content error: {e}")
        await interaction.followup.send(f"❌ Error: {str(e)}")

# ===== SEPARATE CONTENT COMMANDS =====

@bot.tree.command(name="styles", description="🎨 Show available styles for blog and image commands")
async def cmd_styles(interaction: discord.Interaction):
    """Show available styles for content generation"""
    await interaction.response.defer(ephemeral=True)
    
    embed = discord.Embed(
        title="🎨 Available Styles & Options",
        description="Customize your content generation with these style options:",
        color=bot.studio_config['accent_color']
    )
    
    # Blog styles
    embed.add_field(
        name="📝 Blog Writing Styles",
        value="""
**professional** - Corporate, authoritative, business-focused
**casual** - Friendly, conversational, approachable  
**creative** - Artistic, innovative, engaging
**technical** - Detailed, analytical, data-driven
**storytelling** - Narrative-driven, compelling, emotional
**educational** - Informative, tutorial-style, helpful
        """,
        inline=False
    )
    
    # Image styles
    embed.add_field(
        name="🎨 Image Visual Styles",
        value="""
**professional** - Clean, corporate, business-focused
**creative** - Artistic, innovative, visually striking
**casual** - Friendly, approachable, relaxed
**minimalist** - Simple, clean, uncluttered
**modern** - Contemporary, sleek, cutting-edge
**vintage** - Retro, nostalgic, classic
        """,
        inline=False
    )
    
    # Target audiences
    embed.add_field(
        name="👥 Target Audiences",
        value="""
**artists and creators** - Visual artists, writers, designers, musicians
**creative professionals** - Filmmakers, photographers, content creators
**creative entrepreneurs** - Creative business owners, artistic startups
**creative communities** - Art collectives, creative groups, artistic communities
**creative enthusiasts** - Art lovers, creative hobbyists, artistic explorers
**creative students** - Art students, creative learners, artistic education
**creative visionaries** - Innovative creators, boundary-pushing artists
        """,
        inline=False
    )
    
    embed.add_field(
        name="💡 Usage Examples",
        value="""
`/blog topic:"Creative Expression" style:creative audience:artists and creators`
`/image prompt:"artistic workspace" style:minimalist`
`/blog topic:"Artistic Inspiration" style:storytelling audience:creative communities`
        """,
        inline=False
    )
    
    embed.set_footer(text="Creative Studio AI • Custom Content Generation")
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="image", description="🎨 Generate images with Nano Banana AI - supports multiple styles")
async def cmd_image(interaction: discord.Interaction, prompt: str, style: str = "professional"):
    """Generate images using Nano Banana AI"""
    await interaction.response.defer(thinking=True)
    
    try:
        # Generate image
        image_result = await bot._generate_nano_banana_image(prompt, style)
        
        if image_result and image_result.get('success'):
            image_file = discord.File(image_result['image_path'], filename=f"generated_image_{int(datetime.now().timestamp())}.png")
            
            embed = discord.Embed(
                title="🎨 Image Generated",
                description=f"**Prompt:** {prompt}\n**Style:** {style}",
                color=bot.studio_config['accent_color']
            )
            
            embed.add_field(
                name="✨ Generated Image",
                value="AI-generated image attached below",
                inline=False
            )
            
            embed.set_footer(text="Creative Studio AI • Image Generation")
            
            await interaction.followup.send(embed=embed, files=[image_file])
            
            # Clean up temp file
            try:
                os.unlink(image_result['image_path'])
            except:
                pass
        else:
            error_msg = image_result.get('error', 'Unknown error') if image_result else 'No response from image generator'
            await interaction.followup.send(f"❌ Failed to generate image: {error_msg}")
            
    except Exception as e:
        logger.error(f"Image generation error: {e}")
        await interaction.followup.send(f"❌ Error: {str(e)}")

@bot.tree.command(name="logo", description="🎨 Generate logo icon - transparent PNG with no background")
async def cmd_logo_icon(interaction: discord.Interaction, company_name: str, industry: str = "general", style: str = "modern", description: str = ""):
    """Generate a logo icon using Nano Banana AI"""
    await interaction.response.defer(thinking=True)
    
    try:
        # Create detailed prompt for logo icon generation
        logo_prompt = f"""
        Create a professional logo ICON for "{company_name}" in the {industry} industry.
        
        Requirements:
        - ICON ONLY (no text, no wordmark)
        - Transparent background (PNG format)
        - {style} design style
        - Professional and memorable
        - Scalable for various sizes
        - Industry-appropriate symbolism
        
        Company: {company_name}
        Industry: {industry}
        Style: {style}
        Description: {description if description else "Professional business logo"}
        
        Generate a clean, minimalist icon that represents the brand identity.
        """
        
        # Generate the logo using Nano Banana
        logo_result = await bot._generate_nano_banana_image(logo_prompt, style)
        
        if logo_result and logo_result.get('success'):
            logo_file = discord.File(logo_result['image_path'], filename=f"{company_name.replace(' ', '_')}_logo_icon.png")
            
            embed = discord.Embed(
                title="🎨 Logo Icon Generated!",
                description=f"**Company:** {company_name}\n**Industry:** {industry}\n**Style:** {style}",
                color=0x8b5cf6
            )
            embed.set_image(url=f"attachment://{logo_file.filename}")
            embed.add_field(name="📁 File", value=f"`{logo_file.filename}`", inline=True)
            embed.add_field(name="🎯 Type", value="Logo Icon", inline=True)
            embed.add_field(name="🖼️ Format", value="Transparent PNG", inline=True)
            
            await interaction.followup.send(embed=embed, file=logo_file)
        else:
            await interaction.followup.send("❌ Failed to generate logo icon. Please try again.")
            
    except Exception as e:
        logger.error(f"Logo icon generation error: {e}")
        await interaction.followup.send(f"❌ Error: {str(e)}")

@bot.tree.command(name="wordmark", description="📝 Generate logo wordmark - text-based logo with transparent background")
async def cmd_logo_wordmark(interaction: discord.Interaction, company_name: str, industry: str = "general", style: str = "modern", font_style: str = "clean"):
    """Generate a logo wordmark using Nano Banana AI"""
    await interaction.response.defer(thinking=True)
    
    try:
        # Create detailed prompt for wordmark generation
        wordmark_prompt = f"""
        Create a professional logo WORDMARK for "{company_name}" in the {industry} industry.
        
        Requirements:
        - TEXT/LOGO TYPE ONLY (company name as the main element)
        - Transparent background (PNG format)
        - {style} design style with {font_style} typography
        - Professional and readable
        - Scalable for various sizes
        - Industry-appropriate styling
        
        Company: {company_name}
        Industry: {industry}
        Style: {style}
        Typography: {font_style}
        
        Generate a clean, professional wordmark that emphasizes the company name with appropriate styling.
        """
        
        # Generate the wordmark using Nano Banana
        wordmark_result = await bot._generate_nano_banana_image(wordmark_prompt, style)
        
        if wordmark_result and wordmark_result.get('success'):
            wordmark_file = discord.File(wordmark_result['image_path'], filename=f"{company_name.replace(' ', '_')}_wordmark.png")
            
            embed = discord.Embed(
                title="📝 Logo Wordmark Generated!",
                description=f"**Company:** {company_name}\n**Industry:** {industry}\n**Style:** {style}",
                color=0x8b5cf6
            )
            embed.set_image(url=f"attachment://{wordmark_file.filename}")
            embed.add_field(name="📁 File", value=f"`{wordmark_file.filename}`", inline=True)
            embed.add_field(name="🎯 Type", value="Logo Wordmark", inline=True)
            embed.add_field(name="🖼️ Format", value="Transparent PNG", inline=True)
            
            await interaction.followup.send(embed=embed, file=wordmark_file)
        else:
            await interaction.followup.send("❌ Failed to generate logo wordmark. Please try again.")
            
    except Exception as e:
        logger.error(f"Logo wordmark generation error: {e}")
        await interaction.followup.send(f"❌ Error: {str(e)}")

@bot.tree.command(name="combination", description="🔗 Generate logo combination - icon + wordmark together")
async def cmd_logo_combination(interaction: discord.Interaction, company_name: str, industry: str = "general", style: str = "modern", layout: str = "horizontal"):
    """Generate a logo combination using Nano Banana AI"""
    await interaction.response.defer(thinking=True)
    
    try:
        # Create detailed prompt for combination logo generation
        combination_prompt = f"""
        Create a professional COMBINATION LOGO for "{company_name}" in the {industry} industry.
        
        Requirements:
        - ICON + WORDMARK COMBINED (both icon and company name together)
        - Transparent background (PNG format)
        - {style} design style
        - {layout} layout (icon and text arrangement)
        - Professional and balanced composition
        - Scalable for various sizes
        - Industry-appropriate design
        
        Company: {company_name}
        Industry: {industry}
        Style: {style}
        Layout: {layout}
        
        Generate a complete logo that combines both an icon and the company name in a professional, balanced design.
        """
        
        # Generate the combination logo using Nano Banana
        combination_result = await bot._generate_nano_banana_image(combination_prompt, style)
        
        if combination_result and combination_result.get('success'):
            combination_file = discord.File(combination_result['image_path'], filename=f"{company_name.replace(' ', '_')}_combination_logo.png")
            
            embed = discord.Embed(
                title="🔗 Logo Combination Generated!",
                description=f"**Company:** {company_name}\n**Industry:** {industry}\n**Style:** {style}",
                color=0x8b5cf6
            )
            embed.set_image(url=f"attachment://{combination_file.filename}")
            embed.add_field(name="📁 File", value=f"`{combination_file.filename}`", inline=True)
            embed.add_field(name="🎯 Type", value="Logo Combination", inline=True)
            embed.add_field(name="🖼️ Format", value="Transparent PNG", inline=True)
            
            await interaction.followup.send(embed=embed, file=combination_file)
        else:
            await interaction.followup.send("❌ Failed to generate logo combination. Please try again.")
            
    except Exception as e:
        logger.error(f"Logo combination generation error: {e}")
        await interaction.followup.send(f"❌ Error: {str(e)}")

@bot.tree.command(name="logo_family", description="👨‍👩‍👧‍👦 Generate complete logo family - icon, wordmark, and combination")
async def cmd_logo_family(interaction: discord.Interaction, company_name: str, industry: str = "general", style: str = "modern"):
    """Generate a complete logo family using Nano Banana AI"""
    await interaction.response.defer(thinking=True)
    
    try:
        # Generate all three logo types
        icon_prompt = f"Create a professional logo ICON for '{company_name}' in the {industry} industry. ICON ONLY, transparent background, {style} style."
        wordmark_prompt = f"Create a professional logo WORDMARK for '{company_name}' in the {industry} industry. TEXT ONLY, transparent background, {style} style."
        combination_prompt = f"Create a professional COMBINATION LOGO for '{company_name}' in the {industry} industry. ICON + WORDMARK together, transparent background, {style} style."
        
        # Generate all three logos
        icon_result = await bot._generate_nano_banana_image(icon_prompt, style)
        wordmark_result = await bot._generate_nano_banana_image(wordmark_prompt, style)
        combination_result = await bot._generate_nano_banana_image(combination_prompt, style)
        
        files = []
        embed = discord.Embed(
            title="👨‍👩‍👧‍👦 Complete Logo Family Generated!",
            description=f"**Company:** {company_name}\n**Industry:** {industry}\n**Style:** {style}",
            color=0x8b5cf6
        )
        
        # Add each logo file if successful
        if icon_result and icon_result.get('success'):
            icon_file = discord.File(icon_result['image_path'], filename=f"{company_name.replace(' ', '_')}_icon.png")
            files.append(icon_file)
            embed.add_field(name="🎨 Logo Icon", value="✅ Generated", inline=True)
        else:
            embed.add_field(name="🎨 Logo Icon", value="❌ Failed", inline=True)
            
        if wordmark_result and wordmark_result.get('success'):
            wordmark_file = discord.File(wordmark_result['image_path'], filename=f"{company_name.replace(' ', '_')}_wordmark.png")
            files.append(wordmark_file)
            embed.add_field(name="📝 Logo Wordmark", value="✅ Generated", inline=True)
        else:
            embed.add_field(name="📝 Logo Wordmark", value="❌ Failed", inline=True)
            
        if combination_result and combination_result.get('success'):
            combination_file = discord.File(combination_result['image_path'], filename=f"{company_name.replace(' ', '_')}_combination.png")
            files.append(combination_file)
            embed.add_field(name="🔗 Logo Combination", value="✅ Generated", inline=True)
        else:
            embed.add_field(name="🔗 Logo Combination", value="❌ Failed", inline=True)
        
        embed.add_field(name="🖼️ Format", value="Transparent PNG", inline=False)
        embed.add_field(name="📁 Files", value=f"{len(files)} logo files attached", inline=False)
        
        if files:
            await interaction.followup.send(embed=embed, files=files)
        else:
            await interaction.followup.send("❌ Failed to generate any logos. Please try again.")
            
    except Exception as e:
        logger.error(f"Logo family generation error: {e}")
        await interaction.followup.send(f"❌ Error: {str(e)}")

@bot.tree.command(name="carousel", description="📱 Create social media carousel content")
async def cmd_carousel(interaction: discord.Interaction, topic: str, slides: int = 5):
    """Create social media carousel content"""
    await interaction.response.defer(thinking=True)
    
    try:
        system_context = """
        You are a social media content strategist specializing in carousel posts.
        Create engaging, educational carousel content that drives engagement and conversions.
        """
        
        prompt = f"""
        Create a {slides}-slide social media carousel about: {topic}
        
        Requirements:
        - Each slide should have a clear headline and key point
        - Educational and valuable content
        - Engaging and shareable
        - Include a strong call-to-action on the final slide
        - Optimized for Instagram, LinkedIn, and Facebook
        
        Format each slide as:
        Slide 1: [Headline] - [Key Point]
        Slide 2: [Headline] - [Key Point]
        etc.
        """
        
        carousel_content = await bot._get_ai_response(prompt, system_context, max_length=1500)
        
        embed = discord.Embed(
            title="📱 Carousel Content Created",
            description=f"**Topic:** {topic}\n**Slides:** {slides}",
            color=bot.studio_config['accent_color']
        )
        
        embed.add_field(
            name="📄 Carousel Content",
            value=carousel_content[:1024] + "..." if len(carousel_content) > 1024 else carousel_content,
            inline=False
        )
        
        embed.set_footer(text="Creative Studio AI • Carousel Creation")
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Carousel creation error: {e}")
        await interaction.followup.send(f"❌ Error: {str(e)}")

@bot.tree.command(name="spinoff", description="🚀 Create multiple social media posts from blog content")
async def cmd_spinoff(interaction: discord.Interaction, blog_content: str, platforms: str = "all"):
    """Create multiple social media posts from blog content"""
    await interaction.response.defer(thinking=True)
    
    try:
        system_context = """
        You are a social media content strategist who creates platform-specific posts from blog content.
        Extract key points and create engaging posts for different social media platforms.
        """
        
        prompt = f"""
        Create multiple social media posts from this blog content:
        
        {blog_content}
        
        Create posts for: {platforms}
        
        For each platform, create:
        1. Instagram post (with caption and hashtags)
        2. LinkedIn post (professional tone)
        3. Twitter/X post (concise and engaging)
        4. Facebook post (conversational tone)
        5. TikTok script (trendy and engaging)
        
        Each post should:
        - Extract key insights from the blog
        - Be platform-optimized
        - Include relevant hashtags
        - Have a clear call-to-action
        - Be ready to post immediately
        
        Format each post clearly with platform labels.
        """
        
        spinoff_content = await bot._get_ai_response(prompt, system_context, max_length=3000)
        
        embed = discord.Embed(
            title="🚀 Social Media Posts Created",
            description=f"**Platforms:** {platforms}\n**Based on:** Blog content analysis",
            color=bot.studio_config['accent_color']
        )
        
        # Split long content into multiple fields
        if len(spinoff_content) > 1024:
            chunks = [spinoff_content[i:i+1020] for i in range(0, len(spinoff_content), 1020)]
            for i, chunk in enumerate(chunks[:3]):  # Limit to 3 chunks
                embed.add_field(
                    name=f"📱 Social Media Posts {f'(Part {i+1})' if len(chunks) > 1 else ''}",
                    value=chunk,
                    inline=False
                )
        else:
            embed.add_field(
                name="📱 Social Media Posts",
                value=spinoff_content,
                inline=False
            )
        
        embed.set_footer(text="Creative Studio AI • Content Spinoff")
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Spinoff creation error: {e}")
        await interaction.followup.send(f"❌ Error: {str(e)}")

# Add other essential commands...

@bot.tree.command(name="test", description="🧪 Test enterprise system functionality")
async def cmd_test(interaction: discord.Interaction):
    try:
        embed = discord.Embed(
            title="✅ Creative Studio AI",
            description="Professional marketing agency system active • AI agents ready",
            color=bot.brand_config['primary_color']
        )
        embed.add_field(name="🤖 AI Services", value=f"Available: {list(bot.ai_clients.keys())}", inline=False)
        embed.add_field(name="🍌 Nano Banana", value=f"{'✅ Available' if NANO_BANANA_AVAILABLE else '❌ Legacy mode'}", inline=False)
        embed.add_field(name="🎨 Brand System", value="Professional Marketing Agency • AI-Powered • Results-Driven", inline=False)
        embed.add_field(name="🏢 Positioning", value="Premium AI-powered marketing agency", inline=False)
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ Test failed: {str(e)}")

# ===== FILE UPLOAD & PROJECT MANAGEMENT =====

@bot.tree.command(name="upload", description="📁 Upload and analyze files to create projects and campaigns")
async def cmd_upload(interaction: discord.Interaction, file: discord.Attachment):
    """Upload and analyze files to create projects"""
    await interaction.response.defer(thinking=True)
    
    try:
        # Check file type
        if not file.filename.endswith(('.md', '.txt', '.docx', '.pdf')):
            await interaction.followup.send("❌ Please upload .md, .txt, .docx, or .pdf files only.")
            return
        
        # Download and read file
        file_content = await file.read()
        
        if file.filename.endswith('.md') or file.filename.endswith('.txt'):
            content = file_content.decode('utf-8')
        else:
            # For other formats, we'd need additional libraries
            await interaction.followup.send("⚠️ Currently only .md and .txt files are fully supported. Other formats coming soon!")
            return
        
        # Analyze file
        analysis = await bot.analyze_uploaded_file(content, file.filename)
        
        # Create project channel
        project_name = file.filename.replace('.md', '').replace('.txt', '').replace('_', ' ').title()
        channel, project_id = await bot.create_project_channel(
            interaction.guild, 
            project_name, 
            {'summary': analysis[:500] + '...' if len(analysis) > 500 else analysis}
        )
        
        if channel:
            embed = discord.Embed(
                title="📁 File Uploaded & Analyzed!",
                description=f"**File:** {file.filename}\n**Project:** {project_name}\n**Channel:** {channel.mention}",
                color=bot.studio_config['primary_color']
            )
            
            embed.add_field(
                name="🔍 AI Analysis",
                value=analysis[:1000] + "..." if len(analysis) > 1000 else analysis,
                inline=False
            )
            
            embed.add_field(
                name="📋 Next Steps",
                value="1. Review analysis in project channel\n2. Create ClickUp tasks\n3. Set up project timeline\n4. Assign team members",
                inline=False
            )
            
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("❌ Error creating project channel. Please check bot permissions.")
            
    except Exception as e:
        logger.error(f"Upload error: {e}")
        await interaction.followup.send(f"❌ Error processing file: {str(e)}")

@bot.tree.command(name="project", description="🚀 Create a new project with ClickUp integration")
async def cmd_create_project(interaction: discord.Interaction, project_name: str, description: str = ""):
    """Create a new project"""
    await interaction.response.defer(thinking=True)
    
    try:
        # Create project channel
        channel, project_id = await bot.create_project_channel(
            interaction.guild,
            project_name,
            {'summary': description, 'timeline': 'To be determined', 'stakeholders': 'To be identified'}
        )
        
        if channel:
            embed = discord.Embed(
                title="🚀 New Project Created!",
                description=f"**Project:** {project_name}\n**Channel:** {channel.mention}",
                color=bot.studio_config['accent_color']
            )
            
            embed.add_field(
                name="📝 Description",
                value=description if description else "No description provided",
                inline=False
            )
            
            embed.add_field(
                name="📋 Next Steps",
                value="1. Set up ClickUp tasks\n2. Define timeline\n3. Assign team members\n4. Create project milestones",
                inline=False
            )
            
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("❌ Error creating project channel. Please check bot permissions.")
            
    except Exception as e:
        logger.error(f"Project creation error: {e}")
        await interaction.followup.send(f"❌ Error creating project: {str(e)}")

@bot.tree.command(name="clickup", description="📋 ClickUp task management")
async def cmd_clickup(interaction: discord.Interaction, action: str, task_name: str = "", description: str = ""):
    """ClickUp task management"""
    await interaction.response.defer(thinking=True)
    
    try:
        if action == "list":
            tasks = await bot.get_clickup_tasks()
            if tasks and 'tasks' in tasks:
                embed = discord.Embed(
                    title="📋 ClickUp Tasks",
                    description=f"Found {len(tasks['tasks'])} tasks",
                    color=bot.studio_config['primary_color']
                )
                
                for i, task in enumerate(tasks['tasks'][:10]):  # Show first 10
                    status = task.get('status', {}).get('status', 'Unknown')
                    assignee = task.get('assignees', [{}])[0].get('username', 'Unassigned') if task.get('assignees') else 'Unassigned'
                    
                    embed.add_field(
                        name=f"{i+1}. {task.get('name', 'Untitled')}",
                        value=f"Status: {status} | Assignee: {assignee}",
                        inline=False
                    )
                
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send("❌ No tasks found or ClickUp not configured.")
        
        elif action == "create":
            if not task_name:
                await interaction.followup.send("❌ Please provide a task name.")
                return
            
            # You'd need to specify a list_id here
            # For now, we'll show how it would work
            embed = discord.Embed(
                title="📝 Task Creation",
                description="Task creation requires a ClickUp list ID. Use the ClickUp web interface to get the list ID, then we can create tasks programmatically.",
                color=bot.studio_config['warning_color']
            )
            
            embed.add_field(
                name="Task Details",
                value=f"**Name:** {task_name}\n**Description:** {description if description else 'No description'}",
                inline=False
            )
            
            await interaction.followup.send(embed=embed)
        
        else:
            await interaction.followup.send("❌ Use 'list' or 'create' as the action.")
            
    except Exception as e:
        logger.error(f"ClickUp error: {e}")
        await interaction.followup.send(f"❌ ClickUp error: {str(e)}")

# ===== UAT TESTING AGENT =====

@bot.tree.command(name="uat", description="🧪 UAT Testing Agent - Test websites against 13 SOPs")
async def cmd_uat_testing(interaction: discord.Interaction, website_url: str, custom_notes: str = ""):
    """UAT Testing Agent for website testing"""
    await interaction.response.defer(thinking=True)
    
    try:
        # Analyze the website
        embed = discord.Embed(
            title="🧪 UAT Testing Agent",
            description=f"Analyzing website: {website_url}",
            color=bot.studio_config['primary_color']
        )
        
        embed.add_field(
            name="🔍 Initial Analysis",
            value="Scanning website for basic functionality and structure...",
            inline=False
        )
        
        await interaction.followup.send(embed=embed)
        
        # Perform website analysis
        website_data = await bot.analyze_website(website_url)
        
        if "error" in website_data:
            # Check if it's a blocking error (406, 403) and offer manual UAT option
            if "406" in website_data['error'] or "403" in website_data['error']:
                error_embed = discord.Embed(
                    title="⚠️ Website Blocked Automated Analysis",
                    description=f"**Issue:** {website_data['error']}\n\n**Solution:** This website has anti-bot protection. You can still get a UAT report based on manual testing.",
                    color=bot.studio_config['warning_color']
                )
                
                error_embed.add_field(
                    name="🔧 Manual UAT Options",
                    value="1. **Manual Testing:** Test the website manually and provide notes\n2. **Alternative URL:** Try a different page or subdomain\n3. **Contact Admin:** Ask website owner to whitelist automated testing",
                    inline=False
                )
                
                error_embed.add_field(
                    name="📋 Still Want UAT Report?",
                    value="I can generate a UAT checklist and report template based on your custom notes, even without automated analysis.",
                    inline=False
                )
                
                await interaction.followup.send(embed=error_embed)
                return
            else:
                error_embed = discord.Embed(
                    title="❌ UAT Testing Failed",
                    description=f"Could not analyze website: {website_data['error']}",
                    color=bot.studio_config['error_color']
                )
                await interaction.followup.send(embed=error_embed)
                return
        
        # Generate comprehensive UAT report
        uat_report = await bot.generate_uat_report(website_data, custom_notes)
        
        # Create detailed UAT report embed
        report_embed = discord.Embed(
            title="📋 UAT Testing Report",
            description=f"**Website:** {website_data['url']}\n**Title:** {website_data['title']}",
            color=bot.studio_config['accent_color']
        )
        
        # Add website analysis summary
        report_embed.add_field(
            name="📊 Website Analysis Summary",
            value=f"""
**Status Code:** {website_data['status_code']}
**Load Time:** {website_data['load_time']:.2f}s
**HTTPS:** {'✅ Secure' if website_data['is_https'] else '❌ Not Secure'}
**Forms:** {'✅ Present' if website_data['has_forms'] else '❌ None Found'}
**Images:** {'✅ Present' if website_data['has_images'] else '❌ None Found'}
**Scripts:** {'✅ Present' if website_data['has_scripts'] else '❌ None Found'}
**CSS:** {'✅ Present' if website_data['has_css'] else '❌ None Found'}
            """,
            inline=False
        )
        
        # Add UAT report - use description for long content to avoid field limits
        if len(uat_report) > 1024:
            # Use description for long UAT reports (up to 4096 chars)
            report_embed.description = f"**Website:** {website_data['url']}\n**Title:** {website_data['title']}\n\n{uat_report[:3500]}{'...' if len(uat_report) > 3500 else ''}"
        else:
            report_embed.add_field(
                name="📋 UAT Report",
                value=uat_report,
                inline=False
            )
        
        # Add SOP checklist
        sop_summary = "**8 SOP Categories Tested:**\n"
        for sop_name in bot.uat_sops.keys():
            sop_summary += f"• {sop_name}\n"
        
        embed.add_field(
            name="✅ 8 SOP Categories Tested",
            value=sop_summary,
            inline=False
        )
        
        # Create downloadable report file
        full_report = f"""# UAT Testing Report

## Website Information
- **URL:** {website_data['url']}
- **Title:** {website_data['title']}
- **Analysis Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Status Code:** {website_data['status_code']}
- **Load Time:** {website_data['load_time']:.2f} seconds

## Technical Analysis
- **HTTPS:** {'✅ Secure' if website_data['is_https'] else '❌ Not Secure'}
- **Forms:** {'✅ Present' if website_data['has_forms'] else '❌ None Found'}
- **Images:** {'✅ Present' if website_data['has_images'] else '❌ None Found'}
- **Scripts:** {'✅ Present' if website_data['has_scripts'] else '❌ None Found'}
- **CSS:** {'✅ Present' if website_data['has_css'] else '❌ None Found'}
- **Content Length:** {website_data['content_length']} characters

## Custom Notes
{custom_notes if custom_notes else 'No custom notes provided'}

## UAT Testing Report (8-Step Workflow)
{uat_report}

## 8 Marketing Agency SOP Categories Tested
"""
        
        for sop_name, sop_items in bot.uat_sops.items():
            full_report += f"\n### {sop_name}\n"
            for item in sop_items:
                full_report += f"- {item}\n"
        
        # Add file storage information
        full_report += f"""

## File Storage & Data Management

### Where Files Are Saved:
- **Discord Channel:** This report is posted in the current Discord channel
- **Downloadable File:** This markdown file can be downloaded directly from Discord
- **Local Storage:** Reports are temporarily stored in memory during bot operation
- **No Permanent Storage:** The bot does not permanently store UAT reports on the server

### Data Retention:
- **Temporary:** UAT analysis data is held in memory only during the testing session
- **Downloadable:** Users can download the complete report as a markdown file
- **No Database:** No UAT data is stored in databases or external systems
- **Privacy:** All analysis is performed in real-time without data persistence

### Recommended Storage:
- **Client Folders:** Save downloaded reports in organized client project folders
- **Documentation:** Use reports for client deliverables and project documentation
- **Version Control:** Track UAT reports as part of project version control
- **Backup:** Maintain copies of important UAT reports in your preferred storage system

---
*Report generated by Creative Studio AI UAT Testing Agent*
*Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        
        # Create downloadable file
        file_buffer = io.BytesIO(full_report.encode('utf-8'))
        file = discord.File(file_buffer, filename=f"UAT_Report_{website_data['url'].replace('https://', '').replace('http://', '').replace('/', '_')}.md")
        
        await interaction.followup.send(embed=report_embed, file=file)
        
    except Exception as e:
        logger.error(f"UAT testing error: {e}")
        await interaction.followup.send(f"❌ UAT testing error: {str(e)}")

@bot.tree.command(name="sops", description="📋 Show the 8 UAT Testing SOPs")
async def cmd_show_sops(interaction: discord.Interaction):
    """Show the 8 UAT Testing SOPs"""
    try:
        embed = discord.Embed(
            title="📋 UAT Testing SOPs",
            description="8 Marketing Agency Standard Operating Procedures for website testing",
            color=bot.studio_config['primary_color']
        )
        
        for sop_name, sop_items in bot.uat_sops.items():
            sop_text = "\n".join([f"• {item}" for item in sop_items])
            embed.add_field(
                name=sop_name,
                value=sop_text,
                inline=False
            )
        
        embed.set_footer(text="Use /uat command to test a website against these SOPs")
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        if not interaction.response.is_done():
            await interaction.response.send_message(f"❌ Error: {str(e)}")
        else:
            await interaction.followup.send(f"❌ Error: {str(e)}")

@bot.tree.command(name="sync", description="🔄 Force sync Discord commands")
async def cmd_sync(interaction: discord.Interaction):
    """Force sync Discord commands"""
    await interaction.response.defer(thinking=True)
    
    try:
        # Clear all commands first to force refresh
        bot.tree.clear_commands(guild=None)
        
        # Sync commands directly
        synced = await bot.tree.sync()
        
        embed = discord.Embed(
            title="🔄 Commands Synced Successfully",
            description=f"Synced {len(synced)} commands to Discord",
            color=bot.studio_config['accent_color']
        )
        
        # List all synced commands
        command_list = "\n".join([f"• `/{cmd.name}`" for cmd in synced])
        embed.add_field(
            name="📋 Available Commands",
            value=command_list,
            inline=False
        )
        
        embed.add_field(
            name="⏱️ Note",
            value="Commands may take up to 1 hour to appear globally. Try using them in the current server first.",
            inline=False
        )
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        await interaction.followup.send(f"❌ Sync error: {str(e)}")

@bot.tree.command(name="status", description="📊 Show bot status and health information")
async def cmd_status(interaction: discord.Interaction):
    """Show bot status and health information"""
    try:
        uptime = bot.get_uptime()
        uptime_str = f"{uptime.days}d {uptime.seconds//3600}h {(uptime.seconds//60)%60}m"
        
        embed = discord.Embed(
            title="📊 Bot Status & Health",
            description="Creative Studio AI system information",
            color=bot.studio_config['accent_color']
        )
        
        embed.add_field(
            name="⏱️ Uptime",
            value=uptime_str,
            inline=True
        )
        
        embed.add_field(
            name="🔧 Error Count",
            value=f"{bot.error_count}/{bot.max_errors}",
            inline=True
        )
        
        embed.add_field(
            name="📁 Active Projects",
            value=str(len(bot.active_projects)),
            inline=True
        )
        
        embed.add_field(
            name="🤖 AI Services",
            value=f"Available: {len(bot.ai_clients)}",
            inline=True
        )
        
        embed.add_field(
            name="🔗 ClickUp Integration",
            value="✅ Connected" if bot.clickup_config['api_key'] else "❌ Disconnected",
            inline=True
        )
        
        embed.add_field(
            name="🎨 Nano Banana",
            value="✅ Active" if 'nano_banana' in bot.ai_clients else "❌ Inactive",
            inline=True
        )
        
        # Memory usage info
        import psutil
        memory = psutil.virtual_memory()
        embed.add_field(
            name="💾 Memory Usage",
            value=f"{memory.percent}% ({memory.used // 1024 // 1024}MB / {memory.total // 1024 // 1024}MB)",
            inline=False
        )
        
        embed.set_footer(text="Bot Health Monitor • Last updated")
        embed.timestamp = datetime.now()
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        if not interaction.response.is_done():
            await interaction.response.send_message(f"❌ Status error: {str(e)}")
        else:
            await interaction.followup.send(f"❌ Status error: {str(e)}")

@bot.tree.command(name="webhook", description="🔗 Show ClickUp webhook integration status")
async def cmd_webhook_status(interaction: discord.Interaction):
    """Show ClickUp webhook integration status"""
    try:
        webhook_port = os.getenv("WEBHOOK_PORT", "8080")
        railway_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN", "your-app.railway.app")
        webhook_url = f"https://{railway_domain}/webhook/clickup"
        
        embed = discord.Embed(
            title="🔗 ClickUp Webhook Integration",
            description="Automatic Discord channel creation from ClickUp tasks",
            color=bot.studio_config["accent_color"]
        )
        
        embed.add_field(
            name="📡 Webhook URL",
            value=f"`{webhook_url}`",
            inline=False
        )
        
        embed.add_field(
            name="⚙️ Configuration",
            value=f"**Port:** {webhook_port}\n**Status:** 🟢 Active\n**Events:** Task Creation",
            inline=True
        )
        
        embed.add_field(
            name="🎯 How it Works",
            value="1. Create task in ClickUp\n2. ClickUp sends webhook\n3. Bot creates Discord channel\n4. Channel added to Projects category",
            inline=True
        )
        
        embed.add_field(
            name="📋 Setup Instructions",
            value=f"1. Go to ClickUp Space Settings\n2. Add webhook: `{webhook_url}`\n3. Select \"Task Created\" event\n4. Save webhook configuration",
            inline=False
        )
        
        embed.add_field(
            name="📊 Active Projects",
            value=f"Currently tracking {len(bot.active_projects)} projects",
            inline=True
        )
        
        embed.set_footer(text="ClickUp Webhook Automation • Creative Studio AI")
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Webhook status error: {str(e)}")

@bot.tree.command(name="help", description="❓ Show marketing agency AI hub commands")
async def cmd_help(interaction: discord.Interaction):
    try:
        embed = discord.Embed(
            title="🤖 Creative Studio AI",
            description="Complete project management & content creation suite • AI-powered marketing excellence",
            color=bot.studio_config['primary_color']
        )
        
        embed.add_field(
            name="🎨 Content Creation",
            value="• `/blog` - Create professional blog posts with SEO\n• `/image` - Generate images with Nano Banana AI\n• `/carousel` - Create social media carousel content\n• `/spinoff` - Create multiple posts from blog content",
            inline=False
        )
        
        embed.add_field(
            name="📁 Project Management",
            value="• `/upload` - Upload files to create projects\n• `/project` - Create new project channels\n• `/clickup` - ClickUp task management\n• `/webhook` - ClickUp webhook automation status",            inline=False
        )
        
        embed.add_field(
            name="🧪 UAT Testing Agent",
            value="• `/uat` - Test websites against 8 Marketing SOPs\n• `/sops` - Show the 8 UAT Testing SOPs",
            inline=False
        )
        
        embed.add_field(
            name="🎤 Voice Meeting Assistant",
            value="• `/meeting join` - Bot joins voice channel with real-time transcription\n• `/meeting stop` - Stop recording and generate AI-powered minutes\n• `/meeting status` - Check recording status and transcript stats",
            inline=False
        )
        
        embed.add_field(
            name="📊 System Monitoring",
            value="• `/status` - Show bot health and system information\n• `/sync` - Force sync Discord commands",
            inline=False
        )
        
        embed.add_field(
            name="💡 Example Commands",
            value="`/blog topic:'AI Marketing Trends' keywords:'AI, marketing, automation'`\n`/spinoff blog_content:'[paste blog content]' platforms:'all'`\n`/image prompt:'Professional marketing team' style:'modern'`\n`/carousel topic:'Digital Marketing Tips' slides:7`",
            inline=False
        )
        
        embed.add_field(
            name="🚀 Features",
            value="• AI-powered file analysis\n• Dynamic project channels\n• ClickUp integration\n• Nano Banana image generation\n• UAT testing with 8 Marketing SOPs\n• Real-time voice transcription & AI meeting minutes\n• Complete marketing workflows\n• Automatic ClickUp-to-Discord integration",            inline=False
        )
        
        embed.set_footer(text="AI-Powered Marketing Excellence • Results-Driven • Data-Informed")
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        if not interaction.response.is_done():
            await interaction.response.send_message(f"❌ Error: {str(e)}")
        else:
            await interaction.followup.send(f"❌ Error: {str(e)}")

# ===== VOICE MEETING COMMANDS =====

@bot.tree.command(name="meeting", description="🎤 Voice meeting assistant - join, stop, status")
async def cmd_meeting(interaction: discord.Interaction, action: str, channel: discord.VoiceChannel = None):
    """Voice meeting assistant commands"""
    try:
        if action == "join":
            if not channel:
                await interaction.response.send_message("❌ Please specify a voice channel to join!")
                return
            
            # Check if bot is already in a voice channel
            if hasattr(bot, 'voice_client') and bot.voice_client:
                await interaction.response.send_message("❌ Bot is already in a voice channel! Use `/meeting stop` first.")
                return
            
            # Start voice meeting
            success = await bot.start_voice_meeting(channel)
            if success:
                embed = discord.Embed(
                    title="🎤 Voice Meeting Started",
                    description=f"Bot joined **{channel.name}** and is now recording!",
                    color=bot.studio_config["accent_color"]
                )
                embed.add_field(
                    name="📝 What's Happening",
                    value="• Bot is transcribing your conversation\n• Real-time speech-to-text processing\n• Professional meeting minutes will be generated",
                    inline=False
                )
                embed.add_field(
                    name="🛑 To Stop",
                    value="Use `/meeting stop` when your meeting is finished",
                    inline=False
                )
                embed.set_footer(text="Voice Meeting Assistant • Creative Studio AI")
                
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.response.send_message("❌ Failed to join voice channel. Check bot permissions!")
                
        elif action == "stop":
            if not hasattr(bot, 'voice_client') or not bot.voice_client:
                await interaction.response.send_message("❌ Bot is not in any voice channel!")
                return
            
            await interaction.response.defer(thinking=True)
            
            # Stop voice meeting and generate minutes
            minutes = await bot.stop_voice_meeting()
            
            if minutes:
                # Create or get huddle-minutes channel
                guild = interaction.guild
                huddle_channel = discord.utils.get(guild.channels, name="huddle-minutes")
                
                if not huddle_channel:
                    # Create huddle-minutes channel
                    category = discord.utils.get(guild.categories, name="Projects")
                    if not category:
                        category = await guild.create_category("Projects")
                    
                    huddle_channel = await guild.create_text_channel(
                        "huddle-minutes",
                        category=category,
                        topic="Meeting minutes and huddle notes"
                    )
                
                # Send meeting minutes
                embed = discord.Embed(
                    title="📝 Meeting Minutes Generated",
                    description=f"**Meeting:** {interaction.channel.name}\n**Duration:** {bot.meeting_start_time.strftime('%H:%M')} - {datetime.now().strftime('%H:%M')}",
                    color=bot.studio_config["accent_color"]
                )
                # Split long minutes into multiple fields or use description
                if len(minutes) > 1024:
                    # Use description for long content
                    embed.description = minutes[:4096] + "..." if len(minutes) > 4096 else minutes
                else:
                    embed.add_field(
                        name="📋 Minutes",
                        value=minutes,
                        inline=False
                    )
                embed.set_footer(text="Voice Meeting Assistant • Creative Studio AI")
                
                await huddle_channel.send(embed=embed)
                await interaction.followup.send("✅ Meeting minutes generated and posted to #huddle-minutes!")
            else:
                await interaction.followup.send("❌ Failed to generate meeting minutes. Please try again.")
                
        elif action == "status":
            if hasattr(bot, 'voice_client') and bot.voice_client:
                activity_count = 0
                participants = set()
                if hasattr(bot, 'meeting_tracker'):
                    meeting_summary = bot.meeting_tracker.get_meeting_summary()
                    activity_count = len(meeting_summary['activity_log'])
                    participants = set(meeting_summary['participants'])
                
                embed = discord.Embed(
                    title="🎤 Meeting Status: Active",
                    description=f"Bot is tracking meeting in **{bot.voice_client.channel.name}**",
                    color=bot.studio_config["accent_color"]
                )
                embed.add_field(
                    name="📊 Meeting Stats",
                    value=f"**Started:** {bot.meeting_start_time.strftime('%H:%M:%S')}\n**Duration:** {datetime.now() - bot.meeting_start_time}\n**Activity Entries:** {activity_count}\n**Participants:** {len(participants)}",
                    inline=False
                )
                embed.add_field(
                    name="🎙️ Active Features",
                    value="✅ Voice channel connected\n✅ Meeting tracking active\n✅ Participant monitoring\n✅ AI meeting analysis ready",
                    inline=False
                )
                embed.add_field(
                    name="🛑 To Stop",
                    value="Use `/meeting stop` to end session and generate professional minutes",
                    inline=False
                )
            else:
                embed = discord.Embed(
                    title="🎤 Meeting Status: Inactive",
                    description="Bot is not currently in any voice channel",
                    color=bot.studio_config["error_color"]
                )
                embed.add_field(
                    name="🚀 To Start",
                    value="Use `/meeting join <voice_channel>` to start recording",
                    inline=False
                )
            
            embed.set_footer(text="Voice Meeting Assistant • Creative Studio AI")
            await interaction.response.send_message(embed=embed)
            
        else:
            await interaction.response.send_message("❌ Invalid action! Use: `join`, `stop`, or `status`")
            
    except Exception as e:
        logger.error(f"Meeting command error: {e}")
        if not interaction.response.is_done():
            await interaction.response.send_message(f"❌ Meeting error: {str(e)}")
        else:
            await interaction.followup.send(f"❌ Meeting error: {str(e)}")

# Debug: Check if commands are registered
print(f"Bot created. Commands registered: {len(bot.tree.get_commands())}")
for cmd in bot.tree.get_commands():
    print(f"  - /{cmd.name}: {cmd.description}")

# Global exception handler
def handle_exception(exc_type, exc_value, exc_traceback):
    """Global exception handler for unhandled errors"""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

# Set global exception handler
sys.excepthook = handle_exception

# Signal handlers for graceful shutdown
def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Run the bot
if __name__ == "__main__":
    try:
        # Validate environment variables
        required_vars = ['DISCORD_BOT_TOKEN', 'GEMINI_API_KEY']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            logger.error(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
            print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
            sys.exit(1)
        
        token = os.getenv('DISCORD_BOT_TOKEN')
        logger.info("✅ All required environment variables found")
        
        # Add error handling for bot startup
        try:
            # Start ClickUp webhook server
            run_webhook_server()
            logger.info("Starting Creative Studio AI...")
            
            # Run bot with improved connection settings
            bot.run(
                token, 
                reconnect=True,  # Enable automatic reconnection
                log_level=logging.INFO  # Set log level
            )
        except discord.errors.LoginFailure:
            logger.error("❌ Invalid Discord bot token!")
            print("❌ Invalid Discord bot token! Check your DISCORD_BOT_TOKEN environment variable.")
            sys.exit(1)
        except Exception as e:
            logger.error(f"❌ Bot startup error: {e}")
            logger.error(traceback.format_exc())
            print(f"❌ Bot startup error: {e}")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ Critical startup error: {e}")
        logger.error(traceback.format_exc())
        print(f"❌ Critical startup error: {e}")
        sys.exit(1)
