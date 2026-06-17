# KWS 测试集创建与管理平台设计

日期：2026-06-17  
状态：已确认设计，待用户复核  
范围：第一阶段聚焦测试集构建与导出闭环

## 1. 背景与目标

用户正在训练一个关键词唤醒（KWS）模型，需要构造和管理测试数据集的能力。测试集需要覆盖：

1. 关键词正样本、相近音负样本、非完整唤醒语音。
2. 不同音色，包括真人、合成、男女老少等。
3. 不同音量、音调、语速、噪声场景。
4. 损伤场景，包括经过终端、网络侧降噪后的音频。

系统长期需要具备三类能力：

- A：测试集构建与导出闭环。
- C：数据生成与增强闭环。
- D：评测与分析闭环。

第一阶段先解决 A，不考虑未标注音频的多人标注/审核流程。

## 2. 第一阶段范围

第一阶段目标是建立一个本地单人使用的轻量平台：

```text
人工导入原声 wav
  -> 补充元数据与标签
  -> 进入音频资产库
  -> 按规则构建测试集
  -> 手工锁定 / 排除
  -> 生成不可变测试集版本快照
  -> 导出 sherpa_eval JSONL manifest
  -> 由现有离线评测脚本消费
```

明确不做：

- 未标注音频的多人标注/审核系统。
- 平台内直接跑模型评测。
- 完整 TTS/变速/变调/加噪/降噪流水线。
- 多用户权限、云存储、团队协作。
- PostgreSQL、对象存储、任务队列等重型基础设施。

但数据模型和模块边界要为后续 C/D 留出扩展空间。

## 3. 部署和跨平台约束

第一版是本机单人轻量平台，但工程必须能在 macOS、Windows、Linux 上跑起来。

### 3.1 跨平台原则

- 所有路径在代码中使用 `pathlib.Path`，避免硬编码 `/` 或 `\\`。
- 配置文件中允许用户设置本机路径，例如数据目录、评测项目目录。
- 默认数据目录使用项目内相对路径，例如 `data/`，不要依赖 macOS 专有路径。
- macOS 当前评测项目路径只作为用户本机配置示例，不写死到业务逻辑：
  - `/Users/e4/Library/Mobile Documents/com~apple~CloudDocs/自定义唤醒`
- 导出 manifest 中的 `audio` 字段优先支持绝对路径；后续可增加相对路径模式。
- 文件复制、hash、扫描、导出都应使用 Python 标准库跨平台能力。
- 避免 shell 专属脚本作为核心启动方式；可以提供 Python CLI。
- 如需启动前后端，优先提供跨平台命令：
  - `python -m kws_testset serve`
  - 或 `uv run kws-testset serve`
- 前端构建使用 Node/npm 时，需要在文档中说明 Windows/Linux/macOS 一致的启动命令。

### 3.2 平台配置

配置文件建议放在：

```text
configs/app.yaml
```

示例：

```yaml
app:
  data_dir: data
  target_keyword: 你好小智

export:
  default_audio_mode: reference_original_path

# 这是本机可选配置，不是工程默认硬编码。
eval_project:
  root: /Users/e4/Library/Mobile Documents/com~apple~CloudDocs/自定义唤醒
  manifest_dir: sherpa_eval/data
```

Windows 用户可配置：

```yaml
eval_project:
  root: D:\\kws_experiments
  manifest_dir: sherpa_eval\\data
```

实际代码读取后应统一转换为 `Path`。

## 4. 总体架构

建议采用：

```text
Frontend: React + Vite + TypeScript
Backend:  Python FastAPI
Database: SQLite
ORM:      SQLAlchemy 或 SQLModel
CLI:      Typer，可选
Storage:  本地文件目录
```

推荐目录结构：

```text
kws_testset/
├── app/
│   ├── backend/
│   └── frontend/
├── configs/
│   └── app.yaml
├── data/
│   ├── library/
│   │   ├── sources/
│   │   └── variants/
│   ├── exports/
│   └── app.db
├── docs/
└── tests/
```

核心模块：

