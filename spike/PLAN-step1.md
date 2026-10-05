# Step-1: 自定义 GATT 层号服务验证

**分支**: `feature/gatt-layer-probe`  
**目标**: 验证自定义 128-bit UUID GATT 服务能否在 macOS 上被发现和读取

## 架构

```
zmk-config-totem/
  modules/
    zmk-gatt-layer-probe/          # 新增 ZMK 模块
      src/
        layer_gatt.c                # GATT 服务实现
      CMakeLists.txt
      Kconfig
      zephyr/
        module.yml
  config/
    west.yml                        # 修改：添加 modules/ 路径
    totem.conf                      # 修改：启用模块
  build.yaml                        # 不改（或可选添加 CMake 参数）
  spike/ble-probe/
    probe.py                        # 修改：读自定义 UUID
```

## 实现细节

### 1. GATT 服务定义（参考 zmk-gatt-scalar）

- **Service UUID**: `AA440AA0-F5ED-4C48-84A1-8062D20D3D55`  
- **Characteristic UUID**: `AA440AA1-F5ED-4C48-84A1-8062D20D3D55`  
- **属性**: `READ | NOTIFY`  
- **权限**: `BT_GATT_PERM_READ`（无需配对，与 HID 共存的关键）  
- **Payload**: `uint8_t layer_id`（当前最高激活层号）

### 2. ZMK 事件订阅

```c
ZMK_LISTENER(gatt_layer_listener, layer_state_changed_handler);
ZMK_SUBSCRIPTION(gatt_layer_listener, zmk_layer_state_changed);
```

### 3. West 配置

`config/west.yml` 添加本地 modules 路径（与 config 同级）：

```yaml
manifest:
  projects:
    - name: zmk
      ...
  self:
    path: config
    west-commands: scripts/west-commands.yml
    import:
      - modules/zmk-gatt-layer-probe
```

### 4. Kconfig 启用

`config/totem.conf` 添加：
```
CONFIG_ZMK_GATT_LAYER_PROBE=y
CONFIG_BT_GATT_DYNAMIC_DB=y
```

### 5. probe.py 修改

- 改 `PROBE_SERVICE` / `PROBE_CHAR` 为上面的自定义 UUID
- 读取后打印 `layer_id` 而非电量百分比
- 保持其余逻辑不变（连接/发现/读取/notify）

## 验证步骤

1. Push 到 GitHub → Actions 编译 `.uf2`
2. 下载固件，双击复位刷入左半
3. `cd spike/ble-probe && python3 probe.py`
4. 观察日志：
   - `[CB] 服务列表：['AA440AA0-F5ED-4C48-84A1-8062D20D3D55']` ✅
   - `[READ] 层号 = 0` ✅
   - 打字正常 ✅

## 判定标准

- ✅ 自定义服务被 `retrieveConnectedPeripheralsWithServices` 发现
- ✅ 自定义特征可读，返回当前层号
- ✅ HID 打字不受影响

通过后 → 路线 A 完全验证，可进正式实现。
