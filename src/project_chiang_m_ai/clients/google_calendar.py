import datetime
import os.path
from typing import Any, Dict, List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from project_chiang_m_ai.config import settings
from project_chiang_m_ai.interfaces.calendar import CalendarEvent, ICalendarProvider
from project_chiang_m_ai.logger import logger

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar"]


class GoogleCalendarClient(ICalendarProvider):
    """
    Client for interacting with the Google Calendar API.
    Handles authentication and event management (list, create, delete).
    """

    def __init__(self, token_path: str = "token.json"):
        """
        Initialize the Google Calendar client.

        Args:
            token_path (str): Path to store/load the user's access token.
                              Defaults to 'token.json' in current directory.
        """
        self.creds = None
        self.service = None
        self.token_path = token_path
        self.credentials_path = settings.GOOGLE_CALENDAR_CREDENTIALS_FILE

        if not self.credentials_path and not os.path.exists(self.token_path):
            # We can't do anything without credentials if we don't have a token
            # But maybe we have a token?
            pass

        self._authenticate()

    def _authenticate(self):
        """
        Authenticates with Google Calendar API using OAuth2.
        """
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists(self.token_path):
            self.creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)

        # If there are no (valid) credentials available, let the user log in.
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                except Exception as e:
                    logger.error(f"Error refreshing token: {e}")
                    self.creds = None

            if not self.creds:
                if not self.credentials_path:
                    raise ValueError(
                        "GOOGLE_CALENDAR_CREDENTIALS_FILE is not set in settings, "
                        "and no valid token.json found."
                    )
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(
                        f"Credentials file not found at: {self.credentials_path}"
                    )

                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                self.creds = flow.run_local_server(port=0)

            # Save the credentials for the next run
            with open(self.token_path, "w") as token:
                token.write(self.creds.to_json())

        self.service = build("calendar", "v3", credentials=self.creds)

    def list_upcoming_events(
        self, max_results: int = 10, calendar_id: str = "primary"
    ) -> List[CalendarEvent]:
        """
        Lists specific upcoming events on the calendar.

        Args:
            max_results (int): Maximum number of events to fetch.
            calendar_id (str): Calendar ID to query. Defaults to 'primary'.

        Returns:
            List[CalendarEvent]: A list of CalendarEvent objects.
        """
        try:
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            events_result = (
                self.service.events()
                .list(
                    calendarId=calendar_id,
                    timeMin=now,
                    maxResults=max_results,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            raw_events = events_result.get("items", [])

            # Convert to CalendarEvent objects
            calendar_events = []
            for event in raw_events:
                calendar_events.append(self._to_calendar_event(event))

            return calendar_events

        except HttpError as error:
            logger.error(f"An error occurred: {error}")
            return []

    def _to_calendar_event(self, google_event: Dict[str, Any]) -> CalendarEvent:
        """Convert Google Calendar event to CalendarEvent object."""
        # Parse start/end times
        start_str = google_event.get("start", {}).get("dateTime") or google_event.get(
            "start", {}
        ).get("date")
        end_str = google_event.get("end", {}).get("dateTime") or google_event.get(
            "end", {}
        ).get("date")

        # Parse to datetime objects
        start_dt = datetime.datetime.fromisoformat(start_str.replace("Z", "+00:00"))
        end_dt = datetime.datetime.fromisoformat(end_str.replace("Z", "+00:00"))

        return CalendarEvent(
            id=google_event.get("id", ""),
            summary=google_event.get("summary", ""),
            description=google_event.get("description"),
            start=start_dt,
            end=end_dt,
            raw_data=google_event,
        )

    def create_event(
        self,
        summary: str,
        start_time: str | datetime.datetime,
        end_time: str | datetime.datetime,
        description: Optional[str] = None,
        location: Optional[str] = None,
        calendar_id: str = "primary",
    ) -> Optional[CalendarEvent]:
        """
        Creates a new event in the calendar.

        Args:
            summary (str): Title of the event.
            start_time (str | datetime.datetime): Start time
            (ISO format string or datetime object).
            end_time (str | datetime.datetime): End time
            (ISO format string or datetime object).
            description (str, optional): Description of the event.
            location (str, optional): Location of the event.
            calendar_id (str): Calendar ID to add event to. Defaults to 'primary'.

        Returns:
            Optional[CalendarEvent]: The created CalendarEvent object,
                or None if failed.
        """

        # Helper to convert datetime to ISO string if needed
        def _ensure_iso(t):
            if isinstance(t, datetime.datetime):
                return t.isoformat()
            return t

        start_iso = _ensure_iso(start_time)
        end_iso = _ensure_iso(end_time)

        event = {
            "summary": summary,
            "location": location,
            "description": description,
            "start": {
                "dateTime": start_iso,
                "timeZone": "UTC",
            },
            "end": {
                "dateTime": end_iso,
                "timeZone": "UTC",
            },
        }

        try:
            created_event = (
                self.service.events()
                .insert(calendarId=calendar_id, body=event)
                .execute()
            )
            logger.info(f"Event created: {created_event.get('htmlLink')}")
            return self._to_calendar_event(created_event)
        except HttpError as error:
            logger.error(f"An error occurred: {error}")
            return None

    def delete_event(self, event_id: str, calendar_id: str = "primary") -> bool:
        """
        Deletes an event from the calendar.

        Args:
            event_id (str): The unique ID of the event to delete.
            calendar_id (str): Calendar ID. Defaults to 'primary'.

        Returns:
            bool: True if deletion was successful, False otherwise.
        """
        try:
            self.service.events().delete(
                calendarId=calendar_id, eventId=event_id
            ).execute()
            logger.info(f"Event deleted: {event_id}")
            return True
        except HttpError as error:
            logger.error(f"An error occurred: {error}")
            return False
