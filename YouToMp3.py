from flask import Flask, render_template, request, send_file, after_this_request
import yt_dlp
import os
import shutil
import time
import threading

app = Flask(__name__)

# โฟลเดอร์สำหรับเก็บไฟล์ชั่วคราว
DOWNLOAD_FOLDER = 'downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

def remove_file(filepath):
    try:
        # รอสักครู่เพื่อให้การส่งไฟล์เสร็จสิ้น
        time.sleep(10)
        if os.path.exists(filepath):
            os.remove(filepath)
            print(f"Removed file: {filepath}")
    except Exception as e:
        print(f"Error removing file: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert():
    video_url = request.form['url']
    
    # ตรวจสอบ FFmpeg
    ffmpeg_available = shutil.which('ffmpeg') is not None
    
    if not ffmpeg_available:
        print("Warning: ffmpeg not found. Fallback to default audio format.")

    # ตั้งค่า yt-dlp
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'{DOWNLOAD_FOLDER}/%(title)s.%(ext)s',
        'noplaylist': True,
        'nocheckcertificate': True,
    }

    # ตรวจสอบว่ามีไฟล์ cookies.txt หรือไม่
    if os.path.exists('cookies.txt'):
         print(f"Found cookies.txt at {os.path.abspath('cookies.txt')}")
         ydl_opts['cookiefile'] = 'cookies.txt'
         # เมื่อใช้ Cookies ให้ใช้ client แบบ web (default) เพื่อให้ตรงกับ Cookies
         if 'extractor_args' in ydl_opts:
             del ydl_opts['extractor_args']
    else:
         print("cookies.txt NOT FOUND in current directory, using Android client bypass")
         # ถ้าไม่มี Cookies ให้ลองใช้ Android client
         ydl_opts['extractor_args'] = {'youtube': {'player_client': ['android', 'web']}}

    # ถ้ามี FFmpeg ให้เพิ่ม postprocessors สำหรับแปลงเป็น MP3
    if ffmpeg_available:
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]

    try:
        if not video_url:
             return "กรุณาระบุลิงก์ YouTube", 400

        filename = None
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            filename = ydl.prepare_filename(info)
            
            if ffmpeg_available:
                base, ext = os.path.splitext(filename)
                mp3_filename = base + ".mp3"
                if os.path.exists(mp3_filename):
                    filename = mp3_filename
            
        if filename and os.path.exists(filename):
            # ตั้งค่าให้ลบไฟล์หลังจากส่งเสร็จ
            threading.Thread(target=remove_file, args=(filename,)).start()
            return send_file(filename, as_attachment=True)
        else:
             return "ไม่พบไฟล์ที่ดาวน์โหลด อาจเกิดข้อผิดพลาด", 500

        if filename and os.path.exists(filename):
            # ตั้งค่าให้ลบไฟล์หลังจากส่งเสร็จ (ใช้ thread แยกเพราะ after_this_request อาจทำงานก่อนส่งไฟล์เสร็จในบาง environment)
            threading.Thread(target=remove_file, args=(filename,)).start()
            
            return send_file(filename, as_attachment=True)
        else:
             return "ไม่พบไฟล์ที่แปลงแล้ว อาจเกิดข้อผิดพลาดในการแปลง (ตรวจสอบ FFmpeg)", 500

    except Exception as e:
        return f"เกิดข้อผิดพลาด: {str(e)}"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)