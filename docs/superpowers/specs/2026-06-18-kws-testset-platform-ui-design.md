# KWS 测试集平台化 UI 设计

日期：2026-06-18  
状态：已确认设计，待用户复核  
范围：在已完成后端 MVP 基础上，实现完整平台化 UI 的第一阶段闭环

## 1. 背景

当前工程已经完成后端 MVP：

- FastAPI + SQLite/SQLModel 后端。
- Python CLI：`uv run python -m kws_testset doctor`、`uv run python -m kws_testset serve`。
- WAV 探测、hash、导入、资产列表、dataset spec、dataset version、导出等基础能力。
- 一个极简静态 web shell。

本设计在该基础上补齐平台化 UI。目标不是一次性做完整 CMS，而是把用户最需要的第一条工作流做成可用闭环：

```text
浏览器导入 wav
  -> 批量补 metadata
  -> 资产列表筛选 / 播放 / 编辑
  -> 创建 dataset spec
  -> 预览覆盖率与缺口
  -> 构建 dataset version
  -> 导出 manifest / rich_manifest / eval_config_snippet
```

## 2. 设计目标

第一阶段 UI 目标：

1. 让不规范的历史 wav 可以通过人工输入信息导入。
2. 让原声 wav 在没有变速、变调、加噪等增强处理的情况下先进入资产库。
3. 支持关键词正样本、相近音负样本、非完整唤醒语音的管理。
4. 支持音色、音量、音调、语速、噪声、损伤场景等 metadata 的可视化编辑。
5. 支持构建测试集版本，并导出离线评测脚本可消费的文件。
6. 保持工程在 macOS、Windows、Linux 上都能跑。
7. 保持测试 minimum，先确保工程能启动、构建、主要 API 能工作。

## 3. 明确不做

第一版平台化 UI 不做：

- 未标注音频发现、自动标注、多人审核。
- 平台内 ASR 标注。
- 在线音频编辑器。
- TTS、变速、变调、加噪、降噪等生成和增强流水线。
- 模型评测任务调度与结果分析。
- 多用户权限、审计流、团队协作。
- 动态 taxonomy 编辑。
- 完整 E2E 测试体系。

后续 C/D 扩展点需要保留，但第一版不实现。

## 4. 页面组织

采用 **Hybrid Workflow + Resource Pages**：

- 导入和构建使用向导式流程，降低一次性操作复杂度。
- 资产和版本使用资源列表页，方便反复筛选、编辑和查看。

导航结构：

```text
Dashboard
Import Wizard
Assets
Dataset Builder
Versions / Export
Settings
```

### 4.1 Dashboard

职责：

- 显示资产总数、ready 数量、缺 metadata 数量、最近 dataset version。
- 显示测试集覆盖缺口摘要。
- 提供导入、资产管理、构建测试集、导出版本的快捷入口。

不做：

- 复杂趋势图。
- 长周期统计。
- 权限或审计看板。

### 4.2 Import Wizard

职责：

- 浏览器多文件 WAV 上传。
- 上传后探测 WAV 格式、时长、采样率、通道数、hash。
- 显示 staging 表格。
- 支持批量填写 metadata。
- 支持单行编辑。
- 提交入库，生成 `AudioSource` 和 `AudioVariant(original)`。

不做：

- 本地路径扫描作为主 UI 流程。已有 scan API 可保留给 CLI 或高级用法。
- 自动 ASR。
- 在线音频剪辑。

### 4.3 Assets

职责：

- 显示资产列表。
- 支持按 sample type、quality status、voice、gender、age、volume、pitch、speed、noise、impairment 等字段筛选。
- 支持音频播放。
- 支持单条编辑 metadata。
- 支持批量编辑 metadata。
- 显示 ready / draft / invalid 状态与字段级问题。

不做：

- 复杂标注工作台。
- 多人审核流。
- 自动质量评分。

### 4.4 Dataset Builder

职责：

- 创建 dataset spec。
- 填写目标关键词、目标数量、各 sample type 配额。
- 设置基础过滤条件和 balance_by 字段。
- 预览覆盖率与缺口。
- 构建不可变 dataset version。

不做：

- 高级采样策略图形化编辑器。
- 实验追踪系统。
- 平台内模型评测。

