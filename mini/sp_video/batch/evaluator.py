import json


def evaluate_quality(video_path, intervals):
    """简化版质量评分：基础逻辑，返回 0-10 分"""
    # 简化版：基于片段数量和时长的基础评分
    valid_count = len([i for i in intervals if i[0][0]])
    
    # 视频评分（4分）：片段数量合理性
    if valid_count >= 5:
        video_score = 4.0
    elif valid_count >= 3:
        video_score = 3.0
    else:
        video_score = 2.0
    
    # 拼接评分（3分）：片段越多，拼接点越多，扣分
    transition_score = max(0, 3.0 - (valid_count - 1) * 0.3)
    
    # 音频评分（3分）：基础分
    audio_score = 3.0
    
    total = video_score + transition_score + audio_score
    
    return {
        "video": round(video_score, 2),
        "transition": round(transition_score, 2),
        "audio": round(audio_score, 2),
        "total": round(total, 2)
    }
