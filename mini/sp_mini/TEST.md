# skill.py 测试说明

## 测试环境要求

- `ossutil` 已配置 OSS 访问凭证
- `ffmpeg` 已安装
- `data/config/config.yaml` 中填入有效 `DEEPSEEK_API_KEY`
- Python 3.8+

---

## 完整流程测试（正向）

按顺序执行，验证端到端流程：

```bash
# 1. 查询视频列表
python skill.py list

# 2. 开始处理（下载 + Phase1）
python skill.py start --video_id C1873

# 3. 生成脚本 + 时间轴匹配（Phase2+3）
python skill.py phase2 --video_id C1873

# 4. 生成视频并上传（Phase4）
python skill.py generate --video_id C1873
```

**预期**：每步返回 JSON，最终 `generate` 返回公网 URL。

---

## 单项测试用例

### T01 — 跳过 start 直接调 phase2

```bash
python skill.py phase2 --video_id C1874
```

**预期**：
```json
{"status": "error", "message": "找不到 C1874 的处理状态，请先运行 start"}
```

---

### T02 — 跳过 phase2 直接调 generate

```bash
python skill.py generate --video_id C1874
```

**预期**：
```json
{"status": "error", "message": "找不到 C1874 的处理状态，请先运行 start"}
```

---

### T03 — 无效 video_id

```bash
python skill.py start --video_id NOTEXIST
```

**预期**：
```json
{"status": "error", "message": "视频 NOTEXIST 不在缓存中，请先运行 list"}
```

---

### T04 — 重复 start（缓存命中，跳过 Phase1）

```bash
# 前提：已执行过 start --video_id C1873
python skill.py start --video_id C1873
```

**预期**：stderr 打印 `[跳过] 已有缓存: .../step1.txt`，正常返回提示词。

---

### T05 — 重复 phase2（有缓存时询问用户）

```bash
# 前提：已执行过 phase2 --video_id C1873
python skill.py phase2 --video_id C1873
```

**预期**：
```json
{
  "status": "need_confirm_regen",
  "message": "已有上次生成的脚本缓存，是否直接使用？",
  "cached_script_preview": "...",
  "hint": "使用缓存: phase2 --video_id ... --use_cache  |  重新生成: phase2 --video_id ... --force"
}
```

用户说"用缓存"：
```bash
python skill.py phase2 --video_id C1873 --use_cache
```

用户说"重新生成"：
```bash
python skill.py phase2 --video_id C1873 --force
```

两者均应最终返回 `need_confirm_intervals`。

---

### T06 — 自定义 prompt_file 失败后缓存不受污染

```bash
# 前提：已有干净的 step2.txt 缓存
# 记录当前 step2.txt 内容
cat data/skill_state/C1873/step2.txt | head -3

# 用格式错误的提示词触发 Phase3 失败
echo "这是一段无法匹配时间轴的提示词" > /tmp/bad_prompt.txt
python skill.py phase2 --video_id C1873 --prompt_file /tmp/bad_prompt.txt

# 验证 step2.txt 已恢复为原始内容
cat data/skill_state/C1873/step2.txt | head -3
```

**预期**：
- phase2 返回 `{"status": "error", "stage": 3, "message": "未匹配到任何时间片段..."}`
- step2.txt 内容与执行前一致（原缓存已恢复）

---

### T07 — prompt_file 文件不存在

```bash
python skill.py phase2 --video_id C1873 --prompt_file /tmp/no_such_file.txt
```

**预期**：
```json
{"status": "error", "message": "提示词文件不存在: /tmp/no_such_file.txt"}
```

---

## 测试结果记录（2026-03-22）

| 编号 | 场景 | 结果 | 备注 |
|------|------|------|------|
| T01 | 跳过 start 直接 phase2 | ✅ | 正确报错 |
| T02 | 跳过 phase2 直接 generate | ✅ | 正确报错 |
| T03 | 无效 video_id | ✅ | 正确报错 |
| T04 | 重复 start（缓存命中） | ✅ | Phase1 跳过，直接返回提示词 |
| T05 | 重复 phase2 + 用户决策 | ✅ | 返回 need_confirm_regen，--use_cache / --force 均正常 |
| T06 | 自定义 prompt 失败后缓存恢复 | ✅ | step2.txt 恢复为原内容 |
| T07 | prompt_file 不存在 | ✅ | 正确报错 |
