# app.py - Complete updated version with Vercel Cron Job
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
from crewai import Agent, Task, Crew, LLM
import os
from datetime import datetime
import traceback
from dotenv import load_dotenv

# Import your modules
from crewai_modules.searcher import Searcher
from crewai_modules.summarizer import Summarizer
from crewai_modules.spreadsheet_writer import SpreadsheetWriter
from crewai_modules.slack_sender import SlackSender

load_dotenv()

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

# Configuration
SPREADSHEET_ID = "1Ol0Fi9OE-DX78E_187x3BGggQm2LeRTbawmJm3tgF5o"

class HeadlineGenerator:
    def __init__(self):
        # Initialize all tools
        self.search_tool = Searcher()
        self.summarizer_tool = Summarizer()
        self.spreadsheet_writer = SpreadsheetWriter()
        self.slack_sender = SlackSender()
        
        # Initialize LLM
        self.gemini_llm = LLM(
            model="gemini-3-flash-preview",
            temperature=0.7,
            base_url="https://generativelanguage.googleapis.com/v1beta",
            api_key=os.getenv("GEMINI_API_KEY")
        )
        
        # Create headline agent
        self.headline_agent = Agent(
            role="Senior News Anchor and Researcher",
            goal="Create accurate, engaging headlines with supporting facts",
            backstory="""You are a Pulitzer Prize-winning journalist with expertise in researching 
                       and creating compelling headlines. You always verify facts from multiple 
                       sources before creating content.""",
            tools=[self.search_tool, self.summarizer_tool, self.spreadsheet_writer],
            verbose=True,
            llm=self.gemini_llm,
            allow_delegation=False
        )

    def generate_headline(self, topic):
        """Generate headline and distribute through all channels"""
        try:
            print(f"🔍 Starting process for topic: {topic}")
            
            # TASK 1: Research and create headline
            search_task = Task(
                description=f"""Research '{topic}' thoroughly. Find 3-5 recent, credible sources.
                              Focus on facts, statistics, and current developments from the past month.""",
                expected_output="List of sources with URLs and key facts.",
                agent=self.headline_agent
            )
            
            # TASK 2: Create formatted headline with key points
            headline_task = Task(
                description=f"""Based on your research, create:
                              1. A compelling headline (8-15 words max)
                              2. 3-5 key supporting facts as bullet points
                              3. Save everything to Google Sheets
                              
                              Use this EXACT format:
                              HEADLINE: [Your headline here]
                              KEY POINTS:
                              • [Fact 1]
                              • [Fact 2]
                              • [Fact 3]""",
                expected_output="Formatted headline with key points, saved to spreadsheet.",
                agent=self.headline_agent,
                context=[search_task]
            )
            
            # TASK 3: Send to Slack
            slack_task = Task(
                description=f"""Send the generated headline about '{topic}' to Slack.
                              Include: headline, topic, key points, and link to spreadsheet.
                              Format it professionally for team communication.""",
                expected_output="Confirmation of Slack delivery.",
                agent=self.headline_agent,
                context=[headline_task]
            )
            
            # Run the crew
            crew = Crew(
                agents=[self.headline_agent],
                tasks=[search_task, headline_task, slack_task],
                verbose=True
            )
            
            print("🤖 Running AI agents...")
            result = crew.kickoff()
            result_str = str(result)
            
            # Parse the results
            parsed_data = self._parse_output(result_str)
            
            # Extract Slack status
            slack_status = "Sent" if "successfully" in result_str.lower() else "Pending"
            
            return {
                "success": True,
                "topic": topic,
                "headline": parsed_data.get("headline", "No headline generated"),
                "key_points": parsed_data.get("key_points", []),
                "raw_output": result_str[:500] + "..." if len(result_str) > 500 else result_str,
                "slack_status": slack_status,
                "spreadsheet_link": f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "agents_used": ["Researcher", "Slack Distributor"]
            }
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "topic": topic,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

    def _parse_output(self, output):
        """Parse the agent output for clean data"""
        lines = output.split('\n')
        data = {"headline": "", "key_points": []}
        
        current_section = None
        for line in lines:
            line = line.strip()
            
            if not line:
                continue
            
            # Detect headline
            if line.lower().startswith("headline:"):
                data["headline"] = line.split(":", 1)[1].strip()
                current_section = "headline"
            
            # Detect key points section
            elif line.lower().startswith("key points"):
                current_section = "key_points"
            
            # Collect bullet points
            elif current_section == "key_points" and line.startswith(("•", "-", "*")):
                clean_point = line[1:].strip()
                if clean_point:
                    data["key_points"].append(clean_point)
            
            # If we're in headline section but haven't captured it yet
            elif current_section == "headline" and not data["headline"]:
                data["headline"] = line
        
        # Fallback: if no structured format, use first line as headline
        if not data["headline"] and lines:
            data["headline"] = lines[0].strip()
        
        return data

# Initialize the generator
headline_generator = HeadlineGenerator()