1. Audio Library：音频资产库。
2. Import Wizard：人工导入向导。
3. Taxonomy：标签与枚举体系。
4. Dataset Builder：测试集构建器。
5. Exporter：导出器。
6. Quality Gates：质量门禁。

关键原则：

- 音频文件是资产；测试集只是资产的一个版本化选择结果。
- 测试集版本不可变。
- 原声和派生音频可追溯。
- 平台内部可保存丰富 metadata，但导出给离线评测的 manifest 要稳定简单。

## 5. 数据模型

第一版核心对象：

- `audio_source`：原始母版音频。
- `audio_variant`：实际可参与抽样和导出的音频版本。
- `import_batch`：一次批量导入。
- `dataset_spec`：测试集构建规则。
- `manual_override`：手工 include / exclude。
- `dataset_version`：一次构建出的不可变版本。
- `dataset_item`：测试集版本中的样本快照。

### 5.1 Source 与 Variant 分离

即使第一版只有原声，也从第一天区分 source 和 variant。

导入原声 wav 时：

```text
wav 文件
  -> audio_source
  -> audio_variant(original)
```

未来增强时：

```text
audio_source src_001
  ├── audio_variant var_001 original
  ├── audio_variant var_002 speed_change
  ├── audio_variant var_003 noise_mix
  └── audio_variant var_004 device_denoise
```

测试集引用的是 `audio_variant`，不是直接引用 `audio_source`。

### 5.2 audio_source

关键字段：

```text
id                      string primary key
original_filename       string
stored_path             string
sha256                  string unique
duration_sec            float
sample_rate             int
channels                int
bit_depth               int nullable
import_batch_id         string
imported_at             datetime
notes                   text nullable
```

### 5.3 audio_variant

关键字段：

```text
id                         string primary key
source_id                  string references audio_source(id)
parent_variant_id          string nullable references audio_variant(id)
variant_kind               enum
stored_path                string
sha256                     string unique
duration_sec               float
sample_rate                int
channels                   int

text                       string
normalized_text            string
sample_type                enum
quality_status             enum

voice_source               enum
speaker_id                 string nullable
gender                     enum
age_group                  enum
timbre_tags                json array

volume                     enum
pitch                      enum
speed                      enum
noise_scene                enum
snr_bucket                 enum nullable
impairment_type            enum
impairment_chain           json array
processing_params          json object

custom_tags                json array
notes                      text nullable

created_at                 datetime
updated_at                 datetime
```

### 5.4 sample_type

第一版固定四类：

```text
wake_positive
similar_negative
partial_wake
ordinary_negative
```

语义规则：

- `wake_positive`：完整唤醒词正样本，normalized text 必须包含固定唤醒词。
- `similar_negative`：相近音负样本，不得完整包含固定唤醒词。
- `partial_wake`：非完整唤醒，不得完整包含固定唤醒词。
- `ordinary_negative`：普通负样本，不得包含固定唤醒词。

### 5.5 覆盖维度

音色与说话人：

```text
voice_source: human | synthetic | unknown
speaker_id: optional string
gender: male | female | unknown
age_group: child | teen | adult | elderly | unknown
timbre_tags: json array
```

声学条件：

```text
volume: low | normal | high | unknown
pitch: low | normal | high | unknown
speed: slow | normal | fast | unknown
noise_scene: clean | home | office | car | street | music | babble | other | unknown
snr_bucket: clean | gt20 | 10_20 | 0_10 | lt0 | unknown
```

损伤条件：

```text
impairment_type:
  none
  device_denoise
  network_denoise
  codec
  far_field
  clipping
  other
  unknown

impairment_chain: json array
processing_params: json object
```

### 5.6 quality_status

三态：

```text
draft
ready
deprecated
```

`ready` 样本必须满足最低要求：

- 文件存在。
- 能读取 duration。
- `text` 非空。
- `sample_type` 已填。
- `voice_source` 已填。
- `gender` 已填，允许 `unknown`。
- `age_group` 已填，允许 `unknown`。
- `volume` 已填。
- `pitch` 已填。
- `speed` 已填。
- `noise_scene` 已填。
- `impairment_type` 已填。
- 样本语义规则通过。

