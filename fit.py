import fitdecode
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import ImageSequenceClip
import numpy as np
from datetime import timedelta
import os
from tqdm import tqdm
import platform

# 重要！！
# 请将此路径更改为您的实际FIT文件路径
fit_file_path = '******.fit'  #记录设备导出的fit文件路径

# 创建帧列表
frames = []

# 重要
# 更改视频叠加的分辨率、颜色、字体大小和字体
width, height = 1080, 1920  # 生成视频的分辨率
background_color = 'black'  # 背景颜色
font_color = 'white'  # 字体颜色
font_size = 50  # 字体大小

# 设置路径图尺寸
map_width, map_height = 500, 500  #生成路径图的分辨率
padding = 10  # 轨迹与地图边界的空白距离

# 提取经纬度信息
latitudes = []
longitudes = []
heart_rates = []
paces = []  # 存储以 分钟/公里 为单位的配速
cadences = []  # 用于存储步频数据
speeds = []  # 用于存储速度数据 (km/h)

# 设置起始时间戳
start_time = None

# 从文件底部读取统计数据
total_distance = None
total_timer_time = None
avg_heart_rate = None
avg_speed = None
avg_running_cadence = None

with fitdecode.FitReader(fit_file_path) as fitfile:
    for frame in fitfile:
        if isinstance(frame, fitdecode.records.FitDataMessage) and frame.name == 'session':
            total_distance = frame.get_value('total_distance')
            total_timer_time = frame.get_value('total_timer_time')
            avg_heart_rate = frame.get_value('avg_heart_rate')
            avg_speed = frame.get_value('avg_speed')
            avg_running_cadence = frame.get_value('avg_running_cadence')

def semicircles_to_degrees(semicircles):
    return semicircles * (180 / 2 ** 31)


# 加载图标
icons = {}
icon_folder = './icons'
for filename in os.listdir(icon_folder):
    if filename.endswith('.png'):
        key = filename.split('.')[0]  # 使用文件名作为键
        icon_path = os.path.join(icon_folder, filename)
        icons[key] = Image.open(icon_path)


# 加载图标到图像上
def load_icon(image, key, x, y, size):
    if key in icons:
        icon = icons[key].resize((size, size))  # 调整图标大小
        image.paste(icon, (x, y), icon)
    else:
        print(f"缺少图标: {key}")


# 替换文本为图标
def replace_text_with_icon(text, icon_key, icon_size):
    return (icon_key, text, icon_size)


# 字体路径
font_path = os.path.join("fonts", "cangeshuhei.ttf")  # 使用 os.path.join 拼接路径

# 加载字体
font = ImageFont.truetype(font_path, font_size)  # 字体类型
font_small = ImageFont.truetype(font_path, 20)  # 折线图上的字体大小设为20


