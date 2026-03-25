# 批量文件上传下载 Python SDK 设计文档

## 一、需求背景

做一个 Python SDK，封装批量文件的上传和下载功能。底层依赖一个已有的客户端 Python 包，该包每次只能上传或下载单个文件。SDK 需要在此基础上支持批量操作。

---

## 二、需求详述

### 2.1 批量上传

**输入：**
1. `local_dir`：本地文件夹路径
2. `remote_uri`：特殊格式的长字符串（如 `xxx://a/b/c` 三段式），可通过转换函数解析为远端上传目录地址

**处理逻辑：**
- 扫描本地文件夹，**非递归**，只取第一层文件，**跳过所有子文件夹**
- 将所有文件平铺上传到 `remote_uri` 对应的远端目录下（不保留本地目录结构）
- 使用 **5个线程** 并发上传
- 单文件上传失败时：**指数退避重试3次**（间隔 2s → 5s → 8s）
- 3次重试后仍失败：记录该文件失败信息，**跳过，不中断整体上传**

**输出：** `BatchResult` — 成功数、失败数、失败文件列表（含错误信息）

---

### 2.2 批量下载

**输入：**
1. `remote_uri`：特殊格式的长字符串，指向远端目录
2. `local_dir`：本地保存目录

**处理逻辑：**
- 通过 `remote_uri` 解析出远端目录路径，调用远端服务列出该目录下所有条目
- 远端列举支持**分页**，需循环翻页直到获取全部内容
- **跳过文件夹条目**，只收集文件（非递归）
- `local_dir` 不存在时自动创建
- 所有文件平铺下载到 `local_dir`（不保留远端目录结构）
- 使用 **5个线程** 并发下载
- 单文件下载失败时：**指数退避重试3次**（间隔 2s → 5s → 8s）
- 3次重试后仍失败：记录该文件失败信息，**跳过，不中断整体下载**

**输出：** `BatchResult` — 成功数、失败数、失败文件列表（含错误信息）

---

### 2.3 客户端管理机制

`remote_uri` 长字符串需要经过以下步骤才能使用：

1. **URI 解析**：将字符串解析为 `client_key`（标识用哪个客户端）和 `remote_path`（远端目标目录）
2. **缓存查询**：在本地缓存（dict）中查找 `client_key` 对应的客户端实例，命中则直接使用
3. **配置拉取**（缓存未命中时）：调用 REST 接口，获取该客户端的连接配置（IP、密码等）
4. **客户端初始化**：根据配置创建并连接客户端实例，写入本地缓存
5. 预期用户场景下，缓存中客户端条目一般 **≤ 3个**

---

## 三、接口定义

```python
upload_files(local_dir: str, remote_uri: str) -> BatchResult
download_files(remote_uri: str, local_dir: str) -> BatchResult
```

**BatchResult 结构：**
```python
{
  "success_count": int,
  "fail_count": int,
  "failed_files": [
    {"file": "filename", "error": "error message or None"}
  ]
}
```

---

## 四、核心逻辑拆解（10个子任务）

### 公共基础层（上传/下载共用）

**T1 — URI 解析**
- 输入：`remote_uri` 长字符串
- 逻辑：解析出 `client_key`（决定用哪个客户端）+ `remote_path`（远端目标目录）
- 输出：`(client_key: str, remote_path: str)`

**T2 — 客户端缓存查询**
- 输入：`client_key`
- 逻辑：查本地缓存 dict，命中则直接返回
- 输出：`Client` 或 `None`

**T3 — 远端配置拉取**
- 输入：`client_key`
- 逻辑：调用 REST 接口获取连接配置（IP、密码等）
- 输出：`ClientConfig`（dict）

**T4 — 客户端初始化 & 缓存写入**
- 输入：`ClientConfig`
- 逻辑：创建并连接客户端，写入本地缓存（预期 ≤ 3条）
- 输出：`Client`

> T1→T2→(T3→T4 按需) 封装为 `get_client(remote_uri) -> (Client, remote_path)`，上传下载共用。

**T5 — 带重试的单任务执行器**
- 输入：可调用的单文件操作函数
- 逻辑：失败时指数退避重试，最多3次（间隔 2s → 5s → 8s），3次后仍失败则记录并跳过，不中断整体任务
- 输出：`TaskResult(file, success: bool, error: str | None)`

### 上传侧

**T6 — 本地文件扫描**
- 输入：`local_dir`
- 逻辑：列出目录第一层，**跳过子文件夹**，只收集文件（非递归）
- 输出：`List[Path]`

**T7 — 单文件上传**
- 输入：本地文件路径 + `Client` + `remote_path`
- 逻辑：调用底层包上传接口，将文件上传至 `remote_path/filename`，由 T5 包裹重试
- 输出：`TaskResult`

**T8 — 并发上传调度**
- 输入：`List[Path]` + `Client` + `remote_path`
- 逻辑：`ThreadPoolExecutor(max_workers=5)` 并发执行 T7，汇总所有结果
- 输出：`BatchResult`

### 下载侧

**T9 — 远端文件列举（含翻页）**
- 输入：`Client` + `remote_path`
- 逻辑：循环调用列目录接口，有下一页则继续请求，**跳过文件夹条目**，只收集文件（非递归）
- 输出：`List[RemoteFile]`