### 5.7 dataset_spec

关键字段：

```text
id                         string primary key
name                       string
description                text
target_keyword             string
target_keyword_normalized  string
sampling_seed              int
status                     enum active | archived

quotas_json                json object
filters_json               json object
balance_by_json            json array
min_duration_sec           float nullable
max_duration_sec           float nullable

created_at                 datetime
updated_at                 datetime
```

### 5.8 manual_override

关键字段：

```text
id                string primary key
dataset_spec_id   string references dataset_spec(id)
variant_id        string references audio_variant(id)
action            enum include | exclude
reason            text
created_at        datetime
```

规则：

- `exclude` 优先级高于自动抽样。
- `include` 占用对应 `sample_type` 配额。
- 每条 override 必须有 reason。
- 第一版中 include 仍必须满足 ready 和语义校验。

### 5.9 dataset_version

关键字段：

```text
id                       string primary key
dataset_spec_id          string references dataset_spec(id)
version                  int
name                     string
build_status             enum draft | built | exported | failed
sampling_seed            int
rules_snapshot_json      json object
coverage_summary_json    json object
item_count               int
total_duration_sec       float
export_path              string nullable
created_at               datetime
built_at                 datetime nullable
exported_at              datetime nullable
```

### 5.10 dataset_item

关键字段：

```text
id                     string primary key
dataset_version_id     string references dataset_version(id)
variant_id             string references audio_variant(id)
sample_type            enum
text                   string
normalized_text        string
duration_sec           float
selection_reason       enum auto | manual_include
selection_rank         int
metadata_snapshot_json json object
```

`dataset_item` 保存 metadata snapshot，而不是只引用 `audio_variant`，保证历史测试集版本不可变。

## 6. 导入流程与质量门禁

第一版导入只处理本地 wav 原声文件。流程：

```text
选择 wav 文件或目录
  -> 扫描与预检
  -> 设置批次默认 metadata
  -> 逐条修正 / 批量编辑
  -> 质量校验
  -> 入库并生成 source + original variant
```

### 6.1 扫描与预检

自动读取：

- 文件名。
- 绝对路径。
- 时长。
- 采样率。
- 声道数。
- bit depth。
- sha256。

结果分类：

- 可导入。
- 重复文件。
- 异常文件。

重复文件第一版默认跳过。

### 6.2 批次默认 metadata

导入批次可设置默认值：

```text
sample_type
voice_source
gender
age_group
volume
pitch
speed
noise_scene
impairment_type
quality_status
custom_tags
notes
```

当前不规范原声 wav 的推荐默认值：

```yaml
variant_kind: original
impairment_type: none
noise_scene: clean 或 unknown
quality_status: draft
```

### 6.3 表格编辑

Import Wizard 表格列：

- 文件名。
- 播放。
- 时长。
- text。
- sample_type。
- voice_source。
- gender。
- age_group。
- volume。
- pitch。
- speed。
- noise_scene。
- impairment_type。
- quality_status。
- notes。

支持：

- 多行批量设置字段。
- 按缺失字段过滤。
- 按校验错误过滤。
- 一键把通过校验的样本设为 `ready`。
- 一键把未通过样本保留为 `draft`。

### 6.4 质量校验

文件级必须通过：

- 文件存在。
- 文件可读。
- duration_sec > 0。
- sha256 不重复。
- sample_rate 可读取。
- channels 可读取。

警告但不阻塞：

- sample_rate 不是 16000。
- channels 不是 1。
- duration 过短或过长。

语义校验：

- 正样本必须包含完整唤醒词。
- 相近音负样本不能包含完整唤醒词。
- 非完整唤醒不能完整包含唤醒词。
- 普通负样本不能包含完整唤醒词。

## 7. 测试集构建与抽样

测试集构建采用规则抽样 + 手工锁定/排除。

### 7.1 Dataset Spec 示例

