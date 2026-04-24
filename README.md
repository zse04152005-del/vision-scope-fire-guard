# VisionScope Fire Guard

基于 YOLOv8 的校园多路实时火焰/烟雾智能检测系统。

---

## 快速开始（3 步上手）

### 第 1 步：安装 Python

如果电脑上还没有 Python，请先安装：

- 下载地址：https://www.python.org/downloads/
- **版本要求：Python 3.9 或更高**
- **Windows 用户注意：安装时务必勾选「Add Python to PATH」**

### 第 2 步：下载本项目

点击 GitHub 页面的绿色 **Code** 按钮 → **Download ZIP**，解压到任意位置。

或使用 Git 克隆：

```bash
git clone https://github.com/zse04152005-del/vision-scope-fire-guard.git
```

### 第 3 步：一键启动

**Windows 用户：** 双击 `run.bat`

**Mac / Linux 用户：** 打开终端，进入项目目录后运行：

```bash
bash run.sh
```

> 首次启动会自动安装所有依赖（需联网，约 2~5 分钟），之后再启动就是秒开。
>
> 首次启动还会弹出**设置向导**，引导你添加摄像头。

---

## 摄像头接入

系统支持三种视频源，全部可以在程序内「摄像头管理」界面中操作，**无需手动编辑任何配置文件**：

| 类型 | 说明 | 示例 |
|------|------|------|
| USB 摄像头 | 电脑自带或外接的摄像头 | 点击「扫描本地摄像头」自动检测 |
| 网络摄像头 | RTSP / HTTP 协议的 IP 摄像头 | 填入 IP、端口、用户名密码，自动拼接地址 |
| 视频文件 | 本地 mp4 / avi 视频 | 点击「选择视频文件」浏览导入 |

**操作路径：** 右侧面板 → 控制台 → 「摄像头管理」按钮

---

## 功能一览

### 核心检测
- 多路摄像头实时监控（最多 12 路同屏，可拖拽换位）
- YOLOv8 火焰/烟雾目标检测
- 火焰蔓延趋势分析（稳定/增长/蔓延三级判定）
- 低光环境自动增强（CLAHE 算法）

### 智能告警
- 连续命中去抖 + 冷却机制，减少误报
- 告警触发：红框闪烁 + 蜂鸣 + Toast 通知 + 摄像头高亮
- 告警录像：自动保存告警前后各 3 秒视频片段
- 智能阈值顾问：根据历史告警自动建议置信度调整
- ROI 关注区域：鼠标绘制多边形，仅区域内检测触发告警

### 可视化
- 校园地图火情态势图（加载平面图，拖拽放置摄像头，告警脉冲动画）
- 24 小时告警时间轴（点击跳转详情）
- 检测热力图叠加
- 火焰蔓延趋势折线图
- 深色/浅色主题一键切换

### 通知与导出
- 钉钉 / 企业微信 Webhook 推送
- SMTP 邮件通知
- 告警 CSV 一键导出（兼容 Excel）
- 事件自动记录到 `results/events.csv`

### 系统管理
- CPU / 内存 / GPU 实时监控
- RTSP 心跳断线自动重连
- 无头模式（`python main.py --headless`，纯后台推理+通知）
- 完整日志系统（`results/app.log`）

---

## 快捷键

| 快捷键 | 功能 |
|--------|------|
| `F11` | 全屏切换 |
| `Space` | 暂停 / 继续 |
| `Ctrl+S` | 保存截图 |
| `Ctrl+E` | 导出告警 CSV |
| `ESC` | 消音（停止蜂鸣和闪烁） |
| 双击摄像头画面 | 放大查看 |

---

## 项目结构

```
main.py                         入口文件
run.sh / run.bat                一键启动脚本
config.json                     运行配置（程序内可修改，无需手动编辑）
best.pt                         YOLOv8 模型权重
core/                           核心逻辑
  capture_worker.py               采集+推理线程
  alarm_logic.py                  告警去抖状态机
  alarm_saver.py                  告警截图保存
  alarm_clip.py                   告警录像保存
  spread_analyzer.py              火焰蔓延分析
  heatmap_accumulator.py          热力图累积
  image_enhance.py                低光增强
  roi_manager.py                  ROI 区域管理
  threshold_advisor.py            智能阈值顾问
  notifier.py                     Webhook/邮件通知
  system_monitor.py               系统监控
ui/                             界面组件
  camera_manager.py               摄像头管理（自动检测+预览）
  setup_wizard.py                 首次使用向导
  campus_map.py                   校园地图态势图
  roi_editor.py                   ROI 区域编辑器
  timeline_widget.py              告警时间轴
  trend_chart.py                  蔓延趋势图
  clip_player.py                  录像回放
  panels.py / theme.py / toast.py 面板/主题/通知
utils/                          工具
  config_loader.py                配置加载
  camera_config.py                摄像头配置
  logging_setup.py                日志系统
tests/                          单元测试（103 项）
```

---

## 配置说明

大部分配置可在程序界面内完成。如需手动编辑 `config.json`：

| 字段 | 说明 | 默认值 |
|------|------|--------|
| `model_path` | YOLO 权重路径 | `best.pt` |
| `alarm.conf_threshold` | 置信度阈值 | `0.5` |
| `alarm.hit_threshold` | 连续命中帧数 | `3` |
| `alarm.cooldown_seconds` | 告警冷却秒数 | `10` |
| `perf.infer_size` | 推理缩放长边像素（0=不缩放） | `0` |
| `enhance.low_light` | 低光增强开关 | `false` |
| `theme` | 主题（`dark` / `light`） | `dark` |

---

## 测试

```bash
python -m pytest tests/ -v
```

---

## 环境要求

- Python 3.9+
- 依赖包：ultralytics, opencv-python, PyQt6, psutil, requests
- 可选：pynvml（NVIDIA GPU 监控）
- 所有依赖由启动脚本自动安装，无需手动操作

---

## License

For academic use.