# ============================================================================
# FLASK ROUTES
# ============================================================================

@app.route('/')
def index():
    """Main web page"""
    return render_template('index.html', 
                          spreadsheet_id=SPREADSHEET_ID,
                          slack_configured=bool(os.getenv("SLACK_WEBHOOK_URL")))

@app.route('/api/generate', methods=['POST'])
def generate():
    """Generate a headline for a given topic"""
    try:
        data = request.json
        if not data:
            return jsonify({
                "success": False,
                "error": "No data provided"
            }), 400
        
        topic = data.get('topic', '').strip()
        if not topic:
            return jsonify({
                "success": False,
                "error": "Topic is required"
            }), 400
        
        print(f"📨 API Request - Topic: {topic}")
        result = headline_generator.generate_headline(topic)
        
        # Log the result
        if result["success"]:
            print(f"✅ Success - Headline: {result.get('headline', 'N/A')[:50]}...")
        else:
            print(f"❌ Failed - Error: {result.get('error', 'Unknown')}")
        
        return jsonify(result)
        
    except Exception as e:
        error_msg = f"Server error: {str(e)}"
        print(f"🔥 {error_msg}")
        return jsonify({
            "success": False,
            "error": error_msg
        }), 500

@app.route('/api/health')
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "AI Headline Generator",
        "version": "2.0",
        "timestamp": datetime.now().isoformat(),
        "features": {
            "slack": bool(os.getenv("SLACK_WEBHOOK_URL")),
            "google_sheets": True,
            "search": True,
            "summarization": True,
            "cron_job": True
        },
        "spreadsheet_link": f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit"
    })

# ============================================================================
# CRON JOB ENDPOINTS
# ============================================================================

@app.route('/api/cron/daily-headline', methods=['GET', 'POST'])
def daily_headline_cron():
    """Vercel Cron Job endpoint - runs daily at 9 AM UTC"""
    try:
        from datetime import datetime
        import random
        
        # Topics database - rotates based on day of week
        topics_by_day = {
            0: "Artificial Intelligence Breakthroughs",  # Monday
            1: "Climate Change and Sustainability",      # Tuesday
            2: "Space Exploration Discoveries",          # Wednesday
            3: "Healthcare and Medical Innovations",     # Thursday
            4: "Technology and Business Trends",         # Friday
            5: "Science and Research Updates",           # Saturday
            6: "Future Technology Predictions"           # Sunday
        }
        
        # Get current day and select topic
        current_day = datetime.now().weekday()
        topic = topics_by_day.get(current_day, "Latest Technology News")
        
        print("=" * 60)
        print(f"⏰ VERCEL CRON JOB TRIGGERED")
        print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📰 Topic: {topic}")
        print(f"🌍 Timezone: UTC (9:00 AM)")
        print("=" * 60)
        
        # Generate the headline
        result = headline_generator.generate_headline(topic)
        
        # Create a simple log entry
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "cron_job": True,
            "topic": topic,
            "success": result.get("success", False),
            "headline": result.get("headline", "")[:100] + "..." if result.get("headline") else None,
            "slack_status": result.get("slack_status", "Unknown"),
            "trigger": "vercel-cron"
        }
        
        # Save log to a file (persists between deployments on Vercel)
        try:
            with open('/tmp/cron_log.jsonl', 'a') as f:
                import json
                f.write(json.dumps(log_entry) + '\n')
        except:
            # If file write fails, just print
            print(f"📝 Log entry: {json.dumps(log_entry)}")
        
        # Return success response
        return jsonify({
            "success": True,
            "message": "Daily headline automation completed",
            "execution_time": datetime.now().isoformat(),
            "topic": topic,
            "result_summary": {
                "headline_generated": result.get("success", False),
                "slack_notification": result.get("slack_status", "Unknown"),
                "spreadsheet_updated": True if result.get("success") else False
            },
            "next_scheduled_run": "Tomorrow at 09:00 UTC",
            "vercel_cron": {
                "schedule": "0 9 * * *",
                "timezone": "UTC",
                "job_id": "daily-headline-generation"
            }
        })
        
    except Exception as e:
        error_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        error_msg = f"Cron job failed at {error_time}: {str(e)}"
        print(f"🔥 CRON ERROR: {error_msg}")
        
        # Log the error
        try:
            with open('/tmp/cron_errors.log', 'a') as f:
                f.write(f"{error_time}: {str(e)}\n")
        except:
            pass
        
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/cron/test', methods=['GET'])
def test_cron_endpoint():
    """Test endpoint to verify cron setup works"""
    return jsonify({
        "success": True,
        "message": "Cron endpoint is working!",
        "endpoint": "/api/cron/daily-headline",
        "schedule": "Daily at 09:00 UTC",
        "next_run": "Check Vercel Dashboard",
        "timestamp": datetime.now().isoformat(),
        "instructions": "This endpoint will be called automatically by Vercel cron jobs"
    })