### 4.5 Versions / Export

职责：

- 显示 dataset version 列表。
- 查看 version 详情、coverage summary、rules snapshot。
- 查看 version items。
- 导出已有后端支持的文件：
  - `manifest.jsonl`
  - `rich_manifest.jsonl`
  - `dataset.yaml`
  - `coverage_summary.json`
  - `eval_config_snippet`

不做：

- 远程发布。
- 模型评测任务调度。
- 版本合并。

### 4.6 Settings

职责：

- 只读展示数据目录、导出目录、目标关键词等当前配置。
- 只读展示 taxonomy 或链接到 taxonomy API 输出。
- 提醒用户配置来自 `configs/app.yaml`。

不做：

- 第一版不在 UI 中动态编辑 taxonomy。
- 第一版不做多 profile 配置管理。

## 5. 技术架构

前端采用：

```text
React + Vite + TypeScript
```

后端继续使用当前：

```text
FastAPI + SQLite/SQLModel + 本地文件系统
```

建议目录：

```text
/Users/e4/Documents/kws_testset/
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── src/
│       ├── api/
│       ├── components/
│       ├── pages/
│       ├── types/
│       ├── App.tsx
│       └── main.tsx
├── kws_testset/
│   ├── api/
│   ├── services/
│   ├── models/
│   └── web/
└── tests/
```

### 5.1 前端模块边界

`frontend/src/api/`

- 集中封装 `fetch`。
- 统一处理 JSON 解析和错误响应。
- 页面不直接拼 API URL。

`frontend/src/types/`

- 手写与后端 response 对齐的 TypeScript 类型。
- 第一版不引入 OpenAPI 代码生成，以降低工程复杂度。
- 后续可替换为 OpenAPI 生成。

`frontend/src/components/`

可复用组件：

- `AppShell`
- `AssetTable`
- `MetadataEditor`
- `BulkEditToolbar`
- `AudioPlayer`
- `CoveragePanel`
- `DatasetSpecForm`
- `ExportPanel`
- `StatusBadge`
- `ErrorSummary`

`frontend/src/pages/`

页面负责流程编排：

- `DashboardPage`
- `ImportPage`
- `AssetsPage`
- `DatasetBuilderPage`
- `VersionsPage`
- `SettingsPage`

### 5.2 FastAPI 服务前端

开发模式：

```text
Vite dev server -> proxy /api to FastAPI
FastAPI -> JSON API + audio streaming
```

生产/本地一体化模式：

```text
FastAPI -> serve built React assets
FastAPI -> SPA fallback to index.html for non-/api routes
```

要求：

- `/api/*` 永远优先走 API。
- 音频播放 endpoint 不被 SPA fallback 抢走。
- 前端 build 产物缺失时，后端可以回退到当前 `kws_testset/web/index.html` 或显示清晰提示。

### 5.3 跨平台运行

必须避免把核心启动流程绑定到 bash。

后端继续使用：

```bash
uv run python -m kws_testset doctor
uv run python -m kws_testset serve
```

前端使用标准 npm 命令：

```bash
cd frontend
npm install
npm run dev
npm run build
npm run typecheck
```

文档中说明：

- macOS、Windows、Linux 均使用同一组 Python / Node 命令。
- 路径继续由 Python `pathlib.Path` 处理。
- 业务逻辑不硬编码用户本机的 macOS iCloud 路径。

## 6. 后端 API 补充

当前后端已有：

```text
GET  /api/health
GET  /
GET  /api/taxonomy
GET  /api/assets
POST /api/imports/scan
POST /api/imports
POST /api/dataset-specs
POST /api/dataset-specs/{spec_id}/overrides
POST /api/dataset-specs/{spec_id}/build
POST /api/dataset-versions/{version_id}/export
```

为完成 UI 闭环，需要新增或增强：

### 6.1 Import API

```text
POST /api/imports/uploads
GET  /api/imports
GET  /api/imports/{id}
```

`POST /api/imports/uploads`：

