
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
from crewai import Agent, Task, Crew, LLM
import os
from datetime import datetime
import traceback
from dotenv import load_dotenv

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
        
    
        self.headline_agent = Agent(
            role="Senior News Anchor and Researcher",
            goal="Create accurate, engaging headlines with supporting facts then write to Google Sheets and send to Slack.",
            backstory="""You are a Pulitzer Prize-winning journalist with expertise in researching 
                       and creating compelling headlines. You always verify facts from multiple 
                       sources before creating content.""",
            tools=[self.search_tool, self.summarizer_tool, self.spreadsheet_writer,self.slack_sender],
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
                              Focus on facts, statistics, and current developments from the past month.
                              Return sources as a formatted list.""",
                expected_output="List of sources with URLs and key facts.",
                agent=self.headline_agent
            )
            
            # TASK 2: Create formatted headline with key points and save to Google Sheets
            headline_task = Task(
                description=f"""Based on your research of '{topic}', create:
                              1. A compelling headline (8-15 words max)
                              2. 3-5 key supporting facts as bullet points
                              3. Save everything to Google Sheets with columns: headline, date, sources, topic
                              
                              Use the Spreadsheet Writer tool with:
                              - sheet_name: "Headlines"
                              - headings: ["headline", "date", "sources", "topic"]
                              - data: {{"headline": "your headline", "date": "today's date", "sources": "source list", "topic": "{topic}"}}
                              
                              Output format:
                              HEADLINE: [Your headline here]
                              DATE: [Today's date]
                              SOURCES: [Source URLs]
                              TOPIC: {topic}
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
                description=f"""Send the generated headline about '{topic}' to Slack using the Slack Sender tool.
                              Extract from the previous output:
                              - headline: the main headline
                              - topic: {topic}
                              - sources: the sources found
                              
                              Call the Slack Sender tool with these extracted values.
                              Make sure the message is sent successfully.""",
                expected_output="Confirmation of Slack delivery with status message.",
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

# Flask Routes
@app.route('/')
def index():
    return render_template('index.html', 
                          spreadsheet_id=SPREADSHEET_ID,
                          slack_configured=bool(os.getenv("SLACK_WEBHOOK_URL")))

@app.route('/api/generate', methods=['POST'])
def generate():
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
    return jsonify({
        "status": "healthy",
        "service": "AI Headline Generator",
        "version": "2.0",
        "timestamp": datetime.now().isoformat(),
        "features": {
            "slack": bool(os.getenv("SLACK_WEBHOOK_URL")),
            "google_sheets": True,
            "search": True,
            "summarization": True
        },
        "spreadsheet_link": f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit"
    })

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
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

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