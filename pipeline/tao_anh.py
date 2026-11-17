"""Chế độ ảnh AI, bước tạo ảnh: mỗi shot một ảnh anime vẽ bằng ComfyUI chạy trên máy bạn.

Cần bật ComfyUI trước (xem docs/anh-ai.md). Ảnh lưu ở build/<tên>/anh/sNN.png.
Shot nào prompt, hạt giống, model không đổi thì giữ ảnh cũ, không vẽ lại.

    python pipeline/tao_anh.py build/gia_dinh_1788_anime/shots.json [--chi s01,s03] [--ve-lai s02]

--ve-lai: vẽ lại các shot này với hạt giống mới (khi ảnh chưa ưng ý). Hạt giống mới được in ra
          để bạn ghi vào kịch bản (hat_giong) nếu muốn giữ.
"""
import json
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from chung import GOC, doc_json

AM_MAC_DINH = ("lowres, bad anatomy, bad hands, text, error, missing finger, extra digits, fewer digits, cropped, "
               "worst quality, low quality, low score, bad score, average score, signature, watermark, username, blurry")


def workflow_mac_dinh(a):
    """Workflow txt2img chuẩn của ComfyUI (định dạng API), kèm phóng to nếu có anh_ai.phong_to."""
    wf = {
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": a["mo_hinh"]}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": a["rong"], "height": a["cao"], "batch_size": 1}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": a["prompt"], "clip": ["4", 1]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": a["am"] or AM_MAC_DINH, "clip": ["4", 1]}},
        "3": {"class_type": "KSampler", "inputs": {
            "seed": a["hat_giong"], "steps": a["buoc"], "cfg": a["cfg"], "sampler_name": a["sampler"],
            "scheduler": a["scheduler"], "denoise": 1.0, "model": ["4", 0], "positive": ["6", 0],
            "negative": ["7", 0], "latent_image": ["5", 0]}},
        # Giải mã ảnh theo ô 512px: tốn ít bộ nhớ hơn nhiều, hợp với card 6GB
        "8": {"class_type": "VAEDecodeTiled", "inputs": {"samples": ["3", 0], "vae": ["4", 2], "tile_size": 512,
                                                          "overlap": 64, "temporal_size": 64, "temporal_overlap": 8}},
        "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "historyanitation", "images": ["8", 0]}},
    }
    if a.get("phong_to"):
        wf.update(chuoi_phong_to(a, ["8", 0]))
        wf["9"]["inputs"]["images"] = ["12", 0]
    return wf


def chuoi_phong_to(a, anh_vao):
    """Vẽ nhỏ cho nhanh rồi phóng to bằng AI (Real-ESRGAN anime x4), sau đó thu về đúng hệ số mong muốn.
    Chỉ phóng ảnh tĩnh của từng shot (vài ảnh), không phải từng khung video, nên rất nhanh."""
    return {
        "10": {"class_type": "UpscaleModelLoader", "inputs": {"model_name": a["phong_to"]}},
        "11": {"class_type": "ImageUpscaleWithModel", "inputs": {"upscale_model": ["10", 0], "image": anh_vao}},
        "12": {"class_type": "ImageScaleBy", "inputs": {"image": ["11", 0], "upscale_method": "lanczos",
                                                        "scale_by": float(a.get("he_so_phong", 2.0)) / 4.0}},
    }


def workflow_rieng(path, a):
    """Workflow tự làm trong ComfyUI (Save (API Format)), đặt các chỗ cần thay bằng {{prompt}}, {{am}},
    {{hat_giong}}, {{rong}}, {{cao}}. Dùng khi muốn thêm LoRA, upscale, ControlNet..."""
    txt = (GOC / path).read_text(encoding="utf-8")
    for k in ("prompt", "am"):
        txt = txt.replace("{{%s}}" % k, json.dumps(a[k] or (AM_MAC_DINH if k == "am" else ""))[1:-1])
    for k in ("hat_giong", "rong", "cao"):
        txt = txt.replace('"{{%s}}"' % k, str(a[k])).replace("{{%s}}" % k, str(a[k]))
    return json.loads(txt)


