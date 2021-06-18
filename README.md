# Screenshot Organizer (Works on macOS only)
Python script for automating the screenshot folder for Google Calendar Events.

Check out YouTube video about this script: https://www.youtube.com/watch?v=C0qgcsRvsOs

## Running the script:

1. Install dependencies:
```
pip install -r requirements.txt
```
2. Enable Google Calendar API and download `credentials.json`. You can refer to [this](https://developers.google.com/workspace/guides/create-project).
3. Set default screenshot location in the script.
4. Run the script:
```
python screenshot_organizer.py
```
## Troubleshooting

* Sometimes Google Calendar access token might expire. If the script does not print URL to visit and authenticate, then you can manually delete `token.json` and restart the script.
