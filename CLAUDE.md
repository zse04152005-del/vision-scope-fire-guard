# CLAUDE.md

本文件用于记录 Claude Code 在本项目中的工作上下文与每次变更历史，便于跨会话延续开发。

---

## 项目概览

**项目名称：** YOLOv8 校园火警多路监控系统（VisionScope）
**主要语言：** Python 3
**UI 框架：** PyQt6
**核心模型：** YOLOv8（`best.pt`，火焰/烟雾检测）
**入口文件：** `fire_detection_system.py`
**运行方式：** `python fire_detection_system.py`（详见 `运行说明.md`）

## 架构速览

```
fire_detection_system.py        主窗口（MainWindow），协调所有模块
├── camera_manager.py           摄像头配置对话框（CameraManager）
├── capture_worker.py           采集+推理线程（CameraWorker, QThread）
├── alarm_logic.py              告警状态机（AlarmTracker，命中/冷却）
├── event_logger.py             CSV 事件落库
├── alarm_saver.py              告警截图保存（原图+标注图）
├── alert_flash.py              告警红框闪烁状态
├── alert_beep.py               告警蜂鸣状态
├── ui_components.py            CameraTile、网格/滚动区构造
├── ui_utils.py                 列表重排、事件过滤等纯函数
├── camera_config_utils.py      source 归一化、配置持久化
├── config_loader.py            config.json 加载
├── config.json                 运行配置（模型路径、告警阈值、摄像头列表）
├── best.pt                     YOLOv8 权重
├── results/                    告警截图 + 事件 CSV 输出目录
└── tests/                      单元测试（18 个）
```

**数据流：** 摄像头源 → `CameraWorker`（采集+推理，model_lock 保护）→ `AlarmTracker`（去抖/冷却）→ `save_alarm_images` + `write_event` + 主窗口 UI 更新（信号槽）。

## 关键约定

- **模型推理串行化：** 全局 `model_lock` 保证 YOLO 共享实例线程安全。
- **告警去抖：** 连续 `hit_threshold` 帧命中 + `cooldown_seconds` 冷却（见 `config.json`）。
- **配置加载：** 通过 `config_loader.load_config()`，失败时 fallback 到空字典（见已知问题）。
- **中文路径：** Windows 下 `cv2.imwrite` 可能失败，需用 `cv2.imencode` + 二进制写入。

## 常用命令

```bash
# 运行主程序
python fire_detection_system.py

# 跑测试
python -m pytest tests/ -v

# 安装依赖（若缺失）
pip install ultralytics opencv-python PyQt6 numpy
```

## 已知问题与改进计划

详见 `OPTIMIZATION_PLAN.md`（包含 P0~P3 优先级漏洞修复、功能完善、UI 美化方案及执行步骤）。

## 变更日志

| 日期 | 变更内容 | 备注 |
|------|---------|------|
| 2026-04-14 | 初始化 `CLAUDE.md` 与 `OPTIMIZATION_PLAN.md` | 完成全项目审计，输出优化方案待用户确认 |
| 2026-04-14 | [P0-1] 模型加载异常处理 | `fire_detection_system.py` YOLO 加载失败弹窗提示并退出，不再直接崩溃 |
| 2026-04-14 | [P0-2] 线程清理超时 + closeEvent 时钟停止 | `capture_worker.py` `stop()` 超时 3s 后 terminate；主窗关闭前先停 QTimer |
| 2026-04-14 | [P1-1] conf_threshold 加锁 | `CameraWorker` 用 `_conf_lock` + property 消除数据竞争；worker 内单次读取复用 |
| 2026-04-14 | [P1-2] 告警去抖边界修复 | `AlarmTracker` 仅首次越过阈值触发；空帧校验；新增两项单测，28/28 绿 |
| 2026-04-14 | [P2-1] 中文路径图像写入 | `alarm_saver.py` 改用 `cv2.imencode` + 二进制写，兼容中文路径 |
| 2026-04-14 | [P2-2/P3-2] 全局日志系统 | 新增 `logging_setup.py`（RotatingFileHandler→`results/app.log`）；主程序所有 `print` 改为 `logger` |
| 2026-04-14 | [P3-1] 事件 CSV 字段顺序稳定化 | `event_logger.FIELDNAMES` 显式定义，多次写入字段顺序一致 |
| 2026-04-14 | [P3-3] 配置 schema fallback | `config_loader.DEFAULT_CONFIG` + `_deep_merge`，缺字段/坏 JSON 自动回落默认值；新增 3 项单测，32/32 绿 |
| 2026-04-14 | [F1] Webhook 通知 | 新增 `notifier.py`（DingTalk/企微，fire-and-forget 线程 + 5s 超时）；`notify_event` 接入 |
| 2026-04-14 | [F2] RTSP 心跳重连 | `CameraWorker` 新增 `heartbeat_timeout`（默认 5s），超时主动释放并重连 |
| 2026-04-14 | [F3] 性能降帧/降分辨率 | `config.perf.max_fps` 限制推理频率；`infer_size` 按长边 resize；通过 worker 构造参数注入 |
| 2026-04-14 | [F5] CPU/内存/GPU 监控 | 新增 `system_monitor.py`（psutil + 可选 pynvml），主窗 2s `QTimer` 刷新状态栏 |
| 2026-04-14 | 新增 5 项单测 | notifier × 3、system_monitor × 2；37/37 绿 |
| 2026-04-14 | [U1] 深/浅主题系统 | 新增 `ui_theme.py`（Theme dataclass + `build_qss`），默认深色，按钮可一键切换并写回 `config.json` |
| 2026-04-14 | [U2] 按钮 Unicode 符号 | 启动/停止/暂停/导入/管理按钮加 ▶■‖⚙▤▦◉ 符号（无 emoji） |
| 2026-04-14 | [U3] 摄像头状态脉搏动画 | `CameraTile` 新增 `status_dot` + `_pulse_timer`，ONLINE 时 ●/○ 交替呼吸 |
| 2026-04-14 | [U4] Toast 通知系统 | 新增 `ui_toast.py`（`Toast` + `ToastManager`），告警右下角滑入 4s 自动消失 |
| 2026-04-14 | [U5] 响应式网格 | `resizeEvent` 无 `grid_cols` 配置时按窗口宽自动调整列数 |
| 2026-04-14 | headless 烟测通过 | `QT_QPA_PLATFORM=offscreen` 下 `MainWindow()` 成功实例化，主题深色、grid_cols=3 |
| 2026-04-14 | [F4] 告警 CSV 导出 | 新增 `alarm_exporter.py` + 告警中心「导出」按钮，UTF-8 BOM 兼容 Excel |
| 2026-04-14 | [F6] 测试补齐 | 新增 `test_alarm_exporter`、`test_ui_theme`、`test_capture_worker_perf`；45/45 绿 |
| 2026-04-14 | [U6] 告警中心渲染上限 | `ALARM_TABLE_MAX_ROWS=500` 仅渲染最新 N 条，完整数据供导出与过滤用 |
| 2026-04-14 | [U7] 主题常量化收尾 | 主窗 `on_frame`/`on_status`/`highlight_camera`/`lbl_conf_large` 全部改用 `self.theme.*` |
| 2026-04-14 | 修复 Toast 清理崩溃 | `ToastManager._remove/_relayout` 捕获父窗口销毁时的 `RuntimeError` |

<!-- 后续每次变更请在此追加一行：日期 / 变更内容 / 备注 -->
