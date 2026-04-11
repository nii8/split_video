"""
multi_video_selector.py - 多视频输入结构

第三阶段最小版：只支持最简单的多视频输入结构。
"""


def build_video_sources(source_list):
    """
    构建视频源列表。

    输入格式：
    [
        {"video_id": "A001", "video_path": "...", "srt_path": "..."},
        {"video_id": "B002", "video_path": "...", "srt_path": "..."},
    ]

    返回格式：
    [{"video_id": "...", "video_path": "...", "srt_path": "..."}, ...]
    """
    sources = []
    for item in source_list:
        video_id = item.get("video_id")
        video_path = item.get("video_path")
        srt_path = item.get("srt_path")

        if not video_id or not video_path or not srt_path:
            print(f"[警告] 跳过无效视频源：{item}")
            continue

        sources.append(
            {
                "video_id": video_id,
                "video_path": video_path,
                "srt_path": srt_path,
            }
        )

    return sources


def get_main_video(sources):
    """
    获取主视频（默认第一个）。

    第三阶段最小版：直接选第一个视频作为主视频。
    """
    if not sources:
        return None
    return sources[0]


def get_sub_videos(sources):
    """
    获取副视频列表（除主视频外的其他视频）。

    第三阶段最小版：除第一个外都是副视频。
    """
    if len(sources) <= 1:
        return []
    return sources[1:]


if __name__ == "__main__":
    test_sources = [
        {"video_id": "A001", "video_path": "/path/A.mp4", "srt_path": "/path/A.srt"},
        {"video_id": "B002", "video_path": "/path/B.mp4", "srt_path": "/path/B.srt"},
        {"video_id": "C003", "video_path": "/path/C.mp4", "srt_path": "/path/C.srt"},
    ]

    sources = build_video_sources(test_sources)
    print(f"视频源数量：{len(sources)}")

    main = get_main_video(sources)
    print(f"主视频：{main['video_id'] if main else 'None'}")

    subs = get_sub_videos(sources)
    print(f"副视频数量：{len(subs)}")
