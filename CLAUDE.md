# CLAUDE.md

本文件用于记录 Claude Code 在本项目中的工作上下文与每次变更历史，便于跨会话延续开发。

---

## 项目概览

**项目名称：** YOLOv8 校园火警多路监控系统（VisionScope）
**主要语言：** Python 3
**UI 框架：** PyQt6
**核心模型：** YOLOv8（`best.pt`，火焰/烟雾检测）
**入口文件：** `main.py`
**运行方式：** `python main.py`（详见 `运行说明.md`）

## 架构速览

```
main.py                         入口文件（MainWindow），协调所有模块
├── core/                       核心检测与告警逻辑
│   ├── capture_worker.py       采集+推理线程（CameraWorker, QThread）
│   ├── alarm_logic.py          告警状态机（AlarmTracker，命中/冷却）
│   ├── alarm_saver.py          告警截图保存（原图+标注图）
│   ├── alarm_clip.py           告警录像片段保存
│   ├── alarm_exporter.py       告警 CSV 导出
│   ├── alert_flash.py          告警红框闪烁状态
│   ├── alert_beep.py           告警蜂鸣状态
│   ├── event_logger.py         CSV 事件落库
│   ├── notifier.py             Webhook/邮件通知
│   ├── system_monitor.py       CPU/内存/GPU 监控
│   ├── threshold_advisor.py    智能阈值顾问
│   ├── spread_analyzer.py      火焰蔓延趋势分析
│   ├── heatmap_accumulator.py  检测热力图累积
│   ├── image_enhance.py        低光增强预处理（CLAHE）
│   └── roi_manager.py          ROI 区域管理（多边形过滤 + 持久化）
├── ui/                         界面组件
│   ├── components.py           CameraTile、网格/滚动区构造
│   ├── panels.py               右侧标签页 + 状态栏工厂函数
│   ├── theme.py                深/浅主题系统
│   ├── toast.py                Toast 通知
│   ├── utils.py                列表重排、事件过滤
│   ├── clip_player.py          告警录像回放播放器
│   ├── camera_manager.py       摄像头配置对话框
│   ├── timeline_widget.py      告警时间轴组件（24h 可视化）
│   ├── trend_chart.py          火焰蔓延趋势图表
│   ├── roi_editor.py           ROI 关注区域绘制编辑器
│   └── campus_map.py           校园地图火情态势图
├── utils/                      配置与工具
│   ├── config_loader.py        config.json 加载与默认值合并
│   ├── camera_config.py        source 归一化、配置持久化
│   └── logging_setup.py        全局日志系统
├── config.json                 运行配置
├── best.pt                     YOLOv8 权重
├── results/                    告警截图 + 事件 CSV + 录像输出
└── tests/                      单元测试（60 个）
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
python main.py

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
| 2026-04-19 | [P0] alarm_events 内存上限 | `MAX_ALARM_EVENTS=10000` FIFO 淘汰，避免 24h+ 内存膨胀 |
| 2026-04-19 | [P0] 0 摄像头提示 | 未配置时弹窗引导至摄像头管理，禁用启动按钮，仅保留 1 个占位 cam |
| 2026-04-19 | [P0] 输出目录写权限检测 | `output_dir` 不可写时弹窗提示并退出 |
| 2026-04-19 | [P0] 截图时间戳改用 localtime | `alarm_saver.build_alarm_paths` gmtime→localtime，测试同步更新 |
| 2026-04-19 | [P0] 状态栏时间实时更新 | `refresh_system_stats` 中同步刷新 `lbl_time`，每 2s 更新 |
| 2026-04-19 | [F] 告警消音 ESC + 按钮 | ESC 键 / 「✕ 消音」按钮一键停止蜂鸣 + 闪烁 |
| 2026-04-19 | [F] 视频 EOF 处理 | 本地文件播完 break 而非重连；tile 显示「播放结束」 |
| 2026-04-19 | [F] requirements.txt | 新增依赖清单，`pip install -r requirements.txt`；49/49 绿 |
| 2026-04-19 | [U] 右侧 QTabWidget 重构 | 6 个 GroupBox → 3 个标签页（控制台/告警中心/系统状态），告警表高度不再固定 |
| 2026-04-19 | [F] 告警统计面板 | 告警中心 tab 底部显示「今日总计 / 最频繁摄像头」 |
| 2026-04-19 | [UX] 自动跳转 + 滚动 | 新告警自动切到告警中心 tab + scrollToBottom |
| 2026-04-19 | [F] SMTP 邮件通知 | `notifier.py` 扩展 `_send_email`（SMTP+TLS），异步 daemon 线程 |
| 2026-04-19 | [F] RTSP 密码环境变量 | `camera_config_utils` 支持 `${VAR}` 占位符，避免明文密码 |
| 2026-04-19 | [F] Headless 无头模式 | `--headless` 参数启动纯推理+日志+通知，无 GUI，支持 SIGINT/SIGTERM 优雅退出 |
| 2026-04-19 | 新增 4 项单测 | env_expand × 4；53/53 绿 |
| 2026-04-19 | [UX] 快捷键 Ctrl+S/Ctrl+E/Space | 截图、导出告警、暂停/继续一键操作 |
| 2026-04-19 | [Perf] result_table 差分更新 | 仅更新变化单元格，避免每帧清空+重建 |
| 2026-04-19 | [Perf] plot() 跳过优化 | 无检测结果时跳过 results.plot()，减少绘图开销 |
| 2026-04-19 | [Refactor] 主文件拆分 | 新增 `ui_panels.py`，setup_ui 中三个 Tab + 状态栏构建提取为工厂函数；主文件 1033→876 行 |
| 2026-04-20 | [F] 告警录像回放 | 新增 `alarm_clip.py`+`clip_player.py`；worker ring buffer 缓存前后各 3s 帧，告警触发自动保存 .avi；详情弹窗内嵌播放器 |
| 2026-04-20 | [F] 智能阈值顾问 | 新增 `threshold_advisor.py`；按频率/置信度分布分析每摄像头，建议上调/下调/保持；控制台「智能阈值顾问」按钮 + 一键应用 |
| 2026-04-20 | hit_signal 扩展 max_conf | `CameraWorker.hit_signal` 新增第 4 参数 max_conf，alarm_events 记录置信度供顾问分析 |
| 2026-04-20 | 新增 7 项单测 | threshold_advisor × 4、alarm_clip × 3；60/60 绿 |
| 2026-04-20 | [Refactor] 项目目录重构 | 22 个 .py 文件按功能分入 `core/`、`ui/`、`utils/` 三个包；入口改名为 `main.py`；所有 import 路径同步更新；60/60 绿 |
| 2026-04-20 | [F] 火焰蔓延趋势分析 | 新增 `core/spread_analyzer.py` + `ui/trend_chart.py`；追踪 bbox 面积变化，stable/growing/spreading 三级判定；系统状态 tab 实时曲线图；spreading 自动升级告警 |
| 2026-04-20 | [F] 告警热力图 | 新增 `core/heatmap_accumulator.py`；持续累积检测区域生成密度图，开启后半透明叠加到实时画面；控制台「开启热力图」按钮切换 |
| 2026-04-20 | 新增 10 项单测 | spread_analyzer × 5、heatmap × 5；70/70 绿 |
| 2026-04-21 | [F] 历史时间轴回放 | 新增 `ui/timeline_widget.py`（24h 可视化时间条）；告警中心内嵌时间轴，点击标记打开告警详情；`refresh_alarm_table` 自动同步时间轴 |
| 2026-04-21 | [F] 低光增强预处理 | 新增 `core/image_enhance.py`（CLAHE 自适应直方图均衡）；worker 支持 `low_light_enhance` 参数，暗光场景自动增强后再推理 |
| 2026-04-21 | 配置扩展 + 新增 10 项单测 | `enhance` 配置节加入 DEFAULT_CONFIG；image_enhance × 5、timeline × 5；85/85 绿 |
| 2026-04-23 | [F] ROI 关注区域 | 新增 `core/roi_manager.py` + `ui/roi_editor.py`；摄像头画面上鼠标绘制多边形关注区域，仅区域内检测触发告警；ROI 配置持久化到 `roi_config.json` |
| 2026-04-23 | [F] 校园地图火情态势图 | 新增 `ui/campus_map.py`；支持加载校园平面图、拖拽放置摄像头图标、告警脉冲光环动画、点击查看画面；布局持久化到 `map_layout.json` |
| 2026-04-23 | 新增 18 项单测 | roi_manager × 9、campus_map × 9；103/103 绿 |

<!-- 后续每次变更请在此追加一行：日期 / 变更内容 / 备注 -->
