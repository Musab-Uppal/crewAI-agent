from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from groq import Groq
import os, json,requests

from dotenv import load_dotenv
load_dotenv()

class SummarizerInput(BaseModel):
    text: str = Field(description="The text to summarize")
class Summarizer(BaseTool):
    name: str = "Summarizer Tool"
    description: str = "Summarizes the given text."
    args_schema = SummarizerInput

    def _run(self, text: str) -> str:
        groq = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        response = groq.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes tsext concisely."},
                {"role": "user", "content": f"Please summarize the following text:\n\n{text}"}
            ],
            model="llama-3.1-8b-instant",
            max_tokens=600,
            temperature=0.7
        )
        return response.choices[0].message.content

    async def _arun(self, text: str) -> str:
        raise NotImplementedError("Async not supported")