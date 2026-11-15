# Diagnostic: records 6 s with several FFmpeg input layouts and counts video frames.
import os, re, subprocess, sys, tempfile, time
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ff = os.path.join(root, "release", "ffmpeg.exe")
dev = sys.argv[1] if len(sys.argv) > 1 else "CABLE Output (VB-Audio Virtual Cable)"
enc = ["-c:v", "av1_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", "32", "-b:v", "0", "-maxrate", "10M", "-bufsize", "20M", "-g", "120"]
aud = ["-c:a", "aac", "-b:a", "128k"]
dda = "ddagrab=output_idx=0:framerate=60"
V = {
 "fc+audio":        ["-f", "dshow", "-i", "audio=" + dev, "-init_hw_device", "d3d11va", "-filter_complex", dda + "[v]", "-map", "[v]", "-map", "0:a"],
 "lavfi+audio":     ["-init_hw_device", "d3d11va", "-f", "lavfi", "-i", dda, "-f", "dshow", "-i", "audio=" + dev, "-map", "0:v", "-map", "1:a"],
 "lavfi+audio buf50": ["-f", "lavfi", "-i", dda, "-f", "dshow", "-audio_buffer_size", "50", "-i", "audio=" + dev, "-map", "0:v", "-map", "1:a"],
 "lavfi+audio cfr": ["-f", "lavfi", "-i", dda, "-f", "dshow", "-i", "audio=" + dev, "-map", "0:v", "-map", "1:a", "-fps_mode", "cfr", "-r", "60"],
 "fc+audio cfr":    ["-f", "dshow", "-i", "audio=" + dev, "-filter_complex", dda + "[v]", "-map", "[v]", "-map", "0:a", "-fps_mode", "cfr", "-r", "60"],
 "lavfi no audio":  ["-f", "lavfi", "-i", dda, "-map", "0:v"],
}
for name, inp in V.items():
    out = os.path.join(tempfile.gettempdir(), "wrc_var.mp4")
    has_a = "audio" in name and "no audio" not in name
    cmd = [ff, "-hide_banner", "-loglevel", "warning", "-y"] + inp + enc + (aud if has_a else []) + ["-t", "6", out]
    t0 = time.time()
    p = subprocess.run(cmd, capture_output=True)
    took = time.time() - t0
    err = p.stderr.decode("utf-8", "replace").strip().splitlines()
    c = subprocess.run([ff, "-hide_banner", "-i", out, "-map", "0:v", "-c", "copy", "-f", "null", "-"], capture_output=True)
    m = re.findall(r"frame=\s*(\d+)", c.stderr.decode("utf-8", "replace"))
    print("%-20s rc=%d wall=%.1fs frames=%s  %s" % (name, p.returncode, took, m[-1] if m else "?", " | ".join(err[-2:])[:200]))
