from crewai import Agent, Task, Crew, LLM
from searcher import Searcher
from summarizer import Summarizer
from spreadsheet_writer import SpreadsheetWriter
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize tools
search_tool = Searcher() 
summarizer_tool = Summarizer()
spreadsheet_writer = SpreadsheetWriter()

# Initialize LLM
gemini_llm = LLM(
    model="gemini-3-flash-preview",
    temperature=0.7,
    base_url="https://generativelanguage.googleapis.com/v1beta",
    api_key=os.getenv("GEMINI_API_KEY")
)

# Create agent
headline_agent = Agent(
    role="Senior News Anchor",
    goal="Create a headline about a given topic",
    backstory="You are a senior anchor person who searches the internet for articles about a given topic and generates summarized headlines.",
    tools=[search_tool, summarizer_tool, spreadsheet_writer],
    verbose=True,
    llm=gemini_llm,
    allow_delegation=False
)

# Define the topic
topic = "Advancements in Renewable Energy Technologies"


search_topic = Task(
    description=f"Search for the latest news and articles about {topic}",
    expected_output=f"A list of relevant news articles about {topic} with source URLs",
    agent=headline_agent
)

summarize_headline = Task(
    description=f"Create a concise headline about {topic} based on the searched articles. Then write the headline, date, sources, and topic to the spreadsheet using the Spreadsheet Writer tool. Use sheet name 'Headlines'",
    expected_output=f"A concise, informative headline about {topic} with relevant source URLs",
    agent=headline_agent,
    context=[search_topic]  # Use context to pass previous task results
)

write_to_spreadsheet = Task(
    description="Write the headline, date, sources, and topic to the spreadsheet using the Spreadsheet Writer tool.",
    expected_output="Confirmation that the data was written to the spreadsheet",
    agent=headline_agent,
    context=[summarize_headline]
)

# Create and run the crew
mycrew = Crew(
    agents=[headline_agent],
    tasks=[search_topic, summarize_headline, write_to_spreadsheet]
)

