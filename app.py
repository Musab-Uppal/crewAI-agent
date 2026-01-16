from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from crewai import Agent, Task, Crew, LLM
from searcher import Searcher
from summarizer import Summarizer
from spreadsheet_writer import SpreadsheetWriter
import os
from datetime import datetime
import json
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

class HeadlineGenerator:
    def __init__(self):
        # Initialize tools
        self.search_tool = Searcher() 
        self.summarizer_tool = Summarizer()
        self.spreadsheet_writer = SpreadsheetWriter()
        
        # Initialize LLM
        self.gemini_llm = LLM(
            model="gemini-3-flash-preview",
            temperature=0.7,
            base_url="https://generativelanguage.googleapis.com/v1beta",
            api_key=os.getenv("GEMINI_API_KEY")
        )
        
        # Create agent
        self.headline_agent = Agent(
            role="Senior News Anchor",
            goal="Create a headline about a given topic",
            backstory="You are a senior anchor person who searches the internet for articles about a given topic and generates summarized headlines.",
            tools=[self.search_tool, self.summarizer_tool, self.spreadsheet_writer],
            verbose=True,
            llm=self.gemini_llm,
            allow_delegation=False
        )
    
    def generate_headline(self, topic):
        try:
            # Define tasks
            search_topic = Task(
                description=f"Search for the latest news and articles about {topic}",
                expected_output=f"A list of relevant news articles about {topic} with source URLs",
                agent=self.headline_agent
            )
            
            summarize_headline = Task(
                description=f"Create a concise headline about {topic} based on the searched articles. Then write the headline, date, sources, and topic to the spreadsheet using the Spreadsheet Writer tool. Use sheet name 'Headlines'",
                expected_output=f"A concise, informative headline about {topic} with relevant source URLs",
                agent=self.headline_agent,
                context=[search_topic]
            )
            
            # Create and run the crew
            mycrew = Crew(
                agents=[self.headline_agent],
                tasks=[search_topic, summarize_headline],
                verbose=True
            )
            
            # Execute the crew
            result = mycrew.kickoff()
            
            return {
                "success": True,
                "headline": str(result),
                "topic": topic,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "topic": topic
            }

headline_generator = HeadlineGenerator()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/generate', methods=['POST'])
def generate():
    try:
        data = request.json
        topic = data.get('topic', '').strip()
        
        if not topic:
            return jsonify({"success": False, "error": "Topic is required"})
        
        result = headline_generator.generate_headline(topic)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

if __name__ == '__main__':
    app.run(debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true', 
            host='0.0.0.0', 
            port=int(os.getenv('PORT', 5000)))