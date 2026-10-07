# Feature Specification: ZMK Module Distribution

**Feature Branch**: `005-zmk-module-distribution`

**Created**: 2026-10-07

**Status**: Draft

**Input**: User description: "通过zmk module来实现，请分析"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 新用户零拷贝接入 KeyBeacon (Priority: P1)

一位拥有任意 ZMK 键盘的用户想要为自己的键盘添加 KeyBeacon 支持。他不需要复制任何代码文件，只需在 `west.yml` 中添加一行 URL 引用，再在 `.conf` 中启用一个 Kconfig 符号，构建即可成功。

**Why this priority**: 这是本 feature 的核心价值——消除每个用户都持有一份代码副本的问题。实现此用户故事即视为 MVP 交付。

**Independent Test**: 从一个全新的、不包含任何 keybeacon_kit 文件的 zmk-config 仓库出发，仅通过 `west.yml` + `CONFIG_ZMK_KEYBEACON=y` 成功构建出携带 KeyBeacon 功能的固件。

**Acceptance Scenarios**:

1. **Given** 用户拥有一个干净的 zmk-config 仓库（无 keybeacon_kit 目录），**When** 用户在 `west.yml` 中添加 `zmk-keybeacon` 模块引用并执行 `west update`，**Then** west 自动拉取模块代码，无需手动复制文件。
2. **Given** 模块已通过 west 拉取，**When** 用户在 central `.conf` 中添加 `CONFIG_ZMK_KEYBEACON=y` 后执行 `west build`，**Then** 固件成功构建，KeyBeacon GATT 服务编译进 central 目标，peripheral 和 settings_reset 目标不受影响。
3. **Given** 固件已构建并烧录，**When** 用户使用 probe.py 或 BleWidget 连接键盘，**Then** 工具正常读取到层状态和修饰键状态，行为与从代码复制接入的版本一致。

---

### User Story 2 - 模块升级不破坏用户仓库 (Priority: P2)

KeyBeacon 模块发布新版本后，用户只需在 `west.yml` 中更新 `revision` 字段并运行 `west update`，无需在自己的仓库中修改任何文件。

**Why this priority**: 模块化的核心价值之一是可独立更新。若升级需要用户手动同步文件，则与复制代码相比无本质改善。

**Independent Test**: 将 `west.yml` 中的 `revision` 从旧 tag 改为新 tag，运行 `west update && west build`，构建成功且用户仓库无文件变更。

**Acceptance Scenarios**:

1. **Given** 用户已通过模块方式接入 KeyBeacon v1，**When** 模块发布 v2 并用户更新 `revision`，**Then** 用户仓库内无需修改任何 `.c`、`.cmake`、`.kconfig` 文件即可完成升级。

---

### User Story 3 - 现有 Totem 仓库平滑迁移 (Priority: P3)

当前 zmk-config-totem 仓库中已有 `config/keybeacon_kit/` 目录。迁移后，该目录从主仓库移除，由 west 模块提供，shield 的 CMakeLists.txt 和 Kconfig.defconfig 中的引用路径相应更新，功能不变。

**Why this priority**: 迁移是必要的一致性工作，但不影响外部新用户的接入体验，优先级低于前两个故事。

**Independent Test**: 删除 `config/keybeacon_kit/` 目录后，仅依赖模块路径完成构建，功能测试结果与迁移前一致。

**Acceptance Scenarios**:

1. **Given** 主仓库已移除 `config/keybeacon_kit/`，**When** 执行 `west build`，**Then** 构建系统通过 west 模块找到 keybeacon 源文件，构建成功。
2. **Given** 迁移完成，**When** 对 Totem 运行 probe.py 验证，**Then** 输出结果与迁移前相同。

---

### Edge Cases

