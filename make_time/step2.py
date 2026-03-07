from .mode2 import get_intervals_by_mode2
# pip install -U openai


def read_full_text(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()


def parse_zimu_content(filter_zimu):
    filter_zimu_list = []
    lines = filter_zimu.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        # 检查当前行是否是纯数字（序号）
        if line.isdigit():
            num = int(line)
            # 读取下一行（时间区间）
            if i + 1 < len(lines):
                time_duration = lines[i + 1].strip()
                # 检查时间区间格式是否正确（包含 -->）
                if '-->' in time_duration:
                    # 读取下下行（文本）
                    if i + 2 < len(lines):
                        text = lines[i + 2].strip()
                        # 添加到结果列表
                        # time_duration=00:08:04,866 --> 00:08:05,700
                        start = time_duration.split('-->')[0]
                        end = time_duration.split('-->')[1]
                        filter_zimu_list.append([num, [start.strip(), end.strip()], text])
                        i += 3  # 跳过已处理的3行
                        continue
        i += 1  # 继续处理下一行
    filter_zimu_list.sort(key=lambda x: x[0])
    return filter_zimu_list


def get_keep_intervals(zimu_path, wenan_content):
    zimu_content = read_full_text(zimu_path)
    zimu_list = parse_zimu_content(zimu_content)
    result = get_intervals_by_mode2(wenan_content, zimu_list)
    return result