```yaml
name: wakeword_regression
description: 固定唤醒词主回归测试集
target_keyword: 你好小智
sampling_seed: 20260617

quotas:
  wake_positive: 500
  similar_negative: 300
  partial_wake: 300
  ordinary_negative: 1000

filters:
  quality_status: [ready]
  variant_kind: [original]
  impairment_type: [none]
  noise_scene: [clean, home, office, car, street, music, babble]

balance_by:
  - voice_source
  - gender
  - age_group
  - noise_scene
  - impairment_type

duration:
  min_sec: 0.3
  max_sec: 10.0
```

### 7.2 候选池

构建时先筛选：

```text
quality_status = ready
file exists
duration within range
sample_type in quotas
```

然后应用用户 filters。

如果候选不足：

- 允许构建。
- 标记 shortfall。
- 不自动用其他类型补齐。

### 7.3 Include / Exclude

Exclude：

- 不进入候选池。
- 优先级高于自动抽样和 include。
- 必须记录 reason。

Include：

- 通过 ready 与语义校验后必须进入测试集。
- 占用对应 sample_type 配额。
- 默认不允许超过 quota，除非后续增加显式开关。

### 7.4 抽样算法

第一版使用简单、可解释、可复现的分桶轮询：

1. 按 sample_type 独立抽样。
2. 取候选池。
3. 移除 exclude。
4. 加入 include。
5. 计算剩余 quota。
6. 用 balance_by 生成 bucket key。
7. 每个 bucket 内按固定 seed shuffle。
8. 在 bucket 之间轮询取样直到达到 quota 或候选耗尽。

默认均衡维度：

```yaml
balance_by:
  - voice_source
  - gender
  - age_group
  - noise_scene
  - impairment_type
```

音量、音调、语速作为可选维度。UI 应提示维度过多会导致桶稀疏。

### 7.5 覆盖率预览

构建前展示：

- 各 sample_type 的 quota、候选数、预计选中数、shortfall。
- 按 gender、age_group、voice_source、noise_scene、impairment_type 等维度的候选/选中分布。
- 缺口提示，例如某类近音负样本不足、某类降噪损伤为 0。

## 8. 测试集版本与导出

每次构建生成不可变 `dataset_version`。

保存：

- spec snapshot。
- filters snapshot。
- quotas snapshot。
- override snapshot。
- selected item list。
- 每个 item 的 metadata snapshot。
- coverage summary。
- sampling seed。
- 构建时间。

导出目录：

```text
data/exports/
└── wakeword_regression/
    └── v001/
        ├── manifest.jsonl
        ├── rich_manifest.jsonl
        ├── dataset.yaml
        ├── coverage_summary.json
        └── eval_config_snippet.yaml
```

### 8.1 manifest.jsonl

给现有 `sherpa_eval` 直接消费：

```json
{"id":"utt_wakeword_regression_v001_000001","audio":"/abs/path/to/audio.wav","text":"你好小智","duration":1.23}
```

字段：

- `id`：dataset_item id。
- `audio`：variant stored_path。
- `text`：导出文本。
- `duration`：duration_sec。

### 8.2 rich_manifest.jsonl

保留完整 metadata，供后续分析：

```json
{
  "id": "utt_wakeword_regression_v001_000001",
  "audio": "/abs/path/to/audio.wav",
  "text": "你好小智",
  "duration": 1.23,
  "sample_type": "wake_positive",
  "voice_source": "human",
  "speaker_id": "spk_001",
  "gender": "female",
  "age_group": "adult",
  "volume": "normal",
  "pitch": "normal",
  "speed": "normal",
  "noise_scene": "clean",
  "snr_bucket": "clean",
  "impairment_type": "none",
  "variant_kind": "original",
  "source_id": "src_20260617_abcd",
  "variant_id": "var_20260617_abcd",
  "selection_reason": "auto",
  "selection_rank": 1
}
```

### 8.3 dataset.yaml

记录版本元信息：

```yaml
dataset:
  name: wakeword_regression
  version: 1
  id: dsv_wakeword_regression_v001
  target_keyword: 你好小智
  built_at: "2026-06-17T10:00:00+08:00"
  exported_at: "2026-06-17T10:05:00+08:00"
  sampling_seed: 20260617

counts:
  total: 2060
  by_sample_type:
    wake_positive: 500
    similar_negative: 260
    partial_wake: 300
    ordinary_negative: 1000
  total_duration_sec: 2840.3
  negative_duration_sec: 2190.1
  negative_hours: 0.608

files:
  manifest: manifest.jsonl
  rich_manifest: rich_manifest.jsonl
  coverage_summary: coverage_summary.json
```

