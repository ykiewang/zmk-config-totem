# Phase 0 Research: ZMK Module Distribution

本文档解决 feature 005 Technical Context 中的所有技术决策点。无开放 NEEDS CLARIFICATION 项。

---

## R1. Zephyr module.yml 的正确结构

- **Decision**: `zephyr/module.yml` 的 cmake 入口指向模块根目录（`.`），Kconfig 入口直接指向 `Kconfig.keybeacon` 文件。结构如下：

```yaml
name: zmk-keybeacon
build:
  cmake: .
  kconfig: Kconfig.keybeacon
```

- **Rationale**: Zephyr 模块系统在构建时会自动执行 `cmake` 字段指定目录下的 `CMakeLists.txt`（即 `keybeacon.cmake` 通过 `include()` 或直接重命名为 `CMakeLists.txt`），并自动 `rsource` Kconfig 字段指定的文件。用户侧无需在 shield 中手写这两行。ZMK 社区已有 `zmk-tri-state`、`zmk-auto-layer` 等模块验证此模式。
- **关键细节**: `keybeacon.cmake` 需重命名为 `CMakeLists.txt`（Zephyr 模块 cmake 入口的惯例），或在模块根目录新建 `CMakeLists.txt` 并 `include(keybeacon.cmake)`。cmake 守卫逻辑不变。
- **Alternatives considered**:
  - *`cmake` 字段指向 `keybeacon.cmake` 文件路径* — Zephyr 的 `cmake` 字段期望目录，不是文件；已排除。
  - *将 cmake 守卫写入独立脚本* — 不必要，现有 `keybeacon.cmake` 守卫已完整，只需被正确调用。

---

## R2. 模块路径：用户侧 shield 的 CMakeLists.txt 和 Kconfig.defconfig 变更

- **Decision**: 迁移到模块方式后，用户的 shield 文件**不需要** `include(...)` 和 `rsource ...` 这两行。Zephyr 模块系统在 west fetch 后自动完成这两个操作。因此 Totem shield 的 `CMakeLists.txt` 和 `Kconfig.defconfig` 中对 `keybeacon_kit/` 的显式引用行**直接删除**。
- **Rationale**: 这正是模块化的核心收益。`zephyr/module.yml` 声明的 cmake/kconfig 入口由构建系统自动注入，无需用户手动接线。
- **Totem 迁移具体改动**:
  - `config/boards/shields/totem/CMakeLists.txt`：删除 `include(${CMAKE_CURRENT_LIST_DIR}/../../../keybeacon_kit/keybeacon.cmake)` 一行（或整个文件若只有此行）。
  - `config/boards/shields/totem/Kconfig.defconfig`：删除 `rsource "../../../keybeacon_kit/Kconfig.keybeacon"` 一行。

---

## R3. west.yml 的结构与 ZMK GitHub Actions 兼容性

- **Decision**: 用户在 zmk-config 的 `config/west.yml`（ZMK 约定 manifest 位于 `config/` 下，通常已存在）中声明 ZMK 本体依赖和 zmk-keybeacon 模块。ZMK 的 GitHub Actions CI 原生支持此方式，已有社区模块（如 `zmk-tri-state`）验证。最小结构：

```yaml
manifest:
  remotes:
    - name: zmkfirmware
      url-base: https://github.com/zmkfirmware
    - name: ykiewang
      url-base: https://github.com/ykiewang
  projects:
    - name: zmk
      remote: zmkfirmware
      revision: main
      import: app/west.yml
    - name: zmk-keybeacon
      remote: ykiewang
      revision: v1.0.0
  self:
    path: config
```

- **Rationale**: `import: app/west.yml` 继承 ZMK 本体的所有依赖声明（Zephyr、modules 等），避免用户重复声明。`revision: v1.0.0` 固定版本，保证构建可复现。
- **GitHub Actions 兼容性**: ZMK 的 `.github/workflows/build.yml` 在检测到 `west.yml` 时会自动运行 `west update` 拉取所有 project，包括第三方模块。无需修改 CI 配置。
- **Alternatives considered**:
  - *不使用 `import`，手动列出所有 ZMK 依赖* — 维护成本极高，ZMK 依赖树复杂；排除。
  - *使用 `git submodule` 替代 west manifest* — submodule 需要用户手动 `git submodule update`，与 ZMK 的标准构建流程不兼容；排除。

