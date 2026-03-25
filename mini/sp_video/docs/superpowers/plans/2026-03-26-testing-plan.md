# sp_video 测试计划

**日期**: 2026-03-26
**负责人**: Claude (规划) + Codex (实现)
**目标**: 为 sp_video 项目建立基础测试框架，覆盖核心功能

---

## 测试范围

### 优先级 P0 (核心功能)
1. **时间工具函数** (`make_time/time_utils.py`)
   - 时间格式解析和转换
   - 边界条件处理

2. **区间合并逻辑** (`make_time/interval.py`)
   - 相邻区间合并
   - 重叠区间处理

3. **对外接口**
   - `get_keep_intervals()` - 字幕匹配接口
   - `cut_video_main()` - 视频剪辑接口

### 优先级 P1 (重要功能)
4. **脚本解析** (`make_time/mode2.py`)
   - 带时间段落解析
   - 无时间段落解析

5. **skill.py 命令接口**
   - list / start / phase2 / generate 子命令
   - JSON 输出格式验证

---

## 测试策略

### 单元测试
- 使用 pytest 框架
- Mock AI 调用（避免真实 API 消耗）
- Mock ffmpeg 调用（避免实际视频处理）
- 测试覆盖率目标：核心模块 > 80%

### 集成测试
- 使用测试数据（小样本 SRT + 视频）
- 验证模块间数据流转
- 验证 JSON 格式一致性

### 测试数据
- `tests/fixtures/` 目录存放测试数据
  - `sample.srt` - 示例字幕文件
  - `sample_script.txt` - 示例脚本
  - `sample.mp4` - 小视频文件（可选）

---

## 文件结构映射

```
tests/
├── __init__.py
├── conftest.py                    # pytest 配置和 fixtures
├── fixtures/                      # 测试数据
│   ├── sample.srt
│   └── sample_script.txt
├── unit/                          # 单元测试
│   ├── test_time_utils.py        # 时间工具测试
│   ├── test_interval.py          # 区间合并测试
│   └── test_prompts.py           # prompt 构造测试
├── integration/                   # 集成测试
│   ├── test_step2.py             # get_keep_intervals 集成测试
│   └── test_skill.py             # skill.py 命令测试
└── mocks/                         # Mock 工具
    ├── mock_ai.py                # AI 调用 mock
    └── mock_ffmpeg.py            # ffmpeg mock
```

---

## 实施任务（委派给 Codex）

### Task 1: 搭建测试框架 (5 分钟)
- 创建 `tests/` 目录结构
- 创建 `conftest.py` 配置文件
- 添加 pytest 依赖到项目
- 创建基础 fixtures

### Task 2: 时间工具单元测试 (5 分钟)
- 文件：`tests/unit/test_time_utils.py`
- 测试 `make_time/time_utils.py` 中的时间解析函数
- 覆盖正常格式、边界值、异常输入

### Task 3: 区间合并单元测试 (5 分钟)
- 文件：`tests/unit/test_interval.py`
- 测试 `make_time/interval.py` 的 `merge_intervals()` 函数
- 覆盖相邻、重叠、分离区间场景

### Task 4: Mock AI 调用工具 (5 分钟)
- 文件：`tests/mocks/mock_ai.py`
- Mock `make_time/chat.py` 的 `ask_ai()` 函数
- 返回预设的 JSON 响应

### Task 5: 集成测试 - get_keep_intervals (10 分钟)
- 文件：`tests/integration/test_step2.py`
- 准备测试 SRT 和脚本数据
- 使用 Mock AI，测试完整匹配流程
- 验证返回的 keep_intervals 格式

### Task 6: skill.py 命令测试 (10 分钟)
- 文件：`tests/integration/test_skill.py`
- 测试 list / start / phase2 子命令
- 验证 JSON 输出格式
- Mock OSS 和文件操作

---

## 验收标准

- [ ] 所有测试用例通过 `pytest tests/`
- [ ] 核心模块测试覆盖率 > 80%
- [ ] 测试运行时间 < 30 秒（使用 Mock）
- [ ] CI/CD 可集成（可选）

---

## 注意事项

1. **不测试 LLM 输出质量** - 只测试格式和流程
2. **不测试 ffmpeg 实际剪辑** - Mock 文件操作即可
3. **不测试 OSS 上传** - Mock 网络请求
4. **保持测试简单** - 优先覆盖核心逻辑，避免过度测试