class ComfyUI:
    def __init__(self, may_chu):
        self.url = may_chu.rstrip("/")
        self.client_id = uuid.uuid4().hex

    def _goi(self, duong, du_lieu=None):
        req = urllib.request.Request(self.url + duong, data=du_lieu,
                                     headers={"Content-Type": "application/json"} if du_lieu else {})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            noi_dung = e.read().decode("utf-8", "replace")
            if "model_name" in noi_dung and "value_not_in_list" in noi_dung:
                sys.exit("ComfyUI không thấy model phóng to. Tải RealESRGAN_x4plus_anime_6B.pth vào "
                         "ComfyUI\\models\\upscale_models (xem docs/anh-ai.md) hoặc bỏ anh_ai.phong_to.")
            if "ckpt_name" in noi_dung or "value_not_in_list" in noi_dung:
                sys.exit(f"ComfyUI không thấy model. Model đang có: {self.danh_sach_model()}\n"
                         f"Sửa anh_ai.mo_hinh trong kịch bản cho khớp. Chi tiết: {noi_dung[:400]}")
            sys.exit(f"ComfyUI báo lỗi {e.code}: {noi_dung[:600]}")
        except urllib.error.URLError as e:
            sys.exit(f"Không kết nối được ComfyUI ở {self.url} ({e.reason}).\n"
                     "Mở ComfyUI trước (run_nvidia_gpu.bat), xem docs/anh-ai.md.")

    def danh_sach_model(self):
        try:
            d = json.loads(self._goi("/object_info/CheckpointLoaderSimple"))
            return d["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]
        except Exception:
            return "?"

    def ve(self, workflow, dich):
        r = json.loads(self._goi("/prompt", json.dumps({"prompt": workflow, "client_id": self.client_id}).encode()))
        pid = r["prompt_id"]
        t0 = time.time()
        while True:
            h = json.loads(self._goi(f"/history/{pid}"))
            if pid in h:
                muc = h[pid]
                if muc.get("status", {}).get("status_str") == "error":
                    sys.exit(f"ComfyUI vẽ lỗi: {json.dumps(muc['status'].get('messages', ''), ensure_ascii=False)[:600]}")
                for ra in muc.get("outputs", {}).values():
                    for anh in ra.get("images", []):
                        q = urllib.parse.urlencode({"filename": anh["filename"], "subfolder": anh["subfolder"],
                                                    "type": anh["type"]})
                        dich.write_bytes(self._goi(f"/view?{q}"))
                        return time.time() - t0
                if muc.get("status", {}).get("completed"):
                    sys.exit("ComfyUI chạy xong nhưng không trả về ảnh (workflow thiếu node SaveImage?).")
            print(f"\r  đang vẽ... {time.time() - t0:.0f} giây", end="", flush=True)
            time.sleep(1.0)


def tao(shots_json, chi=None, ve_lai=()):
    p = Path(shots_json)
    if not p.is_absolute():
        p = GOC / p
    data = doc_json(p)
    cfg = data["anh_ai"]
    out = p.parent / "anh"
    out.mkdir(exist_ok=True)
    comfy = ComfyUI(cfg.get("may_chu", "http://127.0.0.1:8188"))
    print("Tạo ảnh AI:")
    if data.get("che_do") == "lai":  # chế độ lai: vẽ ảnh nền của từng cảnh
        dung = {x["nen"] for x in data["shots"] if not chi or x["id"] in chi}
        muc = [{"id": k, **v} for k, v in data["nen"].items() if k in dung]
        chi = None
    else:
        muc = data["shots"]
    for s in muc:
        if chi and s["id"] not in chi:
            continue
        dich, h = out / f"{s['id']}.png", out / f"{s['id']}.hash"
        a = dict(s["anh"])
        if s["id"] in ve_lai:
            a["hat_giong"] = random.randrange(2 ** 32)
        elif dich.exists() and h.exists() and h.read_text() == s["hash_anh"]:
            print(f"  [{s['id']}] không đổi, giữ ảnh cũ")
            continue
        wf = workflow_rieng(a["workflow"], a) if a.get("workflow") else workflow_mac_dinh(a)
        print(f"  [{s['id']}] {a['prompt'][:90]}...")
        dt = comfy.ve(wf, dich)
        print(f"\r  [{s['id']}] xong trong {dt:.0f} giây, hạt giống {a['hat_giong']}          ")
        if s["id"] in ve_lai:
            print(f"      Ảnh mới được giữ cho tới khi bạn sửa prompt. Muốn cố định hẳn thì ghi vào kịch bản: "
                  f"hat_giong: {a['hat_giong']}")
        h.write_text(s["hash_anh"])


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    chi = a[a.index("--chi") + 1].split(",") if "--chi" in a else None
    ve_lai = a[a.index("--ve-lai") + 1].split(",") if "--ve-lai" in a else ()
    tao(next(x for x in a if x.endswith(".json")), chi, ve_lai)