---

## R4. 模块仓库的文件结构

- **Decision**: 模块仓库根目录直接放置所有文件，`zephyr/module.yml` 在子目录下。根目录新建 `CMakeLists.txt` 作为 cmake 入口（内容为 `include(${CMAKE_CURRENT_LIST_DIR}/keybeacon.cmake)`），以便保留原 `keybeacon.cmake` 文件名：

```text
zmk-keybeacon/
├── zephyr/
│   └── module.yml
├── CMakeLists.txt          ← 新建，内容：include(${CMAKE_CURRENT_LIST_DIR}/keybeacon.cmake)
├── keybeacon.c             ← 原样移入，内容不变
├── keybeacon.cmake         ← 原样移入，路径引用需核查（${CMAKE_CURRENT_LIST_DIR} 已正确）
├── Kconfig.keybeacon       ← 原样移入，内容不变
├── README.md
└── CHANGELOG.md
```

- **Rationale**: 保留 `keybeacon.cmake` 原文件名，对熟悉旧接入方式的用户保持可读性。`CMakeLists.txt` 作为 Zephyr 模块 cmake 入口的薄包装层，不引入逻辑。
- **keybeacon.cmake 路径检查**: 现有 `keybeacon.cmake` 使用 `${CMAKE_CURRENT_LIST_DIR}/keybeacon.c`，在模块根目录下仍然正确，无需修改。

---

## R5. 版本策略与初始发布

- **Decision**: 模块首版标记为 `v1.0.0`（semver）。`CHANGELOG.md` 记录初始发布内容。firmware repo 的 `west.yml` 固定 `revision: v1.0.0`。后续协议变更（GATT 接口、payload 格式）触发 MAJOR 版本；向后兼容的新 Kconfig 符号触发 MINOR；纯修复触发 PATCH。
- **Rationale**: 与 ZMK 社区其他第三方模块（`zmk-tri-state` 等）的版本化惯例一致。firmware repo 固定 tag 而非 `main`，保证构建可复现（SC-002）。
- **Alternatives considered**:
  - *`revision: main`（跟踪最新）* — 违反构建可复现原则，模块更新可能意外破坏固件构建；排除。

---

## R6. 从 in-repo 复制方式迁移的 Totem 路径变更汇总

迁移后 Totem 仓库需要的所有变更（不涉及任何固件运行时或 GATT 行为改动）：

| 文件 | 变更类型 | 具体内容 |
|------|----------|----------|
| `config/keybeacon_kit/` 整个目录 | 删除 | 内容迁移至模块仓库 |
| `config/boards/shields/totem/CMakeLists.txt` | 删除一行或删除整个文件 | 移除 `include(...keybeacon.cmake)` |
| `config/boards/shields/totem/Kconfig.defconfig` | 删除一行 | 移除 `rsource "...Kconfig.keybeacon"` |
| `west.yml`（新建） | 新增 | west manifest，声明 zmk-keybeacon 模块依赖 |
| `config/keybeacon_kit/GETTING-STARTED.md` | 更新（移至模块仓库后保留副本或重定向） | Step 1 由"复制目录"改为"添加到 west.yml" |

---

## R7. 需要 spike 验证的风险项

本 feature 无高风险未知项，但以下两点在实施前需快速验证（可本地验证，无需 CI）：

1. **`zephyr/module.yml` cmake 入口调用时机**：确认 west fetch 后 Zephyr 构建系统会在用户 shield 的 `CMakeLists.txt` **之前**注入模块 cmake，使 Kconfig 符号在 shield 中可见。（ZMK 社区模块行为已有先例，置信度高。）
2. **`CONFIG_ZMK_KEYBEACON` 符号可见性**：模块的 `Kconfig.keybeacon` 通过 `zephyr/module.yml` 的 `kconfig` 字段 rsource 后，确认符号在 shield 的 `.conf` 中可正常设置。（与 cmake 入口同属 Zephyr 模块标准机制，置信度高。）
