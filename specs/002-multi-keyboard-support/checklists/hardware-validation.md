# 真机验证清单:多键盘支持(feature 002)

**用途**:逐项执行并勾选,完成 `tasks.md` 中 **T029(quickstart D/E/G)** 与
**T030(SC-005 / SC-007)** 的真机验证。纯逻辑项(C 单测、F 迁移逻辑)与固件构建(A)、
移植步数(B)已在 CI/单测中验证,这里只覆盖**必须真机才能确认**的部分,外加端到端复核。

**追溯**:映射 `spec.md` 的 SC-001/002/005/006/007 与 FR-001/002/003/006/012/015/016,
以及 `quickstart.md` 场景 D/E/F/G。

---

## 0. 前置准备(一次性)

- [ ] 一台 macOS,蓝牙开启;首次启动 App 时在系统弹窗授予蓝牙权限
- [ ] **键盘甲**:一把 ZMK 分体键盘,左(central)半已刷入启用 `CONFIG_ZMK_KEYBEACON=y`
      的固件(即本仓 `totem_left`,或任意按套件移植的键盘)
- [ ] **键盘乙**(用于 E/多键盘):第二把兼容键盘,**或**把键盘甲改名后另备一把
      —— 用于证明「非 Totem 也能用」且能在多把之间选择
- [ ] 给键盘乙设置一个**不含 "Totem"** 的名字:编辑其 shield 的
      `Kconfig.defconfig` 里 `config ZMK_KEYBOARD_NAME` 的 `default`(本仓为
      `config/boards/shields/totem/Kconfig.defconfig` 的 `default "TOTEM"`),改成如
      `default "Corne42"`,重新构建并刷入左半
- [ ] 构建并准备 App 与探针:

```bash
# App(前台运行,便于看菜单栏图标/悬浮窗)
cd host/macos && swift run BleWidget

# 探针(另开一个终端)
python3 -m venv tools/.venv
tools/.venv/bin/pip install bleak        # macOS 会一并装好 pyobjc
tools/.venv/bin/python tools/probe.py
```

- [ ] 记下 App 的 UserDefaults 域名(场景 F 要用):

```bash
defaults domains | tr ',' '\n' | grep -i blewidget || echo "未找到:启动过一次 App 后再查"
```

---

## 场景 D — App 连接非 Totem 键盘,零改动(US1,SC-001/SC-002/SC-006,FR-001/002)

- [ ] 仅连接**键盘乙**(名字非 "Totem")到这台 Mac(蓝牙已配对连接)
- [ ] 不改任何 App 代码/配置,直接 `swift run BleWidget`
- [ ] **预期**:悬浮窗出现并显示实时「层名 + 四个修饰指示」,切层/按修饰键会实时变化
- [ ] **预期**:菜单栏图标为「已连接」(keyboard 图标);菜单顶部标题显示键盘乙**自报的名字**
- [ ] **预期**:全程未编辑 App 任何文件(SC-002 零主机侧配置)
- [ ] **反向**:把一台**不暴露自定义服务**的普通蓝牙设备连上 Mac,确认 App **不**把它当键盘
      (不连接、不显示)(FR-003)

> 通过标准:非 Totem 键盘可发现、可连接、状态正确;名字为键盘自报名;无代码改动。

---

## 场景 名字回退 — 空名字优雅降级(US2,SC-006,FR-006)

- [ ] 临时把某把兼容键盘的 `CONFIG_ZMK_KEYBOARD_NAME` 置空/未设,重刷左半
- [ ] 启动 App 连接它
- [ ] **预期**:菜单栏标题显示通用占位名 `Keyboard <短ID>`(不空白、不崩溃),状态照常显示

> 通过标准:无可用名字时显示通用回退名,且仍正常连接显示。

---

## 场景 E — 多键盘选择与记忆(US4,SC-005,FR-013/014/015/016)

- [ ] 同时连接**键盘甲**与**键盘乙**到这台 Mac
- [ ] 启动 App(此前未选择过任何键盘:可先执行场景 F 的「清空」或 `defaults delete <域> selectedKeyboardIdentifier`)
- [ ] 打开菜单栏 → **键盘** 子菜单
- [ ] **预期**:两把都按各自名字列出;**都不自动连接**(因无记忆项)(FR-014,不静默猜测)
- [ ] 选择**键盘甲**
- [ ] **预期**:悬浮窗开始跟踪键盘甲;**键盘** 子菜单里键盘甲带勾选(✓)
- [ ] 退出 App 并重新启动(`q` 退出后再 `swift run BleWidget`)
- [ ] **预期(SC-005)**:App **自动重连到键盘甲**(记忆的 identifier),无需再选
- [ ] 在菜单切换到**键盘乙**
- [ ] **预期**:同一个悬浮窗改为跟踪键盘乙;勾选移到键盘乙;再次重启后自动连键盘乙
- [ ] **单把自动连接**:只连一把兼容键盘启动 App
- [ ] **预期(FR-013)**:无需任何操作即自动连接

