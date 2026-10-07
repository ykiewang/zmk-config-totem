# Data Model: ZMK Module Distribution

## Entities

### zmk-keybeacon Module Repository

独立 Git 仓库，是 KeyBeacon 固件代码的唯一真相源。

| 字段 | 值/说明 |
|------|---------|
| 标识 | `github.com/ykiewang/zmk-keybeacon` |
| 版本单元 | semver tag（`v1.0.0`、`v1.1.0` 等） |
| 版本节奏 | MAJOR：GATT 接口或 payload 格式破坏性变更；MINOR：新 Kconfig 符号等向后兼容新增；PATCH：纯修复 |
| 文件集 | `keybeacon.c`、`keybeacon.cmake`、`Kconfig.keybeacon`、`CMakeLists.txt`（薄包装）、`zephyr/module.yml` |
| 不变量 | `keybeacon.c` 内容与 v1.0.0 前的 `config/keybeacon_kit/keybeacon.c` 字节相同；cmake 守卫完整保留 |

---

### west.yml（用户侧 manifest 文件）

每个接入 KeyBeacon 的 zmk-config 仓库中的 west manifest 文件。

| 字段 | 值/说明 |
|------|---------|
| 位置 | zmk-config 仓库根目录（`west.yml`） |
| 必要声明 | `zmk` project（含 `import: app/west.yml`）+ `zmk-keybeacon` project |
| 版本锁定 | `revision: v1.0.0`（固定 tag，不跟踪 `main`） |
| 所有者 | 各用户的 zmk-config 仓库自行维护 |

---

### zephyr/module.yml（模块声明文件）

模块仓库内的 Zephyr 模块声明，向构建系统暴露 cmake 和 Kconfig 入口。

| 字段 | 值 |
|------|----|
| `name` | `zmk-keybeacon` |
| `build.cmake` | `.`（模块根目录，触发 `CMakeLists.txt`） |
| `build.kconfig` | `Kconfig.keybeacon` |
| 效果 | 构建系统自动在 shield cmake 阶段前注入模块 cmake，自动 rsource Kconfig.keybeacon |

---

### Kconfig Symbol: ZMK_KEYBEACON

| 字段 | 值/说明 |
|------|---------|
| 符号名 | `ZMK_KEYBEACON` |
| 类型 | `bool` |
| 依赖 | `ZMK_BLE` |
| 默认值 | `n` |
| 激活方式 | 用户在 central `.conf` 中写 `CONFIG_ZMK_KEYBEACON=y` |
| 可见范围 | 所有通过 west 拉取了 `zmk-keybeacon` 模块的构建目标 |

---

### CMakeLists.txt（模块 cmake 入口）

模块根目录下的薄包装文件，是 Zephyr 模块 cmake 机制的标准入口。

| 字段 | 值/说明 |
|------|---------|
| 内容 | `include(${CMAKE_CURRENT_LIST_DIR}/keybeacon.cmake)` |
| 作用 | 将实际守卫逻辑委托给 `keybeacon.cmake`，不引入新逻辑 |

---

### cmake 守卫（编译条件）

| 条件 | 说明 |
|------|------|
| `CONFIG_ZMK_KEYBEACON` | 用户在 `.conf` 中显式启用 |
| `CONFIG_ZMK_BLE` | 目标板支持 BLE |
| `CONFIG_ZMK_SPLIT_ROLE_CENTRAL` | 构建目标为 split keyboard 的 central 半 |
| 全部满足时 | `keybeacon.c` 编译进固件 |
| 任一不满足时 | 静默不编译，peripheral 和 settings_reset 不受影响 |

---

## 状态转移：用户接入流程

```
[无 west.yml] → 添加 west.yml (声明 zmk-keybeacon v1.0.0)
             → west update (拉取模块到本地 west 缓存)
             → .conf 中添加 CONFIG_ZMK_KEYBEACON=y
             → west build (构建系统注入模块 cmake/kconfig)
             → 固件含 KeyBeacon GATT 服务 [central only]
```

## 实体关系

```
zmk-keybeacon repo (tag v1.0.0)
    ↑ 引用（revision: v1.0.0）
west.yml (用户 zmk-config)
    ↓ west update 拉取
本地 west 缓存目录
    ↓ Zephyr 构建系统通过 zephyr/module.yml 注入
shield cmake + kconfig 阶段
    ↓ CONFIG_ZMK_KEYBEACON=y (用户 .conf)
keybeacon.c 编译进 central 固件
```