- 接收浏览器 `multipart/form-data` 多 WAV 文件。
- 保存上传文件到受控 staging 目录，例如 `data/uploads/{upload_id}/`；正式提交时再复用现有导入服务复制到 `data/library/sources/`。
- MVP 中 staging 目录提交后暂不自动删除，用于导入失败排查和重试；清理策略后续单独设计。
- 对每个文件做 WAV probe 和 sha256。
- 返回每行文件的探测结果、重复状态、初始 metadata、字段错误。
- 允许部分文件失败，失败行留在 response 中。

`POST /api/imports` 增强：

- 默认保持现有原子提交语义：提交的行只要有一行非法，整批失败并回滚。
- UI 提交 staging 成功行时使用 `partial=true`，后端逐行校验并跳过非法行。
- `partial=true` response 返回 `failed_count` 和逐行 `status/errors`，用于 UI 标记哪些行没有入库。

`GET /api/imports`：

- 返回 import batch 列表。

`GET /api/imports/{id}`：

- 返回单个 import batch 详情和导入数量。

### 6.2 Asset API

```text
GET   /api/assets
PATCH /api/assets/{id}
POST  /api/assets/bulk-update
GET   /api/assets/{id}/audio
```

`GET /api/assets` 增强：

- 支持 query filters。
- 支持分页或最小 limit/offset。
- response 包含 ready validation summary。

`PATCH /api/assets/{id}`：

- 修改单条 `AudioVariant` metadata。
- 保存后重新计算 normalized_text 和 quality/ready 状态。
- 返回更新后的 asset 和字段级问题。

`POST /api/assets/bulk-update`：

- 接收 asset id 列表和 patch 字段。
- 对每个资产单独校验。
- 返回成功数、失败数、失败详情。

`GET /api/assets/{id}/audio`：

- 返回音频文件流，用于浏览器播放。
- 文件路径必须通过数据库记录解析，不能允许任意路径读取。

### 6.3 Dataset API

```text
GET  /api/dataset-specs
GET  /api/dataset-specs/{id}
POST /api/dataset-specs/{id}/preview
GET  /api/dataset-versions
GET  /api/dataset-versions/{id}
GET  /api/dataset-versions/{id}/items
```

`GET /api/dataset-specs`：

- 返回 spec 列表。

`GET /api/dataset-specs/{id}`：

- 返回 spec 详情和 overrides。

`POST /api/dataset-specs/{id}/preview`：

- 使用与 build 相同的候选过滤、配额、balance_by、override 规则。
- 只返回 coverage summary、候选数量、目标数量、shortfalls。
- 不创建 dataset version。

`GET /api/dataset-versions`：

- 返回 version 列表。

`GET /api/dataset-versions/{id}`：

- 返回 version 详情、rules snapshot、coverage summary、export path。

`GET /api/dataset-versions/{id}/items`：

- 返回 version item 列表，用于 UI 查看和抽查。

## 7. 核心数据流

### 7.1 Import Flow

```text
Browser FileList
  -> POST /api/imports/uploads
  -> backend saves/probes/hashes WAV
  -> response staging rows
  -> UI editable metadata table
  -> POST /api/imports
  -> AudioSource + AudioVariant(original) + ImportBatch
```

关键规则：

- 导入的当前 wav 都视为原声，生成 `variant_kind=original`。
- 仍保留 `source` / `variant` 分离，为后续 C 的增强音频做准备。
- 重复 hash 不应静默导入重复资产。
- 用户可以跳过失败行，提交成功行；UI 通过 `POST /api/imports` 的 `partial=true` 模式实现，不改变默认原子导入路径。

### 7.2 Asset Edit Flow

```text
GET /api/assets
  -> AssetTable
  -> single edit or bulk edit
  -> PATCH /api/assets/{id} or POST /api/assets/bulk-update
  -> backend validation
  -> UI refresh row status and error summary
```

关键规则：

- 后端是 metadata 合法性的最终裁判。
- 前端可以做即时提示，但不能替代后端校验。
- 单条和批量编辑都必须返回字段级错误。

### 7.3 Dataset Flow

```text
Ready assets
  -> create DatasetSpec
  -> preview coverage / shortfalls
  -> build DatasetVersion
  -> frozen DatasetItems
  -> export files
```

关键规则：

