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
        'extractor_args': {'youtube': {'player_client': ['ios']}}, # ลองเปลี่ยนเป็น iOS
        'nocheckcertificate': True,
        'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
    }

    # หมายเหตุ: ลองไม่ใช้ cookies.txt ชั่วคราว เพราะอาจเกิดปัญหา IP ไม่ตรง (403 Forbidden)
    # ถ้าจะใช้ ให้ uncomment บรรทัดข้างล่างนี้
    # if os.path.exists('cookies.txt'):
    #      print(f"Found cookies.txt at {os.path.abspath('cookies.txt')}")
    #      ydl_opts['cookiefile'] = 'cookies.txt'

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