# 处理记录数据并生成帧
with fitdecode.FitReader(fit_file_path) as fitfile:
    for i, frame in tqdm(enumerate(fitfile), desc="处理进度"):
        if isinstance(frame, fitdecode.records.FitDataMessage) and frame.name == 'record':
            distance = frame.get_value('distance') if frame.has_field('distance') else 0
            timestamp = frame.get_value('timestamp')
            speed = frame.get_value('speed') if frame.has_field('speed') else 0
            speed = speed if speed is not None else 0
            power = frame.get_value('power') if frame.has_field('power') else None
            heart_rate = frame.get_value('heart_rate') if frame.has_field('heart_rate') else None
            cadence = frame.get_value('cadence') if frame.has_field('cadence') else None
            step_length = frame.get_value('stance_length') if frame.has_field('stance_length') else None

            # 获取经纬度信息并解码
            if frame.has_field('position_lat') and frame.has_field('position_long'):
                latitude = semicircles_to_degrees(frame.get_value('position_lat'))
                longitude = semicircles_to_degrees(frame.get_value('position_long'))
                latitudes.append(latitude)
                longitudes.append(longitude)

            if speed == 0:
                pace_min, pace_sec = 0, 0
                speed_kmh = 0  # 速度为0
            else:
                # 计算配速 (分钟/公里)
                pace_min_km = 60 / (speed * 3.6)  # 将 speed (m/s) 转换为 km/h 后，再计算 分钟/公里
                pace_min = int(pace_min_km)
                pace_sec = int((pace_min_km - pace_min) * 60)
                speed_kmh = speed * 3.6  # 计算速度 km/h

            # 收集心率、配速和步频数据，排除0值和空值
            if heart_rate:
                heart_rates.append(heart_rate)
            if speed != 0:
                paces.append(pace_min_km)  # 存储以 分钟/公里 为单位的配速
                speeds.append(speed_kmh)  # 存储速度 (km/h)
            if cadence:
                cadences.append(2 * cadence)  # 将步频翻倍

            # 设置起始时间戳
            if start_time is None:
                start_time = timestamp

            # 计算耗时
            elapsed_time = timestamp - start_time
            hours, remainder = divmod(elapsed_time.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)

            # 调整时间为北京时间
            timestamp += timedelta(hours=8)

            # 创建图像并绘制文本
            image = Image.new('RGBA', (width, height), background_color)
            draw = ImageDraw.Draw(image)

            # ---  修改顶部文本显示，使用时和平均心率垂直对齐  ---
            avg_font_size = int(font_size * 2 / 3)  # 平均值字体大小
            avg_font = ImageFont.truetype(font_path, avg_font_size)

            # 距离和用时文本
            distance_text = f"距离: {int(total_distance)} m"
            total_time_seconds = total_timer_time if total_timer_time is not None else 0
            total_hours = int(total_time_seconds // 3600)
            total_minutes = int((total_time_seconds % 3600) // 60)
            total_seconds = int(total_time_seconds % 60)
            time_text = f"用时: {total_hours}:{total_minutes:02}:{total_seconds:02}"

            # 平均数据文本
            avg_pace_seconds = 1000 / avg_speed if avg_speed is not None and avg_speed != 0 else 0
            avg_pace_min = int(avg_pace_seconds // 60)
            avg_pace_sec = int(avg_pace_seconds % 60)
            avg_pace_text = f"平均配速: {avg_pace_min:02d}'{avg_pace_sec:02d}''"
            avg_heart_rate_text = f"平均心率: {int(avg_heart_rate)}" if avg_heart_rate is not None else "N/A"
            avg_cadence_text = f"平均步频: {int(avg_running_cadence * 2)}" if avg_running_cadence is not None else "N/A"

            # 计算每个文本块的宽度
            distance_text_width = draw.textlength(distance_text, font=avg_font)
            time_text_width = draw.textlength(time_text, font=avg_font)
            avg_pace_text_width = draw.textlength(avg_pace_text, font=avg_font)
            avg_heart_rate_text_width = draw.textlength(avg_heart_rate_text, font=avg_font)
            avg_cadence_text_width = draw.textlength(avg_cadence_text, font=avg_font)

            # 设置文本块之间的水平间距
            text_spacing_horizontal = 100

            # 计算每个文本块的 x 坐标，使两行文本靠左对齐
            distance_text_x = 50  # 距离左侧 50 像素
            time_text_x = distance_text_x + distance_text_width + text_spacing_horizontal
            avg_pace_text_x = 50  # 距离左侧 50 像素
            avg_heart_rate_text_x = time_text_x  # 与用时文本对齐
            avg_cadence_text_x = avg_heart_rate_text_x + avg_heart_rate_text_width + text_spacing_horizontal

            # 绘制顶部文本
            text_start_y = 60  # 从顶部算起，留出60的距离
            line_height = 50  # 每行文本高度，可根据需要调整

            # 第一行
            draw.text((distance_text_x, text_start_y), distance_text, font=avg_font, fill=font_color)
            draw.text((time_text_x, text_start_y), time_text, font=avg_font, fill=font_color)

            # 第二行
            draw.text((avg_pace_text_x, text_start_y + line_height), avg_pace_text, font=avg_font, fill=font_color)
            draw.text((avg_heart_rate_text_x, text_start_y + line_height), avg_heart_rate_text, font=avg_font,
                      fill=font_color)
            draw.text((avg_cadence_text_x, text_start_y + line_height), avg_cadence_text, font=avg_font,
                      fill=font_color)

            # 文本行
            # --- 修改配速显示 ---
            text_lines = [
                replace_text_with_icon(f"{int(distance)} m", 'draw_distance_icon', font_size),  # 去掉小数点
                replace_text_with_icon(f"{int(hours)}:{int(minutes)}'{int(seconds)}''", 'draw_time_icon', font_size),
                replace_text_with_icon(f"{pace_min:02d}'{pace_sec:02d}''", 'draw_pace_icon', font_size),  # 修改此处
                replace_text_with_icon(f"{heart_rate} bpm" if heart_rate is not None else "N/A", 'draw_heart_rate_icon',
                                       font_size),
                replace_text_with_icon(f"{2 * cadence} spm" if cadence is not None else "N/A", 'draw_cadence_icon',
                                       font_size),
            ]

            # 绘制路径图
            if latitudes and longitudes:
                min_lat, max_lat = min(latitudes), max(latitudes)
                min_long, max_long = min(longitudes), max(longitudes)
                lat_range = max_lat - min_lat
                long_range = max_long - min_long

                # 预先计算缩放比例，确保完整显示
                scale_lat = ((map_width * 1.5) - 2 * padding) / lat_range if lat_range != 0 else 1
                scale_long = ((map_height * 1.5) - 2 * padding) / long_range if long_range != 0 else 1
                scale = min(scale_lat, scale_long)

                path_image = Image.new('RGBA',
                                       (int(map_width * 1.5),
                                        int(map_height * 1.5)),
                                       (0, 0, 0, 0))
                path_draw = ImageDraw.Draw(path_image)

                points = []
                for lat, long in zip(latitudes, longitudes):
                    x = ((long - min_long) * scale) + padding
                    y = ((max_lat - lat) * scale) + padding  # 注意此处：将Y坐标翻转

                    points.append((x, y))

                path_draw.line(points, fill='white', width=8)  # 路径粗细为8

                # 绘制路径点
                for i, (lat, long) in enumerate(zip(latitudes, longitudes)):
                    x = ((long - min_long) * scale) + padding
                    y = ((max_lat - lat) * scale) + padding  # 注意此处：将Y坐标翻转

                    # 检查当前帧
                    if i == len(latitudes) - 1:  # 当前帧点
                        # 绘制当前帧路径点（自定义大小和颜色）
                        path_draw.ellipse((x - 9, y - 9, x + 9, y + 9),
                                           fill=(51, 161, 201))
                    else:
                        # 绘制其他路径点（白色）
                        path_draw.ellipse((x - 3, y - 3, x + 3, y + 3),
                                           fill='white')

                # 计算路径图应该粘贴到视频帧的位置，使其在视频左侧与上方顶部保持各200、200的距离
                map_position = (200, 200)

                # 将路径图粘贴到视频帧上
                image.paste(path_image, map_position, path_image)

            # 绘制每行文本
            text_area_height = height // 3
            max_text_lines = min(len(text_lines), text_area_height // (font_size + 5))
            text_height = max_text_lines * (font_size + 5)  # 计算文本的总高度
            text_start_y = height - text_height - 50  # 从底部算起，留出50的距离
            text_start_x = 50  # 距离左侧留50的距离
            for j, (icon_key, text, icon_size) in enumerate(text_lines[:max_text_lines]):
                if icon_key in icons:
                    icon = icons[icon_key].resize((icon_size, icon_size))  # 调整图标大小
                    icon_width, icon_height = icon.size
                    load_icon(image, icon_key, text_start_x, text_start_y + j * (font_size + 5), icon_size)
                    text_x = text_start_x + icon_width + 30  # 图标后留出30像素空白
                    draw.text((text_x, text_start_y + j * (font_size + 5)), text, font=font, fill=font_color)

            # 添加帧到列表
            frames.append(image)

# 生成折线图
def generate_line_graph(heart_rates, speeds, current_frame_index):
    # 创建折线图
    graph_width, graph_height = 600, 300
    graph_image = Image.new('RGBA', (graph_width, graph_height), (0, 0, 0, 0))
    graph_draw = ImageDraw.Draw(graph_image)

    # 设置纵轴显示范围
    max_hr = 220  # 心率最大值
    max_speed = 25  # 速度最大值 (km/h) - 可以根据需要调整

    # 获取心率和速度的实际最大值
    actual_max_hr = max(heart_rates) if heart_rates else 1
    actual_max_speed = max(speeds) if speeds else 1

    # 如果实际值超过上限，自动缩放
    if actual_max_hr > max_hr:
        max_hr = actual_max_hr
    if actual_max_speed > max_speed:
        max_speed = actual_max_speed

    # 横坐标时间
    time_intervals = np.linspace(0, graph_width, len(heart_rates))

    # 绘制心率折线图
    hr_points = [(time_intervals[i], graph_height - (hr / max_hr) * graph_height) for i, hr in enumerate(heart_rates)]
    graph_draw.line(hr_points, fill=(255, 48, 48), width=3)  # 心率颜色更改为红色

    # 绘制速度折线图
    speed_points = [(time_intervals[i], graph_height - (speed / max_speed) * graph_height) for i, speed in
                   enumerate(speeds)]
    graph_draw.line(speed_points, fill=(30, 144, 255), width=3)  # 速度颜色更改

    # 绘制当前帧对应点
    if 0 <= current_frame_index < len(heart_rates) and current_frame_index < len(speeds):
        # 绘制红线上的白点
        current_frame_x = time_intervals[current_frame_index]
        current_frame_y = graph_height - (heart_rates[current_frame_index] / max_hr) * graph_height
        graph_draw.ellipse((current_frame_x - 6, current_frame_y - 6, current_frame_x + 6, current_frame_y + 6),
                           fill='white', width=6)  # 白点直径8

        # 绘制蓝线上的白点
        current_frame_y = graph_height - (speeds[current_frame_index] / max_speed) * graph_height
        graph_draw.ellipse((current_frame_x - 6, current_frame_y - 6, current_frame_x + 6, current_frame_y + 6),
                           fill='white', width=6)  # 白点直径8

    return graph_image


# 生成一次完整的折线图
line_graph_image = generate_line_graph(heart_rates, speeds, 0)

# 检查是否有帧可处理
if not frames:
    print("没有帧可处理。请检查记录数据。")
    exit(1)

# 输出视频文件名
video_filename = start_time.strftime('%Y%m%d%H%M%S') + '_overlay.mp4'

# 默认采样率为每秒1帧
fps = 1

# 将折线图粘贴到每一帧
graph_position = (width - line_graph_image.width - 50, height - line_graph_image.height - 50)
for i, frame in enumerate(frames):
    # 生成当前帧的折线图，并将当前帧点设置为白色，粗细加倍
    line_graph_image = generate_line_graph(heart_rates, speeds, i)
    frame.paste(line_graph_image, graph_position, line_graph_image)

# 将PIL图像转换为numpy数组
frames_np = [np.array(frame) for frame in frames]

# 创建视频剪辑并写入文件
clip = ImageSequenceClip(frames_np, fps=fps)
clip.write_videofile(video_filename, fps=fps)

print(f'已导出到 {video_filename}')