> 通过标准:多把时需显式选择;所选项跨重启记忆并自动重连;任意时刻仅一个悬浮窗跟踪一把。

---

## 场景 F — 老 Totem 用户升级,设置不丢(FR-004 边界,迁移)

> 迁移逻辑已有单测覆盖;这里验证**真实档案**在升级后位置/锁定被保留(而非重置)。
> 用 `defaults` 伪造一份「旧版」档案,`<域>` 用前置准备里查到的域名(例如 `BleWidget`)。

- [ ] 先确保 App 未运行;清掉新键,写入旧键(屏幕名用你的显示器名,如 `Built-in Retina Display`):

```bash
DOMAIN=BleWidget   # 换成你查到的真实域名
SCREEN="Built-in Retina Display"
defaults delete "$DOMAIN" settingsMigratedV2 2>/dev/null
defaults delete "$DOMAIN" "panelFrame.$SCREEN" 2>/dev/null
defaults delete "$DOMAIN" panelLocked 2>/dev/null
defaults write "$DOMAIN" "totemPanelFrame.$SCREEN" -string "120.0,640.0"
defaults write "$DOMAIN" totemPanelLocked -bool YES
```

- [ ] 启动新版 App
- [ ] **预期**:悬浮窗出现在**与旧值一致**的位置(约 x=120,y=640),且处于**锁定/穿透**状态
- [ ] 校验新键已写入、迁移标记已置位:

```bash
defaults read "$DOMAIN" "panelFrame.$SCREEN"   # 应为 120.0,640.0
defaults read "$DOMAIN" panelLocked            # 应为 1
defaults read "$DOMAIN" settingsMigratedV2     # 应为 1
```

- [ ] **不覆盖**复核:同时存在旧键与一个**已有新值**时,新值不被旧值覆盖(可另置 `panelFrame.*` 为别的值再启动验证)

> 通过标准:旧 `totem*` 位置/锁定被一次性迁移到去品牌键;已有新值不被覆盖;从不重置。

---

## 场景 G — 探针按契约识别任意键盘(US3,FR-012)

- [ ] 连接任一兼容键盘,运行 `tools/.venv/bin/python tools/probe.py`
- [ ] **预期**:打印 `found N connected candidate(s): [...]`,随后
      `status service confirmed on '<键盘名>'`(**按服务 UUID 确认**,而非按 "TOTEM" 名字)
- [ ] **预期**:逐条打印解码快照 `layer_index=.. layer_name=.. mods=0x.. active=[..]`,
      切层/按修饰键时实时更新
- [ ] 指向**非 Totem** 兼容键盘:同样可用
- [ ] 指向**无自定义服务**的设备:报告未找到(回退扫描后超时提示)

> 通过标准:探针仅凭服务契约发现并解码,跨键盘可用。

---

## 场景 SC-007 — 空闲零流量(保持 feature 001 保证)

- [ ] 连接并进入稳定状态后,**不操作键盘**,运行探针观察
- [ ] 在约 1 小时(或你能接受的时长)空闲期内,**预期**:探针**不打印任何新快照行**
      (无通知);一旦切层/按修饰键才出现新行
- [ ] 复核:名字只在连接时取一次,状态流期间不重复取名(行为上即「空闲无新增流量」)

> 通过标准:空闲期零冗余通知;名字不随状态变化重复下发(FR-007)。

---

## 结果记录

| 场景 | 覆盖 | 结果 (PASS/FAIL) | 备注 |
|------|------|------------------|------|
| D 非 Totem 连接 | SC-001/002/006, FR-001/002/003 | | |
| 名字回退 | SC-006, FR-006 | | |
| E 多键盘选择+记忆 | SC-005, FR-013/014/015/016 | | |
| F 升级保设置 | FR-004 | | |
| G 探针按契约 | FR-012 | | |
| SC-007 空闲零流量 | SC-007, FR-007 | | |

- 测试人 / 日期:________________
- App commit:________________(`git rev-parse --short HEAD`)
- 固件 CI run:________________(对应三目标 .uf2)

> 全部 PASS 后,回填 `tasks.md` 的 **T029、T030** 为 `[X]`。
