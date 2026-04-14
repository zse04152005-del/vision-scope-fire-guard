# VisionScope Fire Guard

基于改进 YOLOv8 的多路实时火焰/烟雾检测系统。提供桌面监控大屏、告警中心、事件落库与截图、深/浅主题、Webhook 通知与系统资源监控。

## 功能亮点

### 监控与检测
- 多路摄像头大屏（最多 12 路，支持拖拽换位并持久化）
- YOLOv8 实时火/烟检测，主画面参数联动
- 响应式网格：未显式配置 `grid_cols` 时按窗口宽自动 2/3/4 列重排
- F11 全屏、双击画面放大、摄像头管理（新增/删除/测试/保存）
- 支持 USB 摄像头、RTSP、本地视频/图片导入

### 告警与事件
- 命中去抖（`hit_threshold` 连续帧 + `cooldown` 冷却）
- 告警触发：主窗红框闪烁 + 蜂鸣 + 右下角滑入 Toast 通知 + 摄像头位高亮
- 告警中心：搜索 / 等级过滤 / 详情弹窗（原图 + 标注图对照）
- **一键导出**告警为 CSV（UTF-8 BOM，兼容 Excel 直接打开）
- 事件自动落库到 `results/events.csv`，字段顺序稳定
- **DingTalk / 企业微信 Webhook** 通知（异步 fire-and-forget，5s 超时）

### 性能与稳定性
- 全局 `model_lock` 保证共享 YOLO 实例线程安全
- `perf.max_fps` 限制推理频率；`perf.infer_size` 按长边缩放送推理
- RTSP 心跳检测：`heartbeat_timeout` 秒无帧主动释放并重连
- `CameraWorker.stop()` 3 秒超时后强制 `terminate()`，避免关闭挂死
- 主程序 YOLO 模型加载失败弹窗提示后优雅退出

### 体验与 UI
- 深色 / 浅色主题一键切换，选择写回 `config.json` 持久化
- 摄像头状态「●/○ 脉搏呼吸」动画（ONLINE 时）
- 按钮统一 Unicode 符号前缀（▶ ■ ‖ ⚙ ◉ 等）
- 全局样式由 `ui_theme.py` 集中管理，颜色常量化
- 告警中心最多渲染最新 500 条，避免大数据量卡顿（完整数据仍支持导出/过滤）

### 系统监控与日志
- 顶部状态栏实时显示 `CPU | 内存 | GPU`（psutil + 可选 pynvml）
- 全局 `logging` 系统（RotatingFileHandler → `results/app.log`，按大小滚动）
- 配置 schema fallback：缺字段 / 坏 JSON 自动回落 `DEFAULT_CONFIG`

## 环境依赖

- Python 3.10+
- PyQt6、ultralytics、opencv-python、psutil
- 可选：requests（Webhook 通知）、pynvml（NVIDIA GPU 监控）

```bash
conda create -n fireguard python=3.10 -y
conda activate fireguard
python -m pip install ultralytics opencv-python PyQt6 psutil requests
# 如缺 torch
python -m pip install torch
# 如需 GPU 监控
python -m pip install pynvml
```

## 运行

```bash
python fire_detection_system.py
```

## 配置 `config.json`

| 字段 | 说明 |
|---|---|
| `model_path` | YOLO 权重路径（默认 `best.pt`） |
| `output_dir` | 输出目录（默认 `results`） |
| `theme` | `dark` 或 `light`，默认 `dark` |
| `grid_cols` | 固定列数；留空则响应式 |
| `alarm.hit_threshold` | 连续命中帧数触发告警 |
| `alarm.cooldown_seconds` | 告警冷却秒数 |
| `alarm.conf_threshold` | 置信度阈值 |
| `alarm.interval_s` | 推理间隔秒数 |
| `perf.max_fps` | 推理最大帧率（0 不限制） |
| `perf.infer_size` | 长边缩放至该像素送推理（0 不缩放） |
| `perf.heartbeat_timeout` | 无帧心跳超时（秒，默认 5.0） |
| `webhook.dingtalk_url` | 钉钉群机器人 URL（空则禁用） |
| `webhook.wecom_url` | 企业微信群机器人 URL（空则禁用） |
| `logging.level` | `INFO` / `DEBUG` / `WARNING` |
| `logging.max_bytes` | 单个日志文件大小上限（字节） |
| `logging.backup_count` | 滚动保留份数 |

### 摄像头示例

```json
{
  "cameras": [
    {"id": "cam01", "name": "USB-0", "source": 0},
    {"id": "cam02", "name": "Lab-A", "source": "rtsp://user:pass@192.168.1.20:554/stream1"}
  ]
}
```

配置文件任意字段缺失都会回落到 `DEFAULT_CONFIG`，坏 JSON 也不会导致启动失败。

## 输出

- 告警截图：`results/alarms/`（原图 + 标注图，支持中文路径）
- 事件日志：`results/events.csv`（字段顺序稳定）
- 应用日志：`results/app.log`（自动滚动）
- 告警导出：通过告警中心「导出」按钮生成 `results/alarms_YYYYMMDD_HHMMSS.csv`

## 快捷操作

- `F11` 全屏切换
- 双击摄像头画面 → 放大查看
- 拖拽摄像头位 → 互换位置并保存到 `config.json`
- 右侧「切换浅色 / 切换深色」→ 主题持久化
- 告警中心「导出」→ 按当前过滤条件导出 CSV

## 项目结构

```
fire_detection_system.py   主窗口 + 事件协调
capture_worker.py          QThread 采集/推理（锁保护 conf_threshold）
alarm_logic.py             告警去抖状态机
alarm_saver.py             中文路径安全的告警截图
alarm_exporter.py          告警 CSV 导出
event_logger.py            CSV 事件落库
notifier.py                DingTalk/企微 Webhook 通知
system_monitor.py          CPU/内存/GPU 采集
logging_setup.py           全局日志系统
camera_manager.py          摄像头配置对话框
camera_config_utils.py     配置归一化/持久化
config_loader.py           配置加载（含 DEFAULT_CONFIG + deep merge）
ui_components.py           CameraTile / 网格 / 滚动区
ui_theme.py                主题定义 + QSS 生成
ui_toast.py                Toast 通知组件
ui_utils.py                通用 UI 辅助
alert_flash.py             告警闪烁状态
alert_beep.py              告警蜂鸣状态
tests/                     单元测试（45 项）
```

## 测试

```bash
python -m pytest tests/ -v
```

45/45 项单测覆盖：告警去抖、worker perf 参数与锁、配置 fallback、CSV 字段稳定性、主题生成、通知器、系统监控、导出等。

## 注意事项

- macOS 纯 CPU 推理较慢；生产部署建议 Windows + NVIDIA GPU
- `results/` 目录不入库（含日志、截图、导出、事件 CSV）
- Webhook 失败仅记日志，不影响主流程
- 关闭窗口时 QThread 超时自动 terminate，避免 RTSP 卡顿挂死

## License

For academic use.
