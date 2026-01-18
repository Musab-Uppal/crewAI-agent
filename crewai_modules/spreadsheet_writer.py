from crewai.tools import BaseTool
from pydantic import BaseModel, Field
import google.auth
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
from dotenv import load_dotenv


load_dotenv()


class SpreadsheetInput(BaseModel):
    sheet_name: str = Field(..., description="The name of the sheet to write to.")
    headings: list = Field(..., description="Column headings (e.g., ['headline', 'date', 'sources', 'topic']).")
    data: dict = Field(..., description="The data to write to the sheet as a dictionary with keys matching headings.")


class SpreadsheetWriter(BaseTool):
    name: str = "Spreadsheet Writer Tool"
    description: str = "Writes data to a specified Google Sheets spreadsheet."
    args_schema: type[BaseModel] = SpreadsheetInput
    spreadsheet_id: str = ""
    service: object = None

    def __init__(self):
        spreadsheet_id = os.getenv("SPREADSHEET_ID")
        if not spreadsheet_id:
            raise ValueError("SPREADSHEET_ID not found in .env file")
        
        service = self._get_sheets_service()
        super().__init__(spreadsheet_id=spreadsheet_id, service=service)

    def _get_sheets_service(self):
        creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/spreadsheets"])
        return build('sheets', 'v4', credentials=creds)

    def _run(self, sheet_name: str, headings: list, data: dict) -> str:
        try:
            sheet = self.service.spreadsheets()
            
            # Get existing data to find the next available row
            result = sheet.values().get(
                spreadsheetId=self.spreadsheet_id,
                range=sheet_name
            ).execute()
            
            existing_values = result.get('values', [])
            
            # If no data exists, write headings first
            if not existing_values:
                headings_body = {'values': [headings]}
                sheet.values().append(
                    spreadsheetId=self.spreadsheet_id,
                    range=sheet_name,
                    valueInputOption="RAW",
                    body=headings_body
                ).execute()
                next_row = 2
            else:
                next_row = len(existing_values) + 1
            
            # Prepare data row based on headings order
            data_row = [data.get(heading, "") for heading in headings]
            
            # Write data to the next available row
            data_body = {'values': [data_row]}
            result = sheet.values().append(
                spreadsheetId=self.spreadsheet_id,
                range=f"{sheet_name}!A{next_row}",
                valueInputOption="RAW",
                body=data_body
            ).execute()
            
            return f"Successfully wrote data to row {next_row} in {sheet_name}."
        except HttpError as err:
            return f"An error occurred: {err}"
    
    async def _arun(self, sheet_name: str, headings: list, data: dict) -> str:
        raise NotImplementedError("Async not supported")