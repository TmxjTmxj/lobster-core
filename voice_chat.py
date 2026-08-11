import os
"""
龙虾语音对话 — 本地实时对话
录音→Whisper→回复→TTS→播放
"""
import subprocess, os, sys, tempfile, json, requests, base64

# API配置
API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

def listen(seconds=5):
    """录音"""
    path = "/tmp/input.wav"
    subprocess.run(["arecord", "-d", str(seconds), "-f", "S16_LE", "-r", "16000", path], 
                   capture_output=True)
    return path

def transcribe(path):
    """Whisper转文字"""
    result = subprocess.run(["python3", "-m", "whisper", path, "--model", "tiny", 
                           "--language", "zh", "--output_format", "txt"],
                          capture_output=True, text=True, timeout=60)
    # 从输出中提取文字
    output = result.stdout
    if os.path.exists(path.replace(".wav", ".txt")):
        with open(path.replace(".wav", ".txt")) as f:
            output = f.read().strip()
    return output or "我没听清"

def think(text):
    """调用模型回复"""
    r = requests.post("https://opencode.ai/zen/go/v1/chat/completions",
        json={"model": "deepseek-v4-flash", "messages": [
            {"role": "system", "content": "你是龙虾，tmxj的AI秘书，回复简短口语化，像在打电话一样自然。"},
            {"role": "user", "content": text}
        ]},
        headers={"Authorization": f"Bearer {API_KEY}"}, timeout=15)
    return r.json()["choices"][0]["message"]["content"]

def speak(text):
    """TTS播放"""
    audio_path = "/tmp/output.mp3"
    subprocess.run(["edge-tts", "--text", text, "--voice", "zh-CN-XiaoxiaoNeural", 
                   "--write-media", audio_path], capture_output=True, timeout=20)
    subprocess.run(["ffplay", "-nodisp", "-autoexit", audio_path], 
                   capture_output=True, timeout=30)
    os.remove(audio_path)

def chat_round():
    """一轮对话"""
    print("\n🎤 录音中（5秒）...")
    audio = listen()
    print("📝 识别中...")
    text = transcribe(audio)
    print(f"   您说: {text}")
    print("🧠 思考中...")
    reply = think(text)
    print(f"   我说: {reply}")
    print("🗣️ 播放中...")
    speak(reply)
    os.remove(audio)
    return True

if __name__ == "__main__":
    import time
    speak("主人你好，我是龙虾。来聊天吧")
    for i in range(3):
        chat_round()