- Preview 与 Build 使用同一套采样逻辑。
- Build 成功才创建 `DatasetVersion` 和 `DatasetItem`。
- Build 失败不产生半成品 version。
- Version 不可变；后续变更通过新 spec 或新 build 产生新 version。

## 8. 校验与错误处理

第一版错误处理目标是让用户知道：

1. 哪一步失败。
2. 哪些行或字段失败。
3. 为什么失败。
4. 还能否跳过失败项继续。

### 8.1 Upload Errors

处理：

- 非 WAV 文件：标记失败行。
- WAV probe 失败：标记失败行并显示原因。
- sha256 重复：标记 duplicate，提示已有资产。
- 文件保存失败：标记失败行。

行为：

- 整批上传不因单个文件失败而完全失败。
- UI 提交入库时可以只提交有效行；当用户要求继续时，后端 `partial=true` 模式会逐行跳过非法 metadata 并返回字段级错误。

### 8.2 Validation Errors

处理：

- metadata 缺失。
- taxonomy 非法值。
- sample type 非法。
- label / text / normalized_text 不一致。
- quality status 不满足 ready 条件。

表现：

- 行级状态：Ready、Need metadata、Invalid、Duplicate。
- 字段级错误：在表格单元格或详情面板显示。
- 页面级摘要：顶部显示问题数量，并支持“只看问题行”。

### 8.3 Build Shortfall

处理：

- 构建前 preview 显示每类目标数量、可用数量、缺口。
- 第一版沿用当前后端采样策略：样本不足时可以构建实际数量不足但带有明确 shortfall 记录的版本。
- 如果后端认为规则非法，则 build 失败且不创建 version。

表现：

- CoveragePanel 展示 sample type、voice、gender、age、volume、pitch、speed、noise、impairment 等维度的覆盖情况。
- 明确显示哪些维度缺样本。

### 8.4 Export Errors

处理：

- version 不存在。
- export 目录不可写。
- manifest 生成失败。
- 音频路径缺失。

表现：

- toast 或页面错误块显示简短信息。
- 详情区域显示后端返回的错误原因。
- 不吞异常，不显示“成功但没有文件”。

## 9. 最小测试策略

用户要求保持测试 minimum，第一版只做必要验证。

### 9.1 后端测试

新增最小 pytest 覆盖：

- 上传 API smoke：多文件上传、探测结果、失败行返回。
- asset patch：单条 metadata 更新后返回新状态。
- asset bulk update：部分成功、部分失败。
- dataset spec list/get。
- dataset preview 不创建 version。
- dataset version list/get/items。
- static serving：React index.html 可返回，`/api/health` 不被 SPA fallback 抢走。

现有测试必须继续通过。

### 9.2 前端测试

第一版最小要求：

```bash
npm run typecheck
npm run build
```

可选少量单测：

- API client 错误解析。
- metadata validation display 纯函数。

### 9.3 暂缓

暂缓：

- Playwright E2E。
- 大规模组件测试。
- 视觉回归测试。

这些在 UI 稳定后再补。

## 10. 可扩展性

### 10.1 为 C：数据生成与增强保留扩展点

保留：

- `AudioSource` / `AudioVariant` 分离。
- `parent_variant_id`。
- `variant_kind`。
- impairment、noise、speed、pitch、volume 等字段。

后续可以新增：

- Variant generation jobs。
- 增强参数记录。
- 批量生成 UI。
- 生成结果回流 Assets。

### 10.2 为 D：评测与分析保留扩展点

保留：

- DatasetVersion 不可变。
- DatasetItem metadata snapshot。
- Export artifacts 与 version 关联。
- Coverage summary。

后续可以新增：

- Eval run。
- False accept / false reject 分析。
- 按 metadata 维度聚合评测结果。
- 多 version 对比。

## 11. 实施顺序建议

后续实施计划应按以下顺序拆分：

1. 前端工程脚手架和 FastAPI static serving。
2. 补充 UI 闭环所需后端 API。
3. API client 和基础 layout。
4. Import Wizard。
5. Assets 列表、播放、编辑、批量编辑。
6. Dataset Builder 和 preview。
7. Versions / Export。
8. Dashboard 和 Settings。
9. README 运行说明和最小验证。

实施时应优先保证每一步可运行、可验证，不追求一次性做完所有交互细节。