- 用户的 zmk-config 仓库尚未有 `west.yml`（使用 GitHub Actions 默认 zmk 工作流而非本地 west）：ZMK 的 GitHub Actions 构建系统支持通过 `west.yml` 声明外部模块；若用户没有 `west.yml` 则需要新建，文档须覆盖此场景。
- 用户同时拥有旧的 `keybeacon_kit/` 副本和新的模块引用：构建系统可能遇到符号重复定义；文档须说明迁移时需删除旧副本。
- peripheral-only 键盘（无 central 角色）：模块的 cmake 守卫与现有行为一致，keybeacon.c 不编译进去，但用户可能困惑；文档须明确说明前置条件。

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `zmk-keybeacon` 必须作为独立 Git 仓库发布，包含 `keybeacon.c`、`keybeacon.cmake`、`Kconfig.keybeacon` 以及 `zephyr/module.yml`。
- **FR-002**: `zephyr/module.yml` 必须正确声明 cmake 和 Kconfig 入口，使 Zephyr 构建系统无需用户在 shield 中手写 `include()` 和 `rsource` 即可自动集成。
- **FR-003**: 用户接入 KeyBeacon 所需的用户侧修改必须缩减为：在 `west.yml` 中添加模块引用，以及在 central `.conf` 中添加 `CONFIG_ZMK_KEYBEACON=y`，共两处。
- **FR-004**: 模块的 cmake 守卫（`CONFIG_ZMK_KEYBEACON AND CONFIG_ZMK_BLE AND CONFIG_ZMK_SPLIT_ROLE_CENTRAL`）必须完整保留，peripheral 和 settings_reset 构建目标不得引入 keybeacon.c。
- **FR-005**: 模块必须通过语义化版本（semver）tag 发布，`west.yml` 中通过 `revision` 字段固定版本。
- **FR-006**: 现有 zmk-config-totem 中 Totem shield 的 `include()`/`rsource` 接线必须**移除**（模块通过 `zephyr/module.yml` 自动注入 cmake 和 Kconfig，无需重指路径），`config/keybeacon_kit/` 目录从主仓库移除。
- **FR-007**: 接入文档（GETTING-STARTED.md）必须更新，覆盖"有 west.yml"和"无 west.yml（新建）"两种用户场景。

### Key Entities

- **zmk-keybeacon 模块仓库**：独立 Git repo，包含 keybeacon 固件代码和 Zephyr 模块声明；唯一真相源，所有用户共享同一份代码。
- **west.yml**：用户 zmk-config 仓库中的 west manifest 文件；声明对 zmk-keybeacon 模块的版本化依赖。
- **zephyr/module.yml**：模块仓库内的 Zephyr 模块声明文件；向构建系统暴露 Kconfig 和 cmake 入口点。

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 新用户从零接入 KeyBeacon 所需编辑的用户仓库文件数从 4 个（CMakeLists.txt、Kconfig.defconfig、.conf、复制的 keybeacon_kit 文件）降低到 2 个（west.yml、.conf）。
- **SC-002**: 模块升级时用户仓库需要修改的文件数为 1（仅 west.yml 中的 revision 字段），不需要手动同步任何源文件。
- **SC-003**: 基于模块接入的构建产物通过与复制接入方式完全相同的 probe.py 验证，输出结果无差异；若 keybeacon 仓一致性工具可用，逐项核对结果亦无差异。
- **SC-004**: Totem 参考实现成功从复制模式迁移到模块模式，`config/keybeacon_kit/` 目录从主仓库移除后构建仍通过。

## Assumptions

- 目标用户已具备基本的 west/ZMK 构建环境，了解如何编辑 `west.yml`。
- `zmk-keybeacon` 模块仓库托管在 GitHub，使用 HTTPS URL，与 ZMK 社区其他第三方模块（如 zmk-tri-state）保持一致的发布模式。
- ZMK 的 GitHub Actions CI（`zmk-config` 模板）支持通过 `west.yml` 声明第三方模块——这是 ZMK 社区已验证的既有能力，无需额外 spike。
- `keybeacon.c` 的实际代码内容不变，模块化仅涉及打包方式和引用路径，不触及 GATT 逻辑。
- 本 feature 不包括为模块仓库建立自动化 CI 构建——该工作属于模块仓库的独立 scope，不在本 spec 范围内。
