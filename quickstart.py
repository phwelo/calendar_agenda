#!/usr/bin/env python3

from __future__ import print_function
from flask import Flask, render_template
from flask_htmx import HTMX
import datetime
import os.path
import json
import random
import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
CALENDAR_ID = 'elissa.agans@gmail.com'
WTTR_CITY = "Detroit"

def auth():
  creds = None
  if os.path.exists('token.json'):
      creds = Credentials.from_authorized_user_file('token.json', SCOPES)
  # If there are no (valid) credentials available, let the user log in.
  if not creds or not creds.valid:
      if creds and creds.expired and creds.refresh_token:
          creds.refresh(Request())
      else:
          flow = InstalledAppFlow.from_client_secrets_file(
              'credentials.json', SCOPES)
          creds = flow.run_local_server(port=0)
      # Save the credentials for the next run
      with open('token.json', 'w') as token:
          token.write(creds.to_json())
  return creds

def no_events():
  print("No upcoming events were found.")

def events_list(calendar_id, client, event_count):
  now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
  calendar = [i for i in client.calendarList().list().execute()['items'] if i['id'] == calendar_id][0]
  events = client.events().list(
    calendarId=calendar['id'], 
    timeMin=now,
    maxResults=event_count, 
    singleEvents=True,
    orderBy='startTime'
  ).execute().get('items', [])
  if not events:
      no_events()
  else:
    for event in events:
        yield client.events().get(
          calendarId=calendar['id'], 
          eventId=event['id'], 
          alwaysIncludeEmail=None, 
          timeZone=None, 
          maxAttendees=None
        ).execute()

def icon_assigner(event):
  if 'birthday' in event['summary'].lower():
    return '🎂'
  elif 'zoe' in event['summary'].lower() and 'stella' in event['summary'].lower() or 'girls' in event['summary'].lower():
    return '👭'
  elif 'stella' in event['summary'].lower():
    return '👧🏻'
  elif 'zoe' in event['summary'].lower():
    return '👦🏻'
  elif 'mom' in event['summary'].lower():
    return '🤰'
  elif 'pay' in event['summary'].lower() or '$' in event['summary']:
    return '💲'
  elif 'gramma' in event['summary'].lower():
    return '👵🏻'
  elif 'dental' in event['summary'].lower() or 'dentist' in event['summary'].lower() or 'teeth' in event['summary'].lower() or 'tooth' in event['summary'].lower():
    return '🦷'
  elif 'psych' in event['summary'].lower() or 'therap' in event['summary'].lower():
    return '🤯'
  elif 'daniel' in event['summary'].lower():
    return '🖤'
  elif 'blood' in event['summary'].lower():
    return '🩸'
  else:
    return '📅'

def add_time(event):
  if 'date' in event['start']:
    return {'start_day': event['start']['date'].split('-')[2],
      'start_month': event['start']['date'].split('-')[1],
      'start_year': event['start']['date'].split('-')[0],
      'start_time':'All',
      'end_time': 'Day'
    }
  elif 'dateTime' in event['start']:
    return {'start_day': event['start']['dateTime'].split('T')[0].split('-')[2],
      'start_month':event['start']['dateTime'].split('T')[0].split('-')[1],
      'start_year': event['start']['dateTime'].split('T')[0].split('-')[0],
      'start_time': event['start']['dateTime'].split('T')[1].split('+')[0].split(':')[0] + ':' + event['start']['dateTime'].split('T')[1].split('+')[0].split(':')[1],
      'end_time': event['end']['dateTime'].split('T')[1].split('+')[0].split(':')[0] + ':' + event['end']['dateTime'].split('T')[1].split('+')[0].split(':')[1]
    }

def attribute_deleter(event):
  for attribute in ['creator', 'organizer', 'kind', 'etag', 'id', 'reminders', 'created', 'updated', 'sequence', 'iCalUID', 'recurringEventId', 'originalStartTime', 'attendees']:
    if attribute in event:
      del event[attribute]
  return event

def convert_twelve_time(time):
  if time['start_time'] == 'All':
    return time
  else:
    start = datetime.datetime.strptime(time['start_time'], "%H:%M")
    end = datetime.datetime.strptime(time['end_time'], "%H:%M")
    time['start_time'] = start.strftime("%I:%M%p")
    time['end_time'] = end.strftime("%I:%M%p")
    return time

def weather_grab():
  result = requests.get(f'http://wttr.in/{WTTR_CITY}?format=j2')
  return json.loads(result.text)

def pretty_date_today():
  now = datetime.datetime.now()
  return now.strftime("%B %d, %Y")

def generate_quote():
  f = open("quotes", "r")
  return random.choice(f.readlines())

def filter_events(events):
  for event in events:
    event = attribute_deleter(event)
    event['icon'] = icon_assigner(event)
    event['date'] = convert_twelve_time(add_time(event))
  return events

app = Flask(__name__)

@app.route("/")
def root_path():
  htmx = HTMX(app)
  quote = generate_quote()
  weather = weather_grab()
  if htmx:
    return '<h1>fart</h1>'
  else:
    return render_template(
      'index.html', 
      name='Elissa',
      quote=quote
    )

@app.route("/today")
def today_path():
  weather = weather_grab()
  return render_template(
    'today.html',
    date=pretty_date_today(),
    temp_f=weather['current_condition'][0]['temp_F'],
    weather=weather['current_condition'][0]['weatherDesc'][0]['value']
  )

@app.route("/events")
def events_path():
  creds = auth()
  client = build('calendar', 'v3', credentials=creds)
  calendar_entries = list(events_list(CALENDAR_ID, client, 25))
  calendar_entry_list = filter_events(calendar_entries)
  return render_template(
    'events.html',
    events=calendar_entry_list
  )

def main():
    app.run(host="0.0.0.0", debug=True)

if __name__ == '__main__':
    main()
