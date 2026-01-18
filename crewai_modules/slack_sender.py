# crewai_modules/slack_sender.py
import os
import requests
from datetime import datetime
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

class SlackInput(BaseModel):
    headline: str = Field(..., description="The generated headline")
    topic: str = Field(..., description="The topic used for generation")
    sources: str = Field("", description="Sources or key points")

class SlackSender(BaseTool):
    name: str = "Slack Sender Tool"
    description: str = "Sends generated headlines to a Slack channel using webhooks"
    args_schema: type[BaseModel] = SlackInput
    webhook_url: str = ""
    spreadsheet_id: str = ""

    def __init__(self):
        webhook_url = os.getenv("SLACK_WEBHOOK_URL", "")
        spreadsheet_id = "1Ol0Fi9OE-DX78E_187x3BGggQm2LeRTbawmJm3tgF5o"
        super().__init__(webhook_url=webhook_url, spreadsheet_id=spreadsheet_id)

    def _create_slack_message(self, headline: str, topic: str, sources: str = "") -> dict:
        """Create a formatted Slack message"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*📰 New Headline Generated*\n_{timestamp}_"
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{headline}*"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Topic:* {topic}\n*Sources:* {sources if sources else 'See spreadsheet for details'}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"<https://docs.google.com/spreadsheets/d/{self.spreadsheet_id}/edit|📊 View in Spreadsheet>"
                }
            }
        ]
        
        return {"blocks": blocks}

    def _run(self, headline: str, topic: str, sources: str = "") -> str:
        """Send message to Slack"""
        if not self.webhook_url:
            return "Error: SLACK_WEBHOOK_URL not found in environment variables"
        
        try:
            # Format the message
            message = self._create_slack_message(headline, topic, sources)
            
            # Send to Slack
            response = requests.post(self.webhook_url, json=message, timeout=10)
            
            if response.status_code == 200:
                return "Successfully sent to Slack channel!"
            else:
                return f"Failed to send to Slack. Status: {response.status_code}, Response: {response.text}"
                
        except requests.exceptions.Timeout:
            return "Error: Slack request timed out"
        except Exception as e:
            return f"Error sending to Slack: {str(e)}"

    
    async def _arun(self, headline: str, topic: str, sources: str = "") -> str:
        raise NotImplementedError("Async not supported")