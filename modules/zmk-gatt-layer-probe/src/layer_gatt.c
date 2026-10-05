/*
 * Copyright (c) 2024 The ZMK Contributors
 * SPDX-License-Identifier: MIT
 *
 * ZMK GATT Layer Probe - Step-1 自定义 UUID 验证
 * 
 * 暴露当前最高激活层号（uint8_t）通过自定义 GATT 服务，
 * 验证 macOS 能否发现和读取自定义 128-bit UUID。
 */

#include <zephyr/types.h>
#include <zephyr/bluetooth/bluetooth.h>
#include <zephyr/bluetooth/gatt.h>
#include <zephyr/bluetooth/uuid.h>
#include <zephyr/logging/log.h>
#include <zephyr/init.h>

#include <zmk/keymap.h>
#include <zmk/event_manager.h>
#include <zmk/events/layer_state_changed.h>

LOG_MODULE_DECLARE(zmk, CONFIG_ZMK_LOG_LEVEL);

// 自定义 UUID（与 probe.py 对齐）
// Service: AA440AA0-F5ED-4C48-84A1-8062D20D3D55
#define GATT_LAYER_SERVICE_UUID                                                                    \
    BT_UUID_DECLARE_128(BT_UUID_128_ENCODE(0xAA440AA0, 0xF5ED, 0x4C48, 0x84A1, 0x8062D20D3D55))

// Characteristic: AA440AA1-F5ED-4C48-84A1-8062D20D3D55
#define GATT_LAYER_CHAR_UUID                                                                       \
    BT_UUID_DECLARE_128(BT_UUID_128_ENCODE(0xAA440AA1, 0xF5ED, 0x4C48, 0x84A1, 0x8062D20D3D55))

static uint8_t current_layer = 0;

// GATT read callback
static ssize_t read_layer(struct bt_conn *conn, const struct bt_gatt_attr *attr, void *buf,
                          uint16_t len, uint16_t offset) {
    LOG_DBG("GATT read: layer=%d", current_layer);
    return bt_gatt_attr_read(conn, attr, buf, len, offset, &current_layer, sizeof(current_layer));
}

// CCC (Client Characteristic Configuration) for notify
static void layer_ccc_cfg_changed(const struct bt_gatt_attr *attr, uint16_t value) {
    LOG_INF("Layer notify %s", (value == BT_GATT_CCC_NOTIFY) ? "enabled" : "disabled");
}

// GATT 服务定义
BT_GATT_SERVICE_DEFINE(
    gatt_layer_svc,
    BT_GATT_PRIMARY_SERVICE(GATT_LAYER_SERVICE_UUID),
    BT_GATT_CHARACTERISTIC(GATT_LAYER_CHAR_UUID,
                           BT_GATT_CHRC_READ | BT_GATT_CHRC_NOTIFY,
                           BT_GATT_PERM_READ,
                           read_layer, NULL, NULL),
    BT_GATT_CCC(layer_ccc_cfg_changed, BT_GATT_PERM_READ | BT_GATT_PERM_WRITE),
);

// ZMK layer state changed 事件处理
static int layer_state_changed_handler(const zmk_event_t *eh) {
    current_layer = zmk_keymap_highest_layer_active();
    LOG_DBG("Layer changed: now=%d", current_layer);

    // Notify subscribed clients (if any)
    bt_gatt_notify(NULL, &gatt_layer_svc.attrs[1], &current_layer, sizeof(current_layer));
    
    return ZMK_EV_EVENT_BUBBLE;
}

ZMK_LISTENER(gatt_layer_listener, layer_state_changed_handler);
ZMK_SUBSCRIPTION(gatt_layer_listener, zmk_layer_state_changed);

// 初始化：读取当前层号
static int gatt_layer_init(void) {
    current_layer = zmk_keymap_highest_layer_active();
    LOG_INF("GATT layer probe initialized: layer=%d", current_layer);
    return 0;
}

SYS_INIT(gatt_layer_init, APPLICATION, CONFIG_APPLICATION_INIT_PRIORITY);
