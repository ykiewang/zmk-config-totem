/*
 * Copyright (c) 2024 The ZMK Contributors
 * SPDX-License-Identifier: MIT
 *
 * GATT Layer Probe - Step-1 自定义 UUID 验证
 *
 * 目的只验证「macOS 用户态能否发现/读取/订阅自定义 128-bit UUID 特征」，
 * 并不需要真实层号，所以不依赖任何 ZMK 内部头（app/include 是 PRIVATE，
 * 独立 module 拿不到）。用纯 Zephyr BT API 暴露一个假层号：
 *   - READ   返回当前假值
 *   - NOTIFY 由定时器每 5s 把假值在 0..7 间循环递增并推送
 * 这样 READ 和 NOTIFY 两条链路都能在探针里观测到。
 */

#include <zephyr/types.h>
#include <zephyr/kernel.h>
#include <zephyr/init.h>
#include <zephyr/bluetooth/bluetooth.h>
#include <zephyr/bluetooth/gatt.h>
#include <zephyr/bluetooth/uuid.h>
#include <zephyr/logging/log.h>

LOG_MODULE_REGISTER(gatt_layer_probe, LOG_LEVEL_INF);

// 自定义 UUID（与 probe.py 对齐）
// Service: AA440AA0-F5ED-4C48-84A1-8062D20D3D55
#define GATT_LAYER_SERVICE_UUID                                                                    \
    BT_UUID_DECLARE_128(BT_UUID_128_ENCODE(0xAA440AA0, 0xF5ED, 0x4C48, 0x84A1, 0x8062D20D3D55))

// Characteristic: AA440AA1-F5ED-4C48-84A1-8062D20D3D55
#define GATT_LAYER_CHAR_UUID                                                                       \
    BT_UUID_DECLARE_128(BT_UUID_128_ENCODE(0xAA440AA1, 0xF5ED, 0x4C48, 0x84A1, 0x8062D20D3D55))

static uint8_t fake_layer = 7;
static bool notify_enabled;

static ssize_t read_layer(struct bt_conn *conn, const struct bt_gatt_attr *attr, void *buf,
                          uint16_t len, uint16_t offset) {
    LOG_INF("GATT read: layer=%d", fake_layer);
    return bt_gatt_attr_read(conn, attr, buf, len, offset, &fake_layer, sizeof(fake_layer));
}

static void layer_ccc_cfg_changed(const struct bt_gatt_attr *attr, uint16_t value) {
    notify_enabled = (value == BT_GATT_CCC_NOTIFY);
    LOG_INF("Layer notify %s", notify_enabled ? "enabled" : "disabled");
}

BT_GATT_SERVICE_DEFINE(
    gatt_layer_svc,
    BT_GATT_PRIMARY_SERVICE(GATT_LAYER_SERVICE_UUID),
    BT_GATT_CHARACTERISTIC(GATT_LAYER_CHAR_UUID,
                           BT_GATT_CHRC_READ | BT_GATT_CHRC_NOTIFY,
                           BT_GATT_PERM_READ,
                           read_layer, NULL, NULL),
    BT_GATT_CCC(layer_ccc_cfg_changed, BT_GATT_PERM_READ | BT_GATT_PERM_WRITE),
);

static void layer_tick(struct k_work *work) {
    fake_layer = (fake_layer + 1) % 8;
    if (notify_enabled) {
        bt_gatt_notify(NULL, &gatt_layer_svc.attrs[1], &fake_layer, sizeof(fake_layer));
        LOG_INF("GATT notify: layer=%d", fake_layer);
    }
}

static K_WORK_DEFINE(layer_work, layer_tick);

static void layer_timer_expiry(struct k_timer *timer) {
    k_work_submit(&layer_work);
}

static K_TIMER_DEFINE(layer_timer, layer_timer_expiry, NULL);

static int gatt_layer_init(void) {
    k_timer_start(&layer_timer, K_SECONDS(5), K_SECONDS(5));
    LOG_INF("GATT layer probe initialized: layer=%d", fake_layer);
    return 0;
}

SYS_INIT(gatt_layer_init, APPLICATION, CONFIG_APPLICATION_INIT_PRIORITY);
