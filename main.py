import discord
from discord.ext import commands
import asyncio
import logging
import os
from dotenv import load_dotenv
import io
import json
import tempfile
import requests
from datetime import import datetime, timedelta
import aiofiles
from urllib.parse import urlparse
import asyncio
import signal
import sys
import traceback
from aiohttp import ClientSession

# Reconnect FIX - when disconnected or restarted
from discord.ext import commands

class ResumeHandler(discord.Client):
    async def handle_resumable(self, self, event):
        # Fix for the bot resume event.
        print("Bot resume event detected! Retrying login and restarting connection...")
        try:
            await self.bot.login()
            print("Reconnect login restarted.")
        except terror.LoginRequired:
            print("Reconnect failed login required. Retrying...")

    def add_resume_handler(self):
        bot.addEventListener("websocket.resumed", ResumeHandler())

# ... rest of main.py code
