from __future__ import print_function
import datetime
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import subprocess
import time
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

# Location where screenshots will be located when not attending at any meeting
DEFAULT_SCREENSHOT_LOCATION = ''

# Sleep time represented in seconds before running kilall SystemUIServer
TIME_OFFSET = 5


def time_in_range(start, end, x):
    """Return true if x is in the range [start, end]"""
    if start <= end:
        return start <= x <= end
    else:
        return start <= x or x <= end


def scheduler_date(event_start_date, event_end_date, now, event_name):
    new_screenshot_location = DEFAULT_SCREENSHOT_LOCATION + '/' + event_name
    schedule_date = event_start_date - datetime.timedelta(seconds=TIME_OFFSET)

    # first check if path already exists. otherwise, check if we're in middle of event
    if os.path.exists(new_screenshot_location):
        schedule_date = None
    elif time_in_range(event_start_date, event_end_date, now):
        schedule_date = now

    return schedule_date


def fetch_events(start_date, end_date):
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
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

    service = build('calendar', 'v3', credentials=creds)

    # Call the Calendar API
    min_date = start_date.isoformat() + 'Z'  # 'Z' indicates UTC time
    max_date = end_date.isoformat() + 'Z'  # 'Z' indicates UTC time

    events_result = service.events().list(calendarId='primary',
                                          timeMin=min_date,
                                          timeMax=max_date,
                                          singleEvents=True,
                                          orderBy='startTime').execute()
    return events_result.get('items', [])


def run_bash_command(bashCmd):
    process = subprocess.Popen(bashCmd, stdout=subprocess.PIPE)
    output, error = process.communicate()

    if error is not None:
        print(error)


def change_screenshot_location(event_name=''):
    print('Changing screenshot location...')
    new_screenshot_location = DEFAULT_SCREENSHOT_LOCATION + '/' + event_name
    # Create folder if doesn't exisst
    if not os.path.exists(new_screenshot_location):
        os.makedirs(new_screenshot_location)

    # Change screenshot location
    bashCmd = ['defaults', 'write', 'com.apple.screencapture',
               'location', '"{}"'.format(new_screenshot_location)]
    run_bash_command(bashCmd)

    # We need this so that changes are applied
    time.sleep(TIME_OFFSET)
    bashCmd2 = ['killall', 'SystemUIServer']
    run_bash_command(bashCmd2)


def fetch_events_and_schedule():
    print('Getting the upcoming events')
    now = datetime.datetime.utcnow()
    start_date = now
    end_date = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    events = fetch_events(start_date, end_date)

    if not events:
        print('No upcoming events found.')
    for event in events:

        start = event['start'].get('dateTime', event['start'].get('date'))
        end = event['end'].get('dateTime', event['end'].get('date'))
        event_start_date = datetime.datetime.strptime(
            start, '%Y-%m-%dT%H:%M:%S%z')
        event_end_date = datetime.datetime.strptime(end, '%Y-%m-%dT%H:%M:%S%z')

        event_title = event['summary']

        unique_job_id = '{}-{}-{}'.format(start, end, event_title)

        folder_name = '{}_{}'.format(
            event_start_date.strftime('%Y%m%d%H%M'), event_title)
        possible_job = scheduler.get_job(unique_job_id)

        schedule_date = scheduler_date(
            event_start_date, event_end_date, datetime.datetime.now().astimezone(), folder_name)

        if possible_job is None and schedule_date is not None:
            print('Scheduling job for {}'.format(unique_job_id))

            scheduler.add_job(lambda: change_screenshot_location(
                folder_name), 'date', run_date=schedule_date, id=unique_job_id)

            # when event ends, reset screenshot folder
            scheduler.add_job(lambda: change_screenshot_location(),
                              'date', run_date=event_end_date)

        time.sleep(2)

    print('==================================')


def main():
    # we can already schedule job for checking if there's new events
    scheduler.add_job(fetch_events_and_schedule, 'interval',
                      seconds=15, id='fetch_events_and_schedule')
    scheduler.start()


if __name__ == '__main__':
    main()
    try:
        # keep the script running
        while True:
            time.sleep(2)
    except KeyboardInterrupt:
        print('Closing Google Calendar Automation...')
        print('Shutting down scheduler...')
        scheduler.shutdown(wait=False)
