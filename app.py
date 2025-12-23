import os
import shutil
from flask import Flask, after_this_request, render_template, request, send_file, jsonify
from flask_socketio import SocketIO
from pytubefix import YouTube, Playlist, Search

# Initialize Flask
app = Flask(__name__)
# Use an environment variable for security, fallback to default if not found
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'streamline_key_99')

# IMPORTANT: async_mode='eventlet' is required for Render/Gunicorn
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# --- Progress Callback ---
def progress_check(stream, chunk, bytes_remaining):
    total_size = stream.filesize
    bytes_downloaded = total_size - bytes_remaining
    percentage = (bytes_downloaded / total_size) * 100
    socketio.emit('progress', {'percentage': round(percentage, 1)})

# --- Page Routes ---
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/video')
def video_page():
    url = request.args.get('url', '')
    return render_template('video.html', url=url)

@app.route('/audio')
def audio_page():
    url = request.args.get('url', '')
    return render_template('audio.html', url=url)

@app.route('/playlist')
def playlist_page():
    url = request.args.get('url', '')
    return render_template('playlist.html', url=url)

@app.route('/captions')
def captions_page():
    url = request.args.get('url', '')
    return render_template('captions.html', url=url)

# --- Functional API Routes ---
@app.route('/search', methods=['POST'])
def handle_search():
    query = request.form.get('query')
    try:
        results = Search(query)
        video_list = []
        # Limiting to 6 to prevent timeouts
        for video in results.videos[:6]:
            video_list.append({
                'title': video.title,
                'url': video.watch_url,
                'thumbnail': video.thumbnail_url,
                'duration': video.length
            })
        return jsonify(video_list)
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/get_file/<filename>')
def get_file(filename):
    """Delivers the file (video, audio, or zip) and deletes it afterward."""
    path = os.path.join("downloads", filename)
    
    @after_this_request
    def cleanup(response):
        try:
            if os.path.exists(path):
                os.remove(path)
                print(f"Deleted file: {filename}")
        except Exception as e:
            print(f"Error cleaning up file {filename}: {e}")
        return response

    if os.path.exists(path):
        return send_file(path, as_attachment=True)
    else:
        return "File not found or expired.", 404

# --- WebSocket Events ---
@socketio.on('start_video_download')
def handle_video(data):
    try:
        yt = YouTube(data['url'], on_progress_callback=progress_check)
        stream = yt.streams.get_highest_resolution()
        file_path = stream.download(output_path="downloads/")
        socketio.emit('video_ready', {'file_url': f'/get_file/{os.path.basename(file_path)}'})
    except Exception as e:
        socketio.emit('error', {'message': str(e)})

@socketio.on('start_audio_download')
def handle_audio(data):
    try:
        yt = YouTube(data['url'], on_progress_callback=progress_check)
        stream = yt.streams.get_audio_only()
        file_path = stream.download(output_path="downloads/")
        socketio.emit('download_ready', {'file_url': f'/get_file/{os.path.basename(file_path)}'})
    except Exception as e:
        socketio.emit('error', {'message': str(e)})

@socketio.on('start_playlist_download')
def handle_playlist(data):
    try:
        pl = Playlist(data['url'])
        socketio.emit('playlist_info', {'title': pl.title, 'count': len(pl.videos)})
        
        # Create a specific folder for this playlist
        safe_title = "".join([c for c in pl.title if c.isalnum() or c in (' ', '_')]).rstrip()
        playlist_folder = os.path.join("downloads", safe_title)
        
        if not os.path.exists(playlist_folder):
            os.makedirs(playlist_folder)

        for index, video in enumerate(pl.videos):
            socketio.emit('next_video', {'index': index, 'title': video.title})
            try:
                video.streams.get_highest_resolution().download(output_path=playlist_folder)
            except Exception as e:
                print(f"Skipped video due to error: {e}")
            socketio.emit('video_done', {'index': index})

        # ZIP the folder
        socketio.emit('status', {'message': 'Zipping files...'})
        zip_filename = f"{safe_title}.zip"
        zip_path = os.path.join("downloads", zip_filename)
        
        # Create zip file
        shutil.make_archive(os.path.join("downloads", safe_title), 'zip', playlist_folder)
        
        # Remove the raw folder to save space immediately
        shutil.rmtree(playlist_folder)
        
        socketio.emit('playlist_complete', {'file_url': f'/get_file/{zip_filename}'})

    except Exception as e:
        socketio.emit('error', {'message': str(e)})

@socketio.on('fetch_captions')
def handle_captions(data):
    try:
        yt = YouTube(data['url'])
        tracks = [{'code': code, 'name': cap.name} for code, cap in yt.captions.items()]
        socketio.emit('captions_list', {'title': yt.title, 'tracks': tracks})
    except Exception as e:
        socketio.emit('error', {'message': str(e)})

@socketio.on('download_caption')
def handle_cap_dl(data):
    try:
        yt = YouTube(data['url'])
        caption = yt.captions[data['code']]
        
        # Fix: save_captions in pytubefix/pytube expects a filename without path in some versions, 
        # but to be safe we write manually to control the path perfectly.
        srt_content = caption.generate_srt_captions()
        
        safe_title = "".join([c for c in yt.title if c.isalnum() or c in (' ', '_')]).rstrip()
        filename = f"{safe_title}_{data['code']}.srt".replace(" ", "_")
        path = os.path.join("downloads", filename)

        with open(path, "w", encoding="utf-8") as f:
            f.write(srt_content)
        
        socketio.emit('caption_ready', {'file_url': f'/get_file/{filename}'})
    except Exception as e:
        socketio.emit('error', {'message': str(e)})

if __name__ == '__main__':
    # Ensure downloads directory exists
    if not os.path.exists('downloads'):
        os.makedirs('downloads')
    # Use standard run for local, Gunicorn handles prod
    socketio.run(app, debug=True)
