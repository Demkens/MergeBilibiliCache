import os
import json
import requests
import datetime
import subprocess
import shutil
from typing import Optional, Dict

def get_script_dir() -> str:
    """获取脚本所在目录"""
    return os.path.dirname(os.path.abspath(__file__))

def parse_entry(entry_path: str) -> Optional[Dict]:
    """解析分集目录下的entry.json"""
    try:
        with open(entry_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 处理空标题情况
        part_title = data.get("page_data", {}).get("part") or data.get("title") or f"cid_{data.get('page_data', {}).get('cid', 'unknown')}"
        
        return {
            "bvid": data.get("bvid", ""),
            "title": data.get("title", "未命名视频"),
            "up_name": data.get("owner_name", "未知UP主"),
            "part_title": part_title,
            "cover_url": data.get("cover", "").replace("\\/", "/"),
            "cid": data.get("page_data", {}).get("cid", ""),
            "time_create_stamp": data.get("time_create_stamp", 0)
        }
    except Exception as e:
        print(f"[解析错误] {entry_path}: {str(e)}")
        return None

def download_cover(url: str, save_path: str):
    """下载封面文件"""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                f.write(response.content)
    except Exception as e:
        print(f"[封面下载失败] {url}: {str(e)}")

def merge_videos():
    """主处理逻辑"""
    script_dir = get_script_dir()
    input_base = os.path.join(script_dir, "待处理文件夹")
    output1_base = os.path.join(script_dir, "输出文件夹1")
    output2_base = os.path.join(script_dir, "输出文件夹2")

    # 遍历所有BV号目录
    for bv_id in os.listdir(input_base):
        bv_path = os.path.join(input_base, bv_id)
        if not os.path.isdir(bv_path):
            continue

        # 遍历分集目录
        for part_dir in os.listdir(bv_path):
            part_path = os.path.join(bv_path, part_dir)
            entry_path = os.path.join(part_path, "entry.json")
            
            if not os.path.exists(entry_path):
                continue

            # 解析元数据
            meta = parse_entry(entry_path)
            if not meta:
                print(f"[错误] 无法解析 {part_path} 的元数据")
                continue

            # 生成时间格式化字符串
            try:
                create_time = datetime.datetime.fromtimestamp(meta["time_create_stamp"] / 1000)
                date_str = create_time.strftime("%Y%m%d")
            except Exception as e:
                print(f"[时间戳错误] {meta['time_create_stamp']}: {str(e)}")
                date_str = "00000000"

            # 构建文件名（强制非空）
            base_name = f"{date_str}_{meta['part_title'].strip() or '未命名视频'}"
            base_name = base_name.replace("/", "").replace("\\", "").replace("?", "").replace("<", "").replace(">", "").replace("*", "").replace(":", "").replace("|", "")  # 防止路径注入
            base_name_ = f"{meta['part_title'].strip() or '未命名视频'}"
            base_name_ = base_name_.replace("/", "").replace("\\", "").replace("?", "").replace("<", "").replace(">", "").replace("*", "").replace(":", "").replace("|", "")  # 防止路径注入
            
            # 定位媒体文件
            media_dir = os.path.join(part_path, "80")
            video_path = os.path.join(media_dir, "video.m4s")
            audio_path = os.path.join(media_dir, "audio.m4s")
            if not all(os.path.exists(p) for p in [video_path, audio_path]):
                media_dir = os.path.join(part_path, "64")
                video_path = os.path.join(media_dir, "video.m4s")
                audio_path = os.path.join(media_dir, "audio.m4s")
                if not all(os.path.exists(p) for p in [video_path, audio_path]):
                    media_dir = os.path.join(part_path, "32")
                    video_path = os.path.join(media_dir, "video.m4s")
                    audio_path = os.path.join(media_dir, "audio.m4s")
                    if not all(os.path.exists(p) for p in [video_path, audio_path]):
                        print(f"[错误] {part_dir} 缺少音视频文件")
                        continue

            # 创建输出路径
            try:
                output_dir = os.path.join(output1_base, meta["up_name"], base_name_)
                os.makedirs(output_dir, exist_ok=True)
                video_output = os.path.join(output_dir, f"{base_name}.mp4")
                cover_output = os.path.join(output_dir, f"{base_name}.jpg")
            except Exception as e:
                print(f"[路径创建失败] {output_dir}: {str(e)}")
                continue

            # 执行合并
            try:
                cmd = [
                    "ffmpeg",
                    "-i", video_path,
                    "-i", audio_path,
                    "-c:v", "copy",
                    "-c:a", "copy",
                    video_output,
                    "-y"
                ]
                subprocess.run(
                    cmd,
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                print(f"[成功] 已合并到 {video_output}")

                # 下载封面
                if meta["cover_url"]:
                    download_cover(meta["cover_url"], cover_output)
            except subprocess.CalledProcessError as e:
                print(f"[合并失败] {part_dir}")
                # 失败处理：转移到输出文件夹2
                fallback_dir = os.path.join(output2_base, bv_id, part_dir)
                os.makedirs(fallback_dir, exist_ok=True)
                try:
                    shutil.copy(video_path, os.path.join(fallback_dir, "video.m4s"))
                    shutil.copy(audio_path, os.path.join(fallback_dir, "audio.m4s"))
                    print(f"[备份] 原始文件已保存到 {fallback_dir}")
                except Exception as copy_error:
                    print(f"[备份失败] {str(copy_error)}")
            except Exception as e:
                print(f"[未知错误] {str(e)}")

if __name__ == "__main__":
    merge_videos()