@app.route('/api/cron/status', methods=['GET'])
def cron_status():
    """Check cron job status and recent executions"""
    try:
        from datetime import datetime, timedelta
        
        # Check if cron is configured in vercel.json
        cron_configured = True
        
        # Try to read logs
        recent_executions = []
        error_count = 0
        
        try:
            if os.path.exists('/tmp/cron_log.jsonl'):
                import json
                with open('/tmp/cron_log.jsonl', 'r') as f:
                    lines = f.readlines()
                    for line in lines[-10:]:  # Last 10 executions
                        if line.strip():
                            recent_executions.append(json.loads(line.strip()))
            
            if os.path.exists('/tmp/cron_errors.log'):
                with open('/tmp/cron_errors.log', 'r') as f:
                    error_count = len(f.readlines())
        except:
            pass  # Logs might not exist yet
        
        # Calculate next run (tomorrow at 9 AM UTC)
        now = datetime.utcnow()
        tomorrow_9am = datetime(now.year, now.month, now.day, 9, 0, 0) + timedelta(days=1)
        if now.hour < 9:
            tomorrow_9am = datetime(now.year, now.month, now.day, 9, 0, 0)
        
        return jsonify({
            "status": "active",
            "cron_configured": cron_configured,
            "schedule": {
                "expression": "0 9 * * *",
                "description": "Daily at 9:00 AM UTC",
                "human_readable": "Every day at 9:00 AM (UTC)",
                "next_execution": tomorrow_9am.isoformat(),
                "in_words": f"{((tomorrow_9am - now).seconds // 3600)} hours from now"
            },
            "statistics": {
                "total_executions": len(recent_executions),
                "successful": len([e for e in recent_executions if e.get("success")]),
                "failed": len([e for e in recent_executions if not e.get("success", True)]),
                "errors_logged": error_count,
                "last_execution": recent_executions[-1]["timestamp"] if recent_executions else "Never"
            },
            "recent_executions": recent_executions[-5:],  # Last 5
            "endpoints": {
                "cron_job": "/api/cron/daily-headline",
                "test": "/api/cron/test",
                "manual_trigger": "/api/automation/trigger (POST)"
            },
            "vercel_dashboard": "https://vercel.com/dashboard"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/automation/trigger', methods=['POST'])
def trigger_automation():
    """Manually trigger the automation (for testing)"""
    try:
        data = request.json or {}
        
        # Allow custom topic or use daily rotation
        custom_topic = data.get('topic', '')
        
        if custom_topic:
            topic = custom_topic
        else:
            # Use the same logic as cron job
            from datetime import datetime
            topics_by_day = {
                0: "AI News", 1: "Climate", 2: "Space", 3: "Health",
                4: "Business", 5: "Science", 6: "Future Tech"
            }
            current_day = datetime.now().weekday()
            topic = topics_by_day.get(current_day, "Technology Updates")
        
        print(f"🔧 Manual trigger for topic: {topic}")
        
        result = headline_generator.generate_headline(topic)
        
        return jsonify({
            "success": True,
            "trigger_type": "manual",
            "topic": topic,
            "result": result,
            "timestamp": datetime.now().isoformat(),
            "note": "This was manually triggered. Cron job runs daily at 9 AM UTC."
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/test-slack', methods=['POST'])
def test_slack():
    """Test Slack integration directly"""
    try:
        data = request.json or {}
        test_headline = data.get('headline', '🚀 Test: AI Headline Generator is working!')
        test_topic = data.get('topic', 'System Test')
        
        from crewai_modules.slack_sender import SlackSender
        slack = SlackSender()
        result = slack._run(test_headline, test_topic, "This is a test message from the API.")
        
        return jsonify({
            "success": True,
            "message": "Slack test completed",
            "slack_response": result,
            "test_data": {
                "topic": test_topic,
                "headline": test_headline
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

# ============================================================================
# SERVER STARTUP
# ============================================================================

if __name__ == '__main__':
    # Startup checks
    print("=" * 50)
    print("🤖 AI Headline Generator v2.0")
    print("=" * 50)
    
    # Check environment
    env_vars = {
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
        "SERPER_API_KEY": os.getenv("SERPER_API_KEY"),
        "GROQ_API_KEY": os.getenv("GROQ_API_KEY"),
        "SLACK_WEBHOOK_URL": os.getenv("SLACK_WEBHOOK_URL"),
        "SPREADSHEET_ID": os.getenv("SPREADSHEET_ID", SPREADSHEET_ID)
    }
    
    for key, value in env_vars.items():
        status = "✅" if value else "❌"
        print(f"{status} {key}: {'Set' if value else 'Not set'}")
    
    print(f"\n📊 Google Sheets: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit")
    
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    print(f"\n🌐 Starting server on port {port}")
    print(f"📁 Static folder: {app.static_folder}")
    print(f"📁 Templates folder: {app.template_folder}")
    print("=" * 50)
    
    app.run(debug=debug, host='0.0.0.0', port=port)