### 8.4 eval_config_snippet.yaml

用于复制到现有离线评测项目配置：

```yaml
eval:
  testsets:
    - name: wakeword_regression_v001
      manifest: /abs/path/to/data/exports/wakeword_regression/v001/manifest.jsonl
  negative_hours:
    wakeword_regression_v001: 0.608
```

## 9. 页面设计

第一版页面：

1. Dashboard：资产和测试集概览。
2. Import Wizard：导入 wav、批量编辑 metadata。
3. Asset Library：搜索、筛选、播放、编辑资产。
4. Dataset Specs：创建规则、配额、filters、balance_by、include/exclude。
5. Dataset Versions：查看不可变版本、覆盖统计、导出。
6. Settings：固定唤醒词、路径、导出配置、枚举扩展。

## 10. 后端模块设计

建议后端结构：

```text
app/backend/
├── main.py
├── config.py
├── db.py
├── models/
│   ├── audio.py
│   ├── dataset.py
│   └── import_batch.py
├── schemas/
│   ├── audio.py
│   ├── dataset.py
│   └── import_batch.py
├── services/
│   ├── audio_probe.py
│   ├── import_service.py
│   ├── validation_service.py
│   ├── sampling_service.py
│   ├── coverage_service.py
│   └── export_service.py
├── api/
│   ├── imports.py
│   ├── assets.py
│   ├── datasets.py
│   ├── exports.py
│   └── taxonomy.py
└── utils/
    ├── ids.py
    ├── hashing.py
    └── text_normalize.py
```

原则：

- API 层只负责请求/响应。
- 业务逻辑放在 services。
- models 是数据库结构。
- schemas 是 API 数据结构。
- 抽样、校验、导出都应可单独测试。

## 11. API 草案

Taxonomy：

```http
GET /api/taxonomy
```

Import：

```http
POST /api/imports/scan
POST /api/imports
GET  /api/imports
GET  /api/imports/{id}
```

Assets：

```http
GET    /api/assets
GET    /api/assets/{variant_id}
PATCH  /api/assets/{variant_id}
POST   /api/assets/bulk-update
POST   /api/assets/{variant_id}/validate
```

Dataset Specs：

```http
GET    /api/dataset-specs
POST   /api/dataset-specs
GET    /api/dataset-specs/{id}
PATCH  /api/dataset-specs/{id}
POST   /api/dataset-specs/{id}/preview
POST   /api/dataset-specs/{id}/build
```

Overrides：

```http
GET    /api/dataset-specs/{id}/overrides
POST   /api/dataset-specs/{id}/overrides
DELETE /api/dataset-specs/{id}/overrides/{override_id}
```

Dataset Versions：

```http
GET  /api/dataset-versions
GET  /api/dataset-versions/{id}
GET  /api/dataset-versions/{id}/items
POST /api/dataset-versions/{id}/export
```

## 12. 后续扩展

### 12.1 C：生成与增强

后续可新增 transform job，或先复用 `audio_variant` 字段：

- `parent_variant_id`
- `variant_kind`
- `impairment_chain`
- `processing_params`

典型流程：

```text
选中 source 或 variant
  -> 创建增强任务
  -> 生成新 wav 到 data/library/variants/
  -> 创建新 audio_variant
  -> 自动填 processing_params
  -> 用户校验后设为 ready
```

### 12.2 D：评测与分析

后续新增：

- `eval_run`
- `eval_result`
- `eval_item_result`

并导入现有离线评测输出：

- `metric-*.txt`
- `triggers-*.jsonl`
- `summary-*.json`

利用 `rich_manifest.jsonl` 和 `dataset_item.metadata_snapshot_json` 做维度分析。

## 13. 测试策略：minimum first

