# Contract: zmk-keybeacon Module Interface

本文档定义 `zmk-keybeacon` 模块仓库对外暴露的接口契约，以及消费方（用户 zmk-config 仓库）的接入契约。

## 1. 模块仓库对外契约

### 1.1 `zephyr/module.yml`

```yaml
name: zmk-keybeacon
build:
  cmake: .
  kconfig: Kconfig.keybeacon
```

**保证**:
- `name` 字段固定为 `zmk-keybeacon`，不随版本变化。
- `build.cmake: .` 表示模块根目录的 `CMakeLists.txt` 会被 Zephyr 构建系统自动 `add_subdirectory`。
- `build.kconfig` 指向的文件会被自动 `rsource`，使 `ZMK_KEYBEACON` 符号对所有拉取了本模块的构建目标可见。

### 1.2 Kconfig 符号契约

```kconfig
config ZMK_KEYBEACON
    bool "KeyBeacon: expose keyboard status (layer+mods) over a custom GATT characteristic"
    depends on ZMK_BLE
    default n
```

**保证**: 符号名、依赖、默认值在 v1.x 系列内保持不变。破坏性变更（如重命名符号）须伴随 MAJOR 版本号提升。

### 1.3 cmake 守卫契约

```cmake
if(CONFIG_ZMK_KEYBEACON AND CONFIG_ZMK_BLE AND CONFIG_ZMK_SPLIT_ROLE_CENTRAL)
    zephyr_library()
    zephyr_library_include_directories(${CMAKE_SOURCE_DIR}/include)
    zephyr_library_sources(${CMAKE_CURRENT_LIST_DIR}/keybeacon.c)
endif()
```

**保证**: 三条件守卫逐字保留。满足时且仅当满足时，`keybeacon.c` 编译进目标固件。

### 1.4 GATT 契约（不变，继承自 001/002）

- Service UUID: `AA440AA0-F5ED-4C48-84A1-8062D20D3D55`
- Characteristic UUID: `AA440AA1-F5ED-4C48-84A1-8062D20D3D55`
- Payload: `[layer_index(1B)][mods(1B)][layer_name(0-32B)]`

本 feature 不改变此契约，仅改变代码的打包与分发方式。

---

## 2. 用户侧接入契约

### 2.1 `west.yml` 最小声明

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

**约束**:
- `revision` 字段 MUST 固定为具体 tag（如 `v1.0.0`），不得使用 `main` 跟踪分支。
- 若用户已有 `west.yml`（接入了其他第三方模块），仅需在 `projects` 列表追加 `zmk-keybeacon` 一项。

### 2.2 `.conf` 激活契约

```conf
CONFIG_ZMK_KEYBEACON=y
```

**约束**: 此行 MUST 出现在 central 构建目标的 `.conf` 中（split 键盘为 central 半的 conf；unibody 为唯一目标的 conf）。

### 2.3 用户侧 MUST NOT 操作

- MUST NOT 复制 `keybeacon.c`、`keybeacon.cmake`、`Kconfig.keybeacon` 到自己仓库。
- MUST NOT 在 shield 的 `CMakeLists.txt` 手写 `include(...)`。
- MUST NOT 在 shield 的 `Kconfig.defconfig` 手写 `rsource ...`。

这三项正是模块化相对复制模式节省的操作。

---

## 3. 版本兼容性契约

| 变更类型 | 触发条件 | 版本号影响 |
|----------|----------|-----------|
| GATT UUID 或 payload 格式变更 | 协议破坏性变更 | MAJOR |
| 新增 Kconfig 符号（向后兼容） | 新特性 | MINOR |
| bug 修复，无接口变更 | 修复 | PATCH |

用户固定 `revision` 到具体 tag，因此模块侧的任何版本发布不会影响已固定版本的现有用户构建。
