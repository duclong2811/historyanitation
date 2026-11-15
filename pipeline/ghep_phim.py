"""Bước 6: ghép khung hình + giọng + phụ đề + nhạc nền thành phim (output/<tên>.mp4).

    python pipeline/ghep_phim.py build/mau/shots.json
Dùng NVENC (chip mã hóa video trên card NVIDIA) nếu có, không thì libx264.
"""
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from chung import GOC, doc_json, thoi_luong_am_thanh

_BO_MA = None


def bo_ma_hoa():
    """Thử NVENC thật sự (có trong FFmpeg chưa chắc card dùng được), lỗi thì về libx264."""
    global _BO_MA
    if _BO_MA:
        return _BO_MA
    thu = subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=black:s=256x256:d=0.2",
                          "-c:v", "h264_nvenc", "-f", "null", "-"], capture_output=True)
    if thu.returncode == 0:
        _BO_MA = ["-c:v", "h264_nvenc", "-preset", "p5", "-cq", "19", "-b:v", "0"]
    else:
        _BO_MA = ["-c:v", "libx264", "-preset", "medium", "-crf", "18"]
    print(f"  Bộ mã hóa: {_BO_MA[1]}")
    return _BO_MA


def chay(cmd, cwd=None):
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", *cmd], cwd=cwd)
    if r.returncode:
        sys.exit(f"FFmpeg lỗi khi chạy: {' '.join(cmd)}")


def clip_shot(data, shot, build):
    khung = sorted((build / "khung" / shot["id"]).glob("f_*.png"))
    if not khung:
        sys.exit(f"Shot {shot['id']} chưa có khung hình. Chạy bước render trước.")
    fps, w, h = data["fps"], *data["kho"]
    buoc = 2 if data["on_twos"] else 1
    # Danh sách khung + thời gian hiện mỗi khung (on twos: mỗi khung giữ 2/30 giây)
    ds = build / "clip" / f"{shot['id']}.txt"
    ds.parent.mkdir(exist_ok=True)
    dong = []
    for k in khung:
        dong += [f"file '{k.as_posix()}'", f"duration {buoc / fps:.6f}"]
    dong.append(f"file '{khung[-1].as_posix()}'")
    ds.write_text("\n".join(dong), encoding="utf-8")
    dai = shot["thoi_luong"]
    am = (["-i", str(GOC / shot["giong"])] if shot.get("giong")
          else ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono"])
    out = build / "clip" / f"{shot['id']}.mp4"
    chay(["-f", "concat", "-safe", "0", "-i", str(ds), *am,
          "-vf", f"scale={w}:{h}:flags=lanczos,fps={fps},format=yuv420p",
          "-af", "apad", "-t", f"{dai:.3f}",
          *bo_ma_hoa(), "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2", str(out)])
    return out


def gio_ass(s):
    return f"{int(s // 3600)}:{int(s % 3600 // 60):02d}:{s % 60:05.2f}"


def phu_de(data, build):
    w, h = data["kho"]
    doc = h > w
    co, le, moi_dong = (74, 420, 4) if doc else (54, 70, 8)
    dau = (f"[Script Info]\nScriptType: v4.00+\nPlayResX: {w}\nPlayResY: {h}\nWrapStyle: 0\n\n"
           "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
           "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, "
           "Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
           f"Style: Default,Arial,{co},&H00FFFFFF,&H00FFFFFF,&H00101010,&H64000000,-1,0,0,0,100,100,0,0,1,"
           f"5,2,2,60,60,{le},1\n\n[Events]\n"
           "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    su_kien = []
    for s in data["shots"]:
        chu = s["noi"].split()
        cum = [" ".join(chu[i:i + moi_dong]) for i in range(0, len(chu), moi_dong)]
        noi_dai = (thoi_luong_am_thanh(GOC / s["giong"]) if s.get("giong") else None) or s["thoi_luong"] * 0.9
        tong = sum(len(c) for c in cum)
        t = s["bat_dau"]
        for c in cum:
            d = noi_dai * len(c) / tong
            su_kien.append(f"Dialogue: 0,{gio_ass(t)},{gio_ass(t + d)},Default,,0,0,0,,{c}")
            t += d
    (build / "phu_de.ass").write_text(dau + "\n".join(su_kien) + "\n", encoding="utf-8")


def ghep(shots_json):
    p = Path(shots_json)
    if not p.is_absolute():
        p = GOC / p
    data = doc_json(p)
    build = p.parent
    print("Ghép phim:")
    clips = [clip_shot(data, s, build) for s in data["shots"]]
    (build / "clip" / "ds.txt").write_text("\n".join(f"file '{c.as_posix()}'" for c in clips), encoding="utf-8")
    chay(["-f", "concat", "-safe", "0", "-i", "clip/ds.txt", "-c", "copy", "noi.mp4"], cwd=build)

    vao, loc_v, loc_a = ["-i", "noi.mp4"], [], "[0:a]anull[a]"
    if data["phu_de"]:
        phu_de(data, build)
        loc_v.append("subtitles=phu_de.ass")
    nhac = data.get("nhac_nen")
    if nhac and (GOC / nhac).exists():
        vao += ["-stream_loop", "-1", "-i", str(GOC / nhac)]
        loc_a = (f"[1:a]volume={data['am_luong_nhac']}[n];"
                 "[0:a][n]amix=inputs=2:duration=first:normalize=0[a]")
    loc = (f"[0:v]{','.join(loc_v) or 'null'}[v];{loc_a}")
    ra_dir = GOC / "output"
    ra_dir.mkdir(exist_ok=True)
    ra = ra_dir / f"{data['ten']}.mp4"
    chay([*vao, "-filter_complex", loc, "-map", "[v]", "-map", "[a]",
          *bo_ma_hoa(), "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(ra)], cwd=build)
    print(f"Xong: {ra.relative_to(GOC)}")
    return ra


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    if not shutil.which("ffmpeg"):
        sys.exit("Chưa có FFmpeg trong PATH.")
    ghep(sys.argv[1])
