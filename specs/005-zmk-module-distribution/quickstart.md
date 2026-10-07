# Quickstart Validation Guide: ZMK Module Distribution

本文档描述验证 zmk-keybeacon 模块化改造端到端可用的场景。所有场景均基于真实构建环境，不包含实现代码。

**前置条件**:
- west 工作环境已配置（ZMK 构建环境正常）
- `zmk-keybeacon` 模块仓库已发布 `v1.0.0` tag
- Totem 键盘硬件（SEEED XIAO BLE）用于 on-device 验证

---

## 场景 A：新用户零拷贝接入（验证 SC-001 / FR-003）

**目标**: 从一个不含任何 keybeacon_kit 文件的全新 zmk-config 仓库完成接入。

**准备**:

```bash
# 克隆或创建一个干净的 zmk-config 仓库（无 config/keybeacon_kit/ 目录）
# 确认目录中不存在任何 keybeacon 相关文件
ls config/keybeacon_kit  # 应报"No such file"
```

**接入步骤**（用户侧操作，仅两处）:

1. 在 `config/west.yml` 中声明（ZMK 约定 manifest 位于 config/ 下，已存在则追加 zmk-keybeacon 条目；参见 [contracts/module-interface.md](../contracts/module-interface.md) 第 2.1 节的最小声明）。
2. 在 central shield 的 `.conf` 中添加 `CONFIG_ZMK_KEYBEACON=y`。

**构建**:

```bash
west update
west build -d build/left -b seeeduino_xiao_ble -- -DSHIELD=<your_shield_central>
```

**预期结果**:
- `west update` 无错误，模块拉取到本地 west 缓存。
- `west build` 成功，编译日志中可见 `keybeacon.c` 被编译进 central 目标。
- peripheral 构建（`-DSHIELD=<your_shield_peripheral>`）成功，编译日志中无 `keybeacon.c`。

---

## 场景 B：Totem 参考实现迁移验证（验证 SC-004 / FR-006）

**目标**: 确认 `config/keybeacon_kit/` 目录从主仓库移除后，Totem 构建仍通过。

**前置变更**（迁移已完成时的状态）:
- `config/keybeacon_kit/` 目录已删除。
- `config/boards/shields/totem/CMakeLists.txt` 中的 `include(...)` 行已删除。
- `config/boards/shields/totem/Kconfig.defconfig` 中的 `rsource ...` 行已删除。
- `west.yml` 已创建并声明 `zmk-keybeacon v1.0.0`。

**构建**:

```bash
west update
west build -d build/left  -b seeeduino_xiao_ble -- -DSHIELD=totem_left
west build -d build/right -b seeeduino_xiao_ble -- -DSHIELD=totem_right
```

**预期结果**:
- `totem_left` 构建成功，`keybeacon.c` 编译进固件（`CONFIG_ZMK_SPLIT_ROLE_CENTRAL=y`）。
- `totem_right` 构建成功，`keybeacon.c` 未编译进固件。

---

## 场景 C：on-device 功能与迁移前等价性验证（验证 SC-003）

**目标**: 确认模块化接入后的固件运行时行为与直接复制 keybeacon_kit 时完全一致。

**烧录**:

```bash
# 将 totem_left 固件烧录到左半（double-press reset → mass storage）
cp build/left/zephyr/zmk.uf2 /Volumes/<LEFT_DRIVE>/
```

**运行 probe**:

```bash
python3 -m venv tools/.venv
tools/.venv/bin/pip install bleak
tools/.venv/bin/python tools/probe.py
```

**预期输出**（格式与迁移前相同）:

```
Found keyboard: TOTEM (AA440AA0-...)
layer=0 name="BASE" mods=0x00
layer=1 name="NAVI" mods=0x00
layer=1 name="NAVI" mods=0x02
layer=1 name="NAVI" mods=0x00
```

---

## 场景 D：模块版本升级不影响用户仓库（验证 SC-002）

**目标**: 确认升级 keybeacon 版本时用户仓库只需改 `west.yml` 的 revision 字段，无需修改任何源文件。

**操作**:

```yaml
# west.yml 中将 revision 从 v1.0.0 改为 v1.1.0（假设已发布）
- name: zmk-keybeacon
  remote: ykiewang
  revision: v1.1.0   # ← 唯一改动
```

```bash
west update
west build -d build/left -b seeeduino_xiao_ble -- -DSHIELD=totem_left
```

**预期结果**:
- 用户仓库中 `config/`、`CMakeLists.txt`、`Kconfig.defconfig` 无任何文件变更。
- 构建成功，使用新版本模块的代码。

---

## 场景 E：cmake 守卫验证——peripheral 不含 keybeacon（验证 FR-004 / 宪法原则 III）

**目标**: 确认三条件守卫在 peripheral 和 settings_reset 目标上生效。

```bash
# 构建 peripheral
west build -d build/right -b seeeduino_xiao_ble -- -DSHIELD=totem_right

# 检查编译日志
grep -i keybeacon build/right/CMakeFiles/modules.order || echo "NOT IN BUILD"
```

**预期结果**: `keybeacon.c` 不出现在 peripheral 构建产物中，grep 输出 "NOT IN BUILD" 或无匹配。

---

## 参考文档

- 模块接口契约：[contracts/module-interface.md](../contracts/module-interface.md)
- 实体关系：[data-model.md](../data-model.md)
- 技术决策：[research.md](../research.md)