**T10 — 单文件下载**
- 输入：`RemoteFile` + `local_dir` + `Client`
- 逻辑：`local_dir` 不存在则创建；调用底层包下载接口，保存至 `local_dir/filename`；由 T5 包裹重试
- 输出：`TaskResult`

**T11 — 并发下载调度**
- 输入：`List[RemoteFile]` + `local_dir` + `Client`
- 逻辑：`ThreadPoolExecutor(max_workers=5)` 并发执行 T10，汇总结果
- 输出：`BatchResult`

---

## 五、调用链总览

```
upload_files(local_dir, remote_uri)
  └─ get_client(remote_uri)     → T1 → T2 → [T3 → T4] → (Client, remote_path)
  └─ T6: scan_local(local_dir)  → [file1, file2, ...]
  └─ T8: concurrent_upload(...)
        └─ T5(T7) × 5 threads   → 带重试的单文件上传

download_files(remote_uri, local_dir)
  └─ get_client(remote_uri)     → T1 → T2 → [T3 → T4] → (Client, remote_path)
  └─ T9: list_remote(...)       → [remoteFile1, ...]  ← 含翻页
  └─ T11: concurrent_download(...)
         └─ T5(T10) × 5 threads → 带重试的单文件下载
```

---

## 六、架构设计

### 6.1 文件结构

```
sdk/
├── main.py       # 对外暴露的两个公共接口
├── client.py     # URI解析 + 客户端缓存管理
├── remote.py     # 远端文件列举（含翻页）
├── transfer.py   # 单文件上传/下载 + 重试 + 并发调度
└── tests/
    ├── test_client.py
    └── test_transfer.py
```

### 6.2 各文件函数设计

#### `client.py`

| 函数 | 输入 | 输出 |
|---|---|---|
| `parse_uri(remote_uri)` | `str` | `(client_key: str, remote_path: str)` |
| `get_cached_client(client_key)` | `str` | `Client \| None` |
| `fetch_client_config(client_key)` | `str` | `ClientConfig (dict)` |
| `init_and_cache_client(client_key, config)` | `str, ClientConfig` | `Client` |
| `get_client(remote_uri)` | `str` | `(Client, remote_path: str)` |

> `get_client` 是门面函数，内部串联上面4个

#### `remote.py`

| 函数 | 输入 | 输出 |
|---|---|---|
| `list_remote_files(client, remote_path)` | `Client, str` | `List[RemoteFile]` |

> 内部处理翻页，过滤文件夹，只返回文件

#### `transfer.py`

| 函数 | 输入 | 输出 |
|---|---|---|
| `scan_local_files(local_dir)` | `str` | `List[Path]` |
| `with_retry(fn, *args)` | `callable, args` | `TaskResult` |
| `upload_one(client, remote_path, file_path)` | `Client, str, Path` | `TaskResult` |
| `download_one(client, remote_file, local_dir)` | `Client, RemoteFile, str` | `TaskResult` |
| `run_concurrent(task_fn, items, **kwargs)` | `callable, List, kwargs` | `BatchResult` |

> `with_retry` 封装重试逻辑（2s/5s/8s，最多3次）
> `run_concurrent` 被上传和下载共用，`ThreadPoolExecutor(max_workers=5)`

#### `main.py`

| 函数 | 输入 | 输出 |
|---|---|---|
| `upload_files(local_dir, remote_uri)` | `str, str` | `BatchResult` |
| `download_files(remote_uri, local_dir)` | `str, str` | `BatchResult` |

### 6.3 行数预估

| 文件 | 预估行数 |
|---|---|
| `client.py` | ~60 行 |
| `remote.py` | ~25 行 |
| `transfer.py` | ~70 行 |
| `main.py` | ~20 行 |
| **合计** | **~175 行** |

---

## 七、关键约束汇总

| 项目 | 规则 |
|---|---|
| 目录遍历 | 非递归，只取第一层文件，跳过子文件夹 |
| 路径映射 | 本地/远端结构均忽略，全部平铺到目标目录 |
| 并发数 | 固定 5 线程 |
| 重试次数 | 最多 3 次 |
| 重试间隔 | 指数退避：2s → 5s → 8s |
| 失败处理 | 跳过，不中断整体，计入 `failed_files` |
| 本地目录 | 下载前自动创建（如不存在） |

---

## 八、测试设计

### `test_client.py` — 测客户端管理逻辑

| 函数 | 测什么 |
|---|---|
| `test_parse_uri` | 长字符串正确解析出 client_key 和 remote_path |
| `test_cache_hit` | 已缓存的 client_key 直接返回缓存，不调 REST |
| `test_cache_miss_calls_rest` | 未缓存时触发 fetch_client_config |
| `test_client_saved_after_init` | 初始化后客户端写入缓存 |

### `test_transfer.py` — 测文件扫描 + 重试 + 并发

| 函数 | 测什么 |
|---|---|
| `test_scan_skips_folders` | 文件夹被过滤，只返回文件 |
| `test_retry_success_first_try` | 第一次成功，不重试 |
| `test_retry_succeed_on_third` | 前两次失败，第三次成功，返回成功结果 |
| `test_retry_all_fail` | 三次全败，返回 TaskResult 失败 + error 信息 |
| `test_concurrent_returns_batch_result` | 5个任务并发跑完，BatchResult 计数正确 |
| `test_failed_task_does_not_stop_others` | 某个任务失败，其他任务继续执行完毕 |
