# KWS Testset Platform

本项目是一个本地运行的关键词唤醒测试集创建与管理平台。第一版 MVP 支持：

- 扫描 WAV 文件并读取 duration/sample_rate/channels/hash。
- 人工提交 metadata 后导入为 `audio_source` + `audio_variant(original)`。
- 管理 ready 音频资产。
- 创建 dataset spec。
- 按 quota、include/exclude、固定 seed 构建 dataset version。
- 导出 `manifest.jsonl`、`rich_manifest.jsonl`、`dataset.yaml`、`coverage_summary.json`、`eval_config_snippet.yaml`。

## Requirements

- Python 3.11+
- uv

## Install

```bash
uv sync --extra dev
```

## Configure

默认配置文件：

```text
configs/app.yaml
```

默认数据目录：

```text
data/
```

Windows/Linux/macOS 都通过配置文件设置本机路径。代码使用 `pathlib.Path` 解析路径。

## Doctor

```bash
uv run python -m kws_testset doctor
```

期望输出包含：

```text
doctor=ok
```

## Run Server

```bash
uv run python -m kws_testset serve
```

打开：

```text
http://127.0.0.1:8000
```

API 文档：

```text
http://127.0.0.1:8000/docs
```

## Test

```bash
uv run python -m pytest -v
```

## Export to Existing sherpa_eval Project

在 `configs/app.yaml` 中配置本机评测项目路径：

```yaml
eval_project:
  root: /Users/e4/Library/Mobile Documents/com~apple~CloudDocs/自定义唤醒
  manifest_dir: sherpa_eval/data
```

第一版导出会生成 `eval_config_snippet.yaml`。将其中内容复制到评测项目的 experiment config 即可运行离线评测。
