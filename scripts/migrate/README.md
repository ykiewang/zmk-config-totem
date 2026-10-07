<!--
Copyright (c) 2026 The TOTEM ZMK Contributors
SPDX-License-Identifier: MIT
-->

# Migration tooling — firmware repo → standalone app repo

> **Status: RETIRED (seeding complete).** The app repo has been seeded and the split executed; this
> directory is kept for traceability only. Do **not** re-run `split-app-repo.sh` against the live
> app repo — it would recreate a seed tree over real history.

One-time tooling that seeds the standalone **KeyBeacon app repo**
(`github.com/ykiewang/keybeacon`) from this firmware repo, per feature 003 (research R2).

## `split-app-repo.sh`

History-preserving split of the macOS app into the app repo:

| Source (this repo) | Destination (app repo) | How |
|--------------------|------------------------|-----|
| `host/macos/` | `app/macos/` | `git subtree split` — **commit history preserved** |
| `specs/003-standalone-app-and-protocol/protocol/` | `protocol/` | seeded fresh (content copied by the protocol tasks) |
| `tools/probe.py` | `conformance/` | seeded fresh (evolved by the conformance tasks) |

Only `host/macos/` carries real multi-feature history (001/002), so it is the one path
that is split. `protocol/` and `conformance/` are newly authored in the app repo (their
editorial history would be a single commit), so they are seeded by their own tasks rather
than split.

### Run

```bash
scripts/migrate/split-app-repo.sh --dry-run      # show the plan, change nothing
scripts/migrate/split-app-repo.sh                # produce ../keybeacon (or $KEYBEACON_DEST)
```

The script stops **before** pushing. The push to the public repo is a maintainer action
(requires GitHub auth):

```bash
git -C ../keybeacon push -u origin main
git -C ../keybeacon push origin protocol-v1.0.0   # the pinnable protocol tag
git -C ../keybeacon push origin app-v0.1.0         # triggers the first release build
```

## After migration is verified

- The firmware repo removes `host/macos/` (it now lives in the app repo) and keeps
  `tools/probe.py` as a developer probe — see feature 003 task T030.
- This `scripts/migrate/` directory is **retired** once the app repo is seeded and pushed;
  it is kept in history for traceability.

---

<a id="zh-migrate"></a>

# 迁移工具 — 固件仓 → 独立应用仓(中文版)

**English** · [中文](#zh-migrate)

> **状态:已退役(seeding 完成)。** 应用仓已完成 seeding 且拆分已执行;本目录仅为可追溯性保留。
> **请勿**再对线上应用仓重跑 `split-app-repo.sh` —— 那会在真实历史之上重建一棵 seed 树。

一次性工具,依据 feature 003(research R2)从本固件仓 seeding 出独立的 **KeyBeacon 应用仓**
(`github.com/ykiewang/keybeacon`)。

## `split-app-repo.sh`

将 macOS 应用保历史地拆分到应用仓:

| 来源(本仓) | 目标(应用仓) | 方式 |
|------------|--------------|-----|
| `host/macos/` | `app/macos/` | `git subtree split` —— **提交历史保留** |
| `specs/003-standalone-app-and-protocol/protocol/` | `protocol/` | 全新 seeding(内容由协议任务复制) |
| `tools/probe.py` | `conformance/` | 全新 seeding(由一致性任务演化而来) |

只有 `host/macos/` 承载真正的多 feature 历史(001/002),因此它是唯一被拆分的路径。`protocol/` 与
`conformance/` 在应用仓中为全新撰写(其编辑历史只会是单个提交),故由各自的任务 seeding,而非拆分。

### 运行

```bash
scripts/migrate/split-app-repo.sh --dry-run      # 显示计划,不做任何改动
scripts/migrate/split-app-repo.sh                # 产出 ../keybeacon(或 $KEYBEACON_DEST)
```

脚本在 push **之前**停止。推送到公开仓是维护者操作(需要 GitHub 认证):

```bash
git -C ../keybeacon push -u origin main
git -C ../keybeacon push origin protocol-v1.0.0   # 可被 pin 的协议标签
git -C ../keybeacon push origin app-v0.1.0         # 触发首次 release 构建
```

## 迁移验证之后

- 固件仓移除 `host/macos/`(它现在位于应用仓),并保留 `tools/probe.py` 作为开发者探针 ——
  见 feature 003 任务 T030。
- 一旦应用仓完成 seeding 并推送,本 `scripts/migrate/` 目录即**退役**;它保留在历史中以备追溯。
