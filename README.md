# YouPlex

YouPlex is a Flask-based web application that allows users to download YouTube videos, audio, playlists, and captions directly from a local browser interface.

## Features

- **Video Downloader**: Download specific videos in various qualities.
- **Audio Extraction**: Convert and download video audio.
- **Playlist Support**: Download entire playlists at once.
- **Captions**: Fetch subtitles for videos.
- **Real-time Progress**: SocketIO integration for live download tracking.

## Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install the required dependencies.

```bash
git clone [https://github.com/rishikumarxz513/YouPlex.github.io.git](https://github.com/rishikumarxz513/YouPlex.github.io.git)
cd YouPlex.github.io
pip install -r requirements.txt
```

Usage

To start the local web server, run the app.py file.

```bash
python app.py
```

Once the server is running, open your web browser and navigate to: http://127.0.0.1:5000 or localhost:5000

```bash
YouPlex/
├── downloads/           # Destination folder for downloaded media
├── static/
│   └── style.css        # Frontend styling
├── templates/           # HTML Interfaces
│   ├── audio.html
│   ├── captions.html
│   ├── index.html
│   ├── playlist.html
│   └── video.html
├── app.py               # Main application logic
└── requirements.txt     # Python dependencies
```
Requirements

Ensure your requirements.txt includes the following libraries:

```bash
Flask
Flask-SocketIO
pytubefix
```
