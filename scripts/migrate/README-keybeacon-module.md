<!--
Copyright (c) 2026 The TOTEM ZMK Contributors
SPDX-License-Identifier: MIT
-->

# Migration tooling — firmware repo → standalone `zmk-keybeacon` module

> **Status: PENDING (not yet executed).** The `zmk-keybeacon` module repo has not been published.
> Until it is, this firmware repo keeps `config/keybeacon_kit/` in place and the Totem shield
> keeps its `include()`/`rsource` wiring, so the repo stays buildable.

One-time tooling that seeds the standalone **KeyBeacon Zephyr module**
(`github.com/ykiewang/zmk-keybeacon`) from this firmware repo, per feature 005 (research R4).

> This is separate from `split-app-repo.sh` / `README.md` in this directory, which seeded the
> **macOS app** repo under feature 003 and is retired.

## `split-keybeacon-module.sh`

History-preserving split of the kit into the module repo, with the kit content re-rooted:

| Source (this repo) | Destination (module repo) | How |
|--------------------|---------------------------|-----|
| `config/keybeacon_kit/` | **repo root** (`keybeacon.c`, `keybeacon.cmake`, `Kconfig.keybeacon`, `CMakeLists.txt`, `zephyr/module.yml`, `README.md`, `GETTING-STARTED.md`, `CHANGELOG.md`) | `git subtree split` — **commit history preserved** |

### Run

```bash
scripts/migrate/split-keybeacon-module.sh --dry-run   # show the plan, change nothing
scripts/migrate/split-keybeacon-module.sh             # produce ../zmk-keybeacon (or $KEYBEACON_MODULE_DEST)
```

The script stops **before** pushing. The push + tag is a maintainer action (requires GitHub auth):

```bash
# create the empty repo github.com/ykiewang/zmk-keybeacon first, then:
git -C ../zmk-keybeacon push -u origin main
git -C ../zmk-keybeacon tag v1.0.0
git -C ../zmk-keybeacon push origin v1.0.0            # the pinnable module tag
```

## Order of operations (why publish must come first)

The destructive firmware-repo changes depend on the module existing at a published tag:

1. **Publish** `zmk-keybeacon` `v1.0.0` (steps above).
2. Add `west.yml` to this repo pinning `zmk-keybeacon` `v1.0.0` — **task T012**.
3. Remove the `include(...)` line from `config/boards/shields/totem/CMakeLists.txt` — **T013**.
4. Remove the `rsource ...` line from `config/boards/shields/totem/Kconfig.defconfig` — **T014**.
5. Delete `config/keybeacon_kit/` from this repo — **task T018**.

Doing 2–5 before step 1 would break `west update` / the Totem build, because the pinned module
would not yet be fetchable. Pre-publish local validation instead uses
`ZEPHYR_EXTRA_MODULES=<repo>/config/keybeacon_kit` (quickstart Scenario A).

---

<a id="zh-migrate-kb"></a>

# 迁移工具 — 固件仓 → 独立 `zmk-keybeacon` 模块（中文版）

**English** · [中文](#zh-migrate-kb)

> **状态:待执行(尚未运行)。** `zmk-keybeacon` 模块仓库尚未发布。在发布之前,本固件仓保留
> `config/keybeacon_kit/`,Totem shield 保留其 `include()`/`rsource` 接线,使仓库保持可构建。

一次性工具,依据 feature 005(research R4)从本固件仓 seeding 出独立的 **KeyBeacon Zephyr 模块**
(`github.com/ykiewang/zmk-keybeacon`)。

> 本工具与本目录下的 `split-app-repo.sh` / `README.md` 相互独立——后者在 feature 003 下 seeding
> 了 **macOS 应用**仓并已退役。

## `split-keybeacon-module.sh`

将 kit 保历史地拆分到模块仓库,内容重定位到仓库根:

| 来源(本仓) | 目标(模块仓) | 方式 |
|------------|--------------|-----|
| `config/keybeacon_kit/` | **仓库根**(`keybeacon.c`、`keybeacon.cmake`、`Kconfig.keybeacon`、`CMakeLists.txt`、`zephyr/module.yml`、`README.md`、`GETTING-STARTED.md`、`CHANGELOG.md`) | `git subtree split` —— **提交历史保留** |

### 运行

```bash
scripts/migrate/split-keybeacon-module.sh --dry-run   # 显示计划,不做任何改动
scripts/migrate/split-keybeacon-module.sh             # 产出 ../zmk-keybeacon(或 $KEYBEACON_MODULE_DEST)
```

脚本在 push **之前**停止。推送 + 打 tag 是维护者操作(需要 GitHub 认证):

```bash
# 先创建空仓库 github.com/ykiewang/zmk-keybeacon,然后:
git -C ../zmk-keybeacon push -u origin main
git -C ../zmk-keybeacon tag v1.0.0
git -C ../zmk-keybeacon push origin v1.0.0            # 可被 pin 的模块标签
```

## 操作顺序(为何必须先发布)

固件仓的破坏性改动依赖模块已在某个发布 tag 上存在:

1. **发布** `zmk-keybeacon` `v1.0.0`(上述步骤)。
2. 本仓添加 `west.yml` 固定 `zmk-keybeacon` `v1.0.0` —— **任务 T012**。
3. 从 `config/boards/shields/totem/CMakeLists.txt` 移除 `include(...)` 行 —— **T013**。
4. 从 `config/boards/shields/totem/Kconfig.defconfig` 移除 `rsource ...` 行 —— **T014**。
5. 从本仓删除 `config/keybeacon_kit/` —— **任务 T018**。

在第 1 步之前执行 2–5 会破坏 `west update` / Totem 构建,因为被 pin 的模块尚不可拉取。发布前的
本地验证改用 `ZEPHYR_EXTRA_MODULES=<repo>/config/keybeacon_kit`(quickstart 场景 A)。
