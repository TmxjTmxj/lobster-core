"""龙虾视频分析 — 适配claude-video机制"""
import os
import subprocess, os
class VideoAnalyzer:
    def analyze(self, url: str, question: str = "描述这个视频") -> str:
        subprocess.run(["yt-dlp", "--write-auto-sub", "--sub-lang", "en,zh",
                       "--skip-download", "-o", "/tmp/video", url], capture_output=True, timeout=60)
        transcript = ""
        for f in ["/tmp/video.en.vtt", "/tmp/video.zh.vtt"]:
            if os.path.exists(f): transcript = open(f).read()[:2000]; break
        return f"视频: {url}\n字幕: {transcript[:500]}\n问题: {question}"
va = VideoAnalyzer()