用户明确希望第一阶段测试保持 minimum，先把工程跑起来。因此测试策略调整为“最小可靠测试集”，先覆盖最容易破坏核心闭环的纯业务逻辑，不追求完整 UI/E2E 覆盖。

### 13.1 第一版 minimum 测试范围

必须有的最小测试：

1. 文本 normalization 与唤醒词匹配。
2. 样本语义校验。
3. WAV 探测与 hash 去重的最小 happy path。
4. 抽样服务：quota、include/exclude、固定 seed 可复现。
5. 导出服务：manifest.jsonl、dataset.yaml、negative_hours。

这些测试优先写成后端单元测试，不依赖浏览器。

### 13.2 暂不强制的测试

第一版不强制：

- 完整前端 E2E。
- 复杂浏览器自动化。
- 大规模性能测试。
- 多平台 CI 矩阵。
- 音频增强算法测试。
- 评测脚本真实调用集成测试。

但工程结构要允许后续补充。

### 13.3 跨平台冒烟测试

为了保证 Windows/Linux/macOS 都能跑，第一版至少提供一个轻量 smoke test 或命令：

```bash
python -m kws_testset doctor
```

或：

```bash
uv run pytest tests/test_smoke.py
```

检查：

- 配置可加载。
- SQLite 可初始化。
- 数据目录可创建。
- pathlib 路径处理正常。
- 一个临时 wav 可被探测。
- manifest 可写出。

## 14. 第一版验收标准

### 14.1 导入能力

- 能选择一批 wav。
- 能读取时长、采样率、声道、hash。
- 能批量和逐条补充 metadata。
- 能创建 source + original variant。
- 能区分 draft/ready。
- 重复文件不会重复入库。

### 14.2 资产管理

- 能查看、搜索、筛选音频资产。
- 能播放音频。
- 能编辑 metadata。
- 能运行 ready 校验。

### 14.3 测试集构建

- 能创建 dataset spec。
- 能设置四类样本 quota。
- 能设置 filters 和 balance_by。
- 能 include/exclude 样本。
- 能预览覆盖率和缺口。
- 能构建不可变 version。

### 14.4 导出对接

- 能导出 `manifest.jsonl`。
- 能导出 `rich_manifest.jsonl`、`dataset.yaml`、`coverage_summary.json`。
- 能生成 `eval_config_snippet.yaml`。
- 可选复制 manifest 到用户配置的评测项目目录。
- 现有离线评测脚本可以读取导出的 manifest。

### 14.5 跨平台

- 工程不依赖 macOS 专有路径。
- 默认配置在 Windows/Linux/macOS 上可启动。
- 路径处理使用 `pathlib.Path`。
- 至少有最小 smoke test 或 doctor 命令验证本地环境。

## 15. 建议实现顺序

1. 项目骨架、配置、SQLite schema。
2. 跨平台路径与配置加载。
3. 枚举 taxonomy 与文本 normalization。
4. WAV 扫描、hash、导入服务。
5. 最小后端 API。
6. Asset Library 基础 UI。
7. ready 校验。
8. dataset spec 数据结构。
9. sampling service。
10. coverage preview。
11. dataset version 快照。
12. export service。
13. eval project config snippet。
14. minimum tests 与 smoke/doctor。

## 16. 设计小结

第一阶段平台是一个本地运行的数据集资产管理与测试集构建平台。它把不规范原声 wav 导入为标准化 source/variant 资产，通过 ready 质量门禁保证数据可用；再用规则抽样和手工 include/exclude 构建不可变测试集版本；最后导出兼容现有 sherpa_eval 的 manifest，同时保留 rich metadata 支撑后续细分分析。

设计重点：

- 可扩展：source/variant 谱系承接后续生成、增强、降噪损伤。
- 可维护：固定 taxonomy、清晰 service 边界、不可变 version。
- 可复现：规则快照、seed、metadata snapshot、导出产物完整记录。
- 可对接：第一版直接服务现有离线评测脚本。
- 不过度设计：不做多人标注、权限、云部署、平台内评测。
- minimum tests：先覆盖核心业务逻辑，让工程尽快跑起来。
- 跨平台：Windows/Linux/macOS 均可通过配置运行。
