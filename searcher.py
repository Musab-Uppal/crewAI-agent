from crewai.tools import BaseTool
from pydantic import BaseModel, Field
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()


class SearchInput(BaseModel):
    query: str = Field(..., description="The search query string.")


class Searcher(BaseTool):
    name: str = "Search Tool"
    description: str = "Search the internet using the Serper API and return structured results."
    args_schema: type[BaseModel] = SearchInput

    def _run(self, query: str) -> str:
        url = "https://google.serper.dev/search"

        payload = {
            "q": query,
            "num": 5
        }
        headers = {
            "X-API-KEY": os.environ.get("SERPER_API_KEY"),
            "Content-Type": "application/json"
        }

        response = requests.post(url, headers=headers, data=json.dumps(payload))

        if response.status_code != 200:
            return json.dumps({
                "query": query,
                "error": f"Request failed with status {response.status_code}",
                "results": []
            })

        data = response.json()
        organic_results = data.get("organic", [])

        results = []
        for item in organic_results:
            results.append({
                "title": item.get("title"),
                "link": item.get("link"),
                "snippet": item.get("snippet")
            })

        return json.dumps({
            "query": query,
            "results": results
        }, ensure_ascii=False)
    
    async def _arun(self, query: str) -> str:
        raise NotImplementedError("Async not supported")
