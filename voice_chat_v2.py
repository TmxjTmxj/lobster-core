import os
"""
龙虾语音对话 v2 — 按键触发模式
按回车开始录音，说完自动识别回复
"""
import subprocess, sys, os, requests

API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

def speak(text):
    subprocess.run(["edge-tts", "--text", text, "--voice", "zh-CN-XiaoxiaoNeural",
                   "--write-media", "/tmp/say.mp3"], capture_output=True, timeout=20)
    subprocess.run(["ffplay", "-nodisp", "-autoexit", "/tmp/say.mp3"], capture_output=True, timeout=30)

def listen():
    subprocess.run(["arecord", "-d", "4", "-f", "S16_LE", "-r", "16000", "/tmp/in.wav"], capture_output=True)

def transcribe():
    """Vosk本地离线语音识别"""
    import json, wave
    from vosk import Model, KaldiRecognizer
    
    model = Model("/tmp/vosk-model")
    wf = wave.open("/tmp/in.wav", "rb")
    rec = KaldiRecognizer(model, wf.getframerate())
    
    while True:
        data = wf.readframes(4000)
        if len(data) == 0: break
        rec.AcceptWaveform(data)
    
    result = json.loads(rec.FinalResult())
    text = result.get("text", "").strip()
    return text if text else "嗯?"

def think(text):
    r = requests.post("https://opencode.ai/zen/go/v1/chat/completions",
        json={"model": "deepseek-v4-flash", "messages": [
            {"role": "system", "content": "你是龙虾，tmxj的私人AI秘书。回复简短口语化，不要过于骚，像正常打电话一样自然。"},
            {"role": "user", "content": text}
        ]},
        headers={"Authorization": f"Bearer {API_KEY}"}, timeout=15)
    return r.json()["choices"][0]["message"]["content"]

speak("主人，龙虾准备好了。按回车开始说话")
print("\n🦞 语音对话就绪！按 Enter 开始说话，说完等4秒自动识别")
print("   输入 q 退出\n")

while True:
    cmd = input(">> 按 Enter 说话 (q退出): ")
    if cmd.lower() == 'q': break
    
    print("🎤 录音中（4秒）...")
    listen()
    print("📝 识别中...")
    text = transcribe()
    print(f"   您说: {text}")
    
    if not text or text == "嗯?":
        speak("我没听清，您再说一遍")
        continue
    
    print("🧠 思考中...")
    reply = think(text)
    print(f"   我说: {reply}")
    speak(reply)

speak("主人再见")
