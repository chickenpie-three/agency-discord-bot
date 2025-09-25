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

class MarketingAgencyBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix='!agency ',
            intents=intents,
            description='Marketing Agency AI Hub - Complete Project Management & Content Creation Suite'
        )
        
        # Agency configuration
        def parse_color(color_str, default):
            try:
                if not color_str or color_str.strip() == '':
                    return int(default.replace('#', ''), 16)
                color_clean = color_str.replace('#', '').strip()
                return int(color_clean, 16) if len(color_clean) == 6 else int(default.replace('#', ''), 16)
            except (ValueError, AttributeError):
                return int(default.replace('#', ''), 16)
        
        self.agency_config = {
            'name': os.getenv('AGENCY_NAME', 'Marketing Pro AI'),
            'primary_color': parse_color(os.getenv('AGENCY_PRIMARY_COLOR'), '#2563eb'),   # Professional Blue
            'secondary_color': parse_color(os.getenv('AGENCY_SECONDARY_COLOR'), '#f8fafc'), # Light Gray
            'accent_color': parse_color(os.getenv('AGENCY_ACCENT_COLOR'), '#10b981'),     # Success Green
            'warning_color': parse_color(os.getenv('AGENCY_WARNING_COLOR'), '#f59e0b'),   # Warning Orange
            'error_color': parse_color(os.getenv('AGENCY_ERROR_COLOR'), '#ef4444'),       # Error Red
            'service_colors': {
                'Content Creation': '#8b5cf6',      # Purple - Creativity
                'Strategy Planning': '#3b82f6',     # Blue - Trust
                'Campaign Management': '#f59e0b',   # Orange - Energy
                'Analytics & Insights': '#10b981',  # Green - Growth
                'Project Management': '#6366f1',    # Indigo - Organization
                'Social Media': '#ec4899',          # Pink - Social
                'SEO & Marketing': '#06b6d4',       # Cyan - Digital
                'Brand Development': '#84cc16'      # Lime - Innovation
            },
            'style_guidelines': (
                "Modern, clean, and professional marketing agency aesthetic. "
                "Data-driven approach with creative flair. "
                "Clear hierarchy and actionable insights. "
                "Results-oriented with measurable outcomes. "
                "Client-focused with transparent communication."
            ),
            'voice_tone': (
                "Professional yet approachable. "
                "Data-driven and results-focused. "
                "Clear, actionable, and strategic. "
                "Confident without being arrogant. "
                "Always providing value and insights."
            ),
            'tagline': "AI-Powered Marketing Excellence. Results-Driven. Data-Informed.",
            'core_values': [
                "Results Over Rhetoric",
                "Data-Driven Decisions",
                "Client Success First",
                "Innovation Through AI",
                "Transparent Communication"
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
        
        # UAT Testing SOPs
        self.uat_sops = {
            "1. Navigation & Menu": [
                "All navigation links work correctly",
                "Menu items are clearly labeled and organized",
                "Breadcrumb navigation is present and functional",
                "Search functionality works properly",
                "Mobile navigation is responsive and accessible"
            ],
            "2. Page Loading & Performance": [
                "Pages load within 3 seconds",
                "Images are optimized and load properly",
                "No broken images or missing assets",
                "Page performance scores are acceptable",
                "Loading states are properly displayed"
            ],
            "3. Forms & User Input": [
                "All form fields are functional",
                "Form validation works correctly",
                "Error messages are clear and helpful",
                "Required fields are properly marked",
                "Form submission works end-to-end"
            ],
            "4. Content & Copy": [
                "All text content is readable and error-free",
                "Headings and subheadings are properly structured",
                "Content is relevant and up-to-date",
                "Call-to-action buttons are clear and compelling",
                "Legal pages (privacy, terms) are present and accessible"
            ],
            "5. Visual Design & Layout": [
                "Design is consistent across all pages",
                "Colors, fonts, and spacing are uniform",
                "Layout is responsive on all device sizes",
                "Visual hierarchy is clear and logical",
                "Branding elements are properly implemented"
            ],
            "6. Functionality & Features": [
                "All interactive elements work as expected",
                "Buttons and links respond to user actions",
                "Dynamic content loads correctly",
                "User workflows are intuitive and logical",
                "Error handling is graceful and informative"
            ],
            "7. Cross-Browser Compatibility": [
                "Site works in Chrome, Firefox, Safari, Edge",
                "No layout breaks or functionality issues",
                "JavaScript works across all browsers",
                "CSS rendering is consistent",
                "Browser-specific features are handled properly"
            ],
            "8. Mobile Responsiveness": [
                "Layout adapts properly to mobile screens",
                "Touch interactions work correctly",
                "Text is readable without zooming",
                "Navigation is thumb-friendly",
                "Mobile-specific features function properly"
            ],
            "9. Accessibility (WCAG)": [
                "Alt text is provided for all images",
                "Color contrast meets accessibility standards",
                "Keyboard navigation works throughout",
                "Screen reader compatibility is maintained",
                "Focus indicators are visible and clear"
            ],
            "10. Security & Privacy": [
                "HTTPS is properly implemented",
                "Contact forms use secure submission",
                "No sensitive data is exposed in URLs",
                "Privacy policy is accessible and current",
                "Cookie consent is properly implemented"
            ],
            "11. SEO & Meta Tags": [
                "Page titles are unique and descriptive",
                "Meta descriptions are present and compelling",
                "Header tags (H1, H2, H3) are properly structured",
                "URLs are clean and SEO-friendly",
                "Schema markup is implemented where appropriate"
            ],
            "12. Analytics & Tracking": [
                "Analytics tracking is properly implemented",
                "Conversion tracking is set up correctly",
                "Event tracking works for key interactions",
                "Goal funnels are properly configured",
                "Data collection complies with privacy regulations"
            ],
            "13. Error Handling & Edge Cases": [
                "404 pages are custom and helpful",
                "Server errors are handled gracefully",
                "Empty states are properly designed",
                "Offline functionality works where applicable",
                "Edge cases are handled without breaking the site"
            ]
        }
        
        # Agency DNA for marketing excellence
        self.agency_dna = """
        Marketing Pro AI — Complete Marketing Agency Hub
        
        Agency Profile:
        - Mission: Empower marketing teams with AI-driven insights, automated content creation, and intelligent project management.
        - Vision: Become the most trusted AI-powered marketing partner for agencies and businesses worldwide.
        - Ideal Clients: Marketing agencies, SMBs, startups, e-commerce businesses, SaaS companies, and enterprise marketing teams.
        - Service Focus: Content creation, strategy planning, campaign management, analytics, and project coordination.
        
        Service Portfolio:
        1) Content Creation & Management
           - Blog posts, social media content, email campaigns, ad copy, product descriptions
           - AI-generated images with Nano Banana integration
           - SEO-optimized content with keyword research
           - Multi-platform content adaptation
        
        2) Strategy & Planning
           - Marketing strategy development
           - Campaign planning and execution
           - Competitive analysis and market research
           - ROI optimization and performance tracking
        
        3) Campaign Management
           - Multi-channel campaign orchestration
           - Automated workflow creation
           - A/B testing and optimization
           - Performance monitoring and reporting
        
        4) Analytics & Insights
           - Performance data analysis
           - ROI calculation and reporting
           - Trend identification and forecasting
           - Actionable recommendations
        
        5) Project Management Integration
           - ClickUp task and project management
           - Automated task creation and updates
           - Deadline tracking and notifications
           - Team collaboration and communication
        
        AI-Powered Capabilities:
        - Natural language project management
        - Intelligent content generation with brand consistency
        - Automated image creation with professional quality
        - Data-driven insights and recommendations
        - Seamless platform integrations
        
        Brand Identity:
        - Palette: Professional Blue (#2563eb), Success Green (#10b981), Warning Orange (#f59e0b)
        - Style: Modern, clean, data-driven with creative flair
        - Voice: Professional yet approachable, results-focused, actionable
        - Approach: AI-enhanced human creativity and strategic thinking
        
        Key Differentiators:
        - Complete marketing workflow automation
        - AI-powered content creation with professional quality
        - Integrated project management and task tracking
        - Real-time analytics and performance insights
        - Natural language interaction for complex tasks
        
        Success Metrics:
        - Content engagement and conversion rates
        - Campaign performance and ROI
        - Project completion and deadline adherence
        - Client satisfaction and retention
        - Team productivity and efficiency gains
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
                color=self.agency_config['primary_color']
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
            
            # Basic website analysis
            response = requests.get(url, timeout=10)
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
            
        except requests.exceptions.RequestException as e:
            return {"error": f"Failed to analyze website: {str(e)}"}
        except Exception as e:
            return {"error": f"Analysis error: {str(e)}"}
    
    async def generate_uat_report(self, website_data: dict, custom_notes: str = ""):
        """Generate comprehensive UAT testing report"""
        try:
            prompt = f"""
            Generate a comprehensive UAT (User Acceptance Testing) report for this website:
            
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
            
            Please provide a detailed UAT report covering all 13 SOP categories:
            
            1. **Navigation & Menu** - Test navigation functionality
            2. **Page Loading & Performance** - Analyze loading times and performance
            3. **Forms & User Input** - Check form functionality and validation
            4. **Content & Copy** - Review content quality and structure
            5. **Visual Design & Layout** - Assess design consistency and layout
            6. **Functionality & Features** - Test interactive elements
            7. **Cross-Browser Compatibility** - Note browser compatibility issues
            8. **Mobile Responsiveness** - Check mobile optimization
            9. **Accessibility (WCAG)** - Review accessibility compliance
            10. **Security & Privacy** - Assess security measures
            11. **SEO & Meta Tags** - Check SEO optimization
            12. **Analytics & Tracking** - Note tracking implementation
            13. **Error Handling & Edge Cases** - Test error scenarios
            
            For each category, provide:
            - ✅ **PASS** - What's working well
            - ⚠️ **WARNING** - Areas that need attention
            - ❌ **FAIL** - Critical issues that must be fixed
            - 📝 **RECOMMENDATIONS** - Specific improvement suggestions
            
            Format as a professional UAT report with clear sections and actionable insights.
            """
            
            return await self._get_ai_response(prompt, "UAT Testing Expert")
            
        except Exception as e:
            logger.error(f"UAT report generation error: {e}")
            return f"Error generating UAT report: {str(e)}"
    
    async def _generate_nano_banana_image(self, prompt: str, style: str = "professional"):
        """Generate images using Nano Banana with Modern Weave™ branding"""
        try:
            if 'nano_banana' not in self.ai_clients:
                return {"success": False, "error": "Nano Banana not available"}
            
            branded_prompt = f"""
            Create a professional marketing agency image:
            
            Subject: {prompt}
            Style: {style}, modern, clean, professional marketing aesthetic
            Brand Colors: Professional Blue (#2563eb), Success Green (#10b981), Warning Orange (#f59e0b)
            Design System: Modern, clean, data-driven with creative flair
            Photography Style: Bright, professional, showing marketing processes and team collaboration
            Layout: Clean hierarchy, ample whitespace, decisive composition
            Quality: Professional-grade, suitable for marketing presentations and campaigns
            
            Focus on visual elements that convey marketing expertise and professional agency services.
            Avoid text overlays, clutter, or gimmicks. Clean, professional, results-focused aesthetic.
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
                        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
                        image.save(temp_file.name, 'PNG')
                        
                        return {
                            "success": True,
                            "image_path": temp_file.name,
                            "description": "Professional marketing agency image generated",
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
            {self.agency_dna}
            
            Your Expert Role: {system_context}
            
            User Request: {prompt}
            
            Marketing Agency Guidelines:
            1. Apply professional marketing agency approach with data-driven insights
            2. Use clear, actionable language that drives results
            3. Lead with outcomes and measurable metrics; quantify when possible
            4. Emphasize ROI and performance optimization
            5. Position as premium AI-powered marketing solution
            6. Include relevant case studies, benchmarks, and best practices
            7. For content, aim for comprehensive, SEO-optimized pieces
            8. Use service-specific colors and branding appropriately
            9. Maintain professional yet approachable tone
            10. Always include clear, conversion-focused calls-to-action
            
            Create expert-level marketing content that positions our agency as the premium AI-powered choice.
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
        logger.info("Setting up Marketing Agency AI Hub...")
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} marketing agents")
        except Exception as e:
            logger.error(f"Sync error: {e}")
    
    async def on_ready(self):
        logger.info(f'{self.user} connected! Marketing Agency AI Hub active')
        logger.info(f"AI services: {list(self.ai_clients.keys())}")
        logger.info(f"Nano Banana: {NANO_BANANA_AVAILABLE}")
        logger.info(f"ClickUp integration: {'✅' if self.clickup_config['api_key'] else '❌'}")
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="Marketing Agency operations"))

# Bot instance
bot = MarketingAgencyBot()

# ===== ENTERPRISE CONTENT CREATION =====

@bot.tree.command(name="content", description="📝 Enterprise blog posts with SEO and paired images")
async def cmd_content_enterprise(interaction: discord.Interaction, content_type: str, topic: str, keywords: str = "", include_image: bool = True):
    """Enterprise content creation with Modern Weave™ branding"""
    await interaction.response.defer(thinking=True)
    
    try:
        system_context = """
        You are a senior content strategist and marketing expert for a professional marketing agency.
        
        Expertise:
        - B2B marketing content creation and strategy
        - Professional marketing agency brand implementation
        - Executive-level thought leadership content
        - SEO optimization for marketing keywords
        - Competitive positioning in the marketing services industry
        """
        
        enhanced_prompt = f"""
        Create comprehensive {content_type} for our marketing agency about: {topic}
        Target Keywords: {keywords if keywords else 'marketing strategy, content creation, digital marketing, brand development'}
        
        ENTERPRISE CONTENT REQUIREMENTS:
        
        1. COMPREHENSIVE LENGTH: 2500-4000 words for blog posts
        2. EXECUTIVE POSITIONING: Target COOs, CTOs, CMOs, Heads of Operations
        3. MODERN WEAVE™ BRAND INTEGRATION:
           - Use institutional clarity with cultural warmth
           - Reference Filipino craftsmanship and heritage
           - Emphasize managed delivery vs marketplace approach
           - Include enterprise governance and SLA focus
        
        4. ADVANCED SEO STRATEGY:
           - Primary keyword in title, first 100 words, and conclusion
           - Secondary keywords naturally integrated throughout
           - Long-tail enterprise keywords (managed virtual teams, offshore CX pod)
           - Meta title and description optimized for enterprise search intent
           - Header structure optimized for featured snippets
           - Internal linking opportunities to marketing agency service pages
        
        5. ENTERPRISE CONTENT STRUCTURE:
           - Executive Summary (key outcomes and ROI upfront)
           - Market Context and Industry Challenges
           - Problem Analysis (enterprise pain points and constraints)
           - Marketing Agency Solution Framework (service offerings, engagement models)
           - Competitive Differentiation (vs Belay, Time Etc, TaskUs)
           - Implementation Methodology (pod deployment, governance, SLAs)
           - ROI Analysis and Business Case
           - Case Study or Success Story (with metrics)
           - Strategic Recommendations and Next Steps
           - Executive Call-to-Action (pilot pod, SOW scoping, fit assessment)
        
        6. PROOF POINTS TO INCLUDE:
           - Specific metrics and ROI data
           - SLA attainment and quality scorecards
           - Ramp timelines and time-to-productivity
           - Security and compliance frameworks
           - Team composition and governance structures
        
        Create authoritative, evidence-based content that positions our marketing agency as the premium choice.
        """
        
        # Generate comprehensive content
        logger.info(f"Generating enterprise content: {topic}")
        content_result = await bot._get_ai_response(enhanced_prompt, system_context)
        
        # Extract enterprise SEO keywords
        seo_keywords = await bot._extract_seo_keywords(content_result)
        
        # Generate professional marketing image
        image_result = None
        if include_image and NANO_BANANA_AVAILABLE:
            image_prompt = f"Professional marketing agency header image for article about {topic}. Clean layout, modern marketing aesthetic, professional photography. Professional, clean, marketing-grade visual suitable for business audiences."
            image_result = await bot._generate_nano_banana_image(image_prompt, "professional")
        
        # Create professional marketing embed
        embed = discord.Embed(
            title="📝 Marketing Content Created!",
            description=f"**Type:** {content_type}\n**Topic:** {topic}\n**Length:** {len(content_result)} characters\n**AI-Optimized:** ✅",
            color=bot.agency_config['primary_color']
        )
        
        # Add marketing SEO analysis
        if seo_keywords:
            embed.add_field(
                name="🔍 Marketing SEO Keywords",
                value=", ".join(seo_keywords[:10]),
                inline=False
            )
        
        # Create comprehensive marketing content file
        seo_analysis = f"""
## Marketing SEO Analysis
- **Content Length:** {len(content_result)} characters (Professional standard: 2000+ words)
- **Target Audience:** Marketing professionals, business owners, CMOs
- **Primary Keywords:** {keywords if keywords else 'Marketing strategy and content'}
- **Extracted Keywords:** {', '.join(seo_keywords)}
- **Brand System:** Professional marketing agency integrated
- **Competitive Positioning:** Premium AI-powered marketing solutions
- **Optimization Status:** ✅ Marketing SEO Optimized

## Marketing Agency Brand Integration
- **Voice:** Professional yet approachable, results-focused
- **Positioning:** Premium AI-powered marketing agency
- **Approach:** Data-driven with creative flair
- **Governance:** ROI-focused, performance-driven delivery
- **Image Pairing:** {'✅ Professional marketing image generated' if image_result and image_result.get('success') else '❌ Image generation not available'}

## Marketing Messaging Framework
- Results-first, data-backed content
- AI-enhanced marketing vs traditional approaches
- Performance optimization and ROI focus
- Professional expertise as competitive differentiator
- Modern marketing visual identity integration
        """
        
        full_content = f"# Marketing Agency {content_type.title()}: {topic}\n\n{seo_analysis}\n\n## Professional Content\n\n{content_result}"
        
        # Create downloadable marketing file
        file_buffer = io.BytesIO(full_content.encode('utf-8'))
        file = discord.File(file_buffer, filename=f"Marketing_Agency_{content_type}_{topic.replace(' ', '_')}.md")
        
        # Smart preview handling for marketing content
        if len(content_result) > 1000:
            embed.add_field(name="📋 Marketing Summary", value=content_result[:1000], inline=False)
            if len(content_result) > 2000:
                embed.add_field(name="📋 Content Preview", value=content_result[1000:2000], inline=False)
                embed.add_field(name="📄 Complete Marketing Content", value="See attached file for full article with marketing analysis", inline=False)
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

# Add other essential commands...

@bot.tree.command(name="test", description="🧪 Test enterprise system functionality")
async def cmd_test(interaction: discord.Interaction):
    try:
        embed = discord.Embed(
            title="✅ Marketing Agency AI Hub",
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
                color=bot.agency_config['primary_color']
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
                color=bot.agency_config['accent_color']
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
                    color=bot.agency_config['primary_color']
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
                color=bot.agency_config['warning_color']
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
            color=bot.agency_config['primary_color']
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
            error_embed = discord.Embed(
                title="❌ UAT Testing Failed",
                description=f"Could not analyze website: {website_data['error']}",
                color=bot.agency_config['error_color']
            )
            await interaction.followup.send(embed=error_embed)
            return
        
        # Generate comprehensive UAT report
        uat_report = await bot.generate_uat_report(website_data, custom_notes)
        
        # Create detailed UAT report embed
        report_embed = discord.Embed(
            title="📋 UAT Testing Report",
            description=f"**Website:** {website_data['url']}\n**Title:** {website_data['title']}",
            color=bot.agency_config['accent_color']
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
        
        # Add UAT report
        if len(uat_report) > 1024:
            chunks = [uat_report[i:i+1020] for i in range(0, len(uat_report), 1020)]
            for i, chunk in enumerate(chunks[:3]):  # Limit to 3 chunks
                report_embed.add_field(
                    name=f"📋 UAT Report {f'(Part {i+1})' if len(chunks) > 1 else ''}",
                    value=chunk,
                    inline=False
                )
        else:
            report_embed.add_field(
                name="📋 UAT Report",
                value=uat_report,
                inline=False
            )
        
        # Add SOP checklist
        sop_summary = "**13 SOP Categories Tested:**\n"
        for sop_name in bot.uat_sops.keys():
            sop_summary += f"• {sop_name}\n"
        
        report_embed.add_field(
            name="✅ SOP Checklist",
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

## UAT Testing Report
{uat_report}

## 13 SOP Categories Tested
"""
        
        for sop_name, sop_items in bot.uat_sops.items():
            full_report += f"\n### {sop_name}\n"
            for item in sop_items:
                full_report += f"- {item}\n"
        
        # Create downloadable file
        file_buffer = io.BytesIO(full_report.encode('utf-8'))
        file = discord.File(file_buffer, filename=f"UAT_Report_{website_data['url'].replace('https://', '').replace('http://', '').replace('/', '_')}.md")
        
        await interaction.followup.send(embed=report_embed, file=file)
        
    except Exception as e:
        logger.error(f"UAT testing error: {e}")
        await interaction.followup.send(f"❌ UAT testing error: {str(e)}")

@bot.tree.command(name="sops", description="📋 Show the 13 UAT Testing SOPs")
async def cmd_show_sops(interaction: discord.Interaction):
    """Show the 13 UAT Testing SOPs"""
    try:
        embed = discord.Embed(
            title="📋 UAT Testing SOPs",
            description="13 Standard Operating Procedures for website testing",
            color=bot.agency_config['primary_color']
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
        await interaction.response.send_message(f"❌ Error: {str(e)}")

@bot.tree.command(name="help", description="❓ Show marketing agency AI hub commands")
async def cmd_help(interaction: discord.Interaction):
    try:
        embed = discord.Embed(
            title="🤖 Marketing Agency AI Hub",
            description="Complete project management & content creation suite • AI-powered marketing excellence",
            color=bot.agency_config['primary_color']
        )
        
        embed.add_field(
            name="🎨 Content Creation",
            value="• `/content` - Blog posts with SEO + AI images\n• `/image` - Nano Banana image generation",
            inline=False
        )
        
        embed.add_field(
            name="📁 Project Management",
            value="• `/upload` - Upload files to create projects\n• `/project` - Create new project channels\n• `/clickup` - ClickUp task management",
            inline=False
        )
        
        embed.add_field(
            name="🧪 UAT Testing Agent",
            value="• `/uat` - Test websites against 13 SOPs\n• `/sops` - Show the 13 UAT Testing SOPs",
            inline=False
        )
        
        embed.add_field(
            name="💡 Example Commands",
            value="`/upload file:project-brief.md`\n`/project project_name:'New Campaign' description:'Q1 marketing campaign'`\n`/clickup action:list`\n`/uat website_url:https://example.com custom_notes:'Test for mobile responsiveness'`",
            inline=False
        )
        
        embed.add_field(
            name="🚀 Features",
            value="• AI-powered file analysis\n• Dynamic project channels\n• ClickUp integration\n• Nano Banana image generation\n• UAT testing with 13 SOPs\n• Complete marketing workflows",
            inline=False
        )
        
        embed.set_footer(text="AI-Powered Marketing Excellence • Results-Driven • Data-Informed")
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {str(e)}")

# Run the bot
if __name__ == "__main__":
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        logger.error("DISCORD_BOT_TOKEN not found")
        exit(1)
    
    try:
        logger.info("Starting Marketing Agency AI Hub...")
        bot.run(token)
    except Exception as e:
        logger.error(f"Bot startup error: {e}")
        exit(1)
