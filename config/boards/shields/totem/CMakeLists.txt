# Copyright (c) 2026 The TOTEM ZMK Contributors
# SPDX-License-Identifier: MIT

if(CONFIG_ZMK_TOTEM_GATT_STATUS AND CONFIG_ZMK_BLE AND CONFIG_ZMK_SPLIT_ROLE_CENTRAL)
    zephyr_library()
    zephyr_library_include_directories(${CMAKE_SOURCE_DIR}/include)
    zephyr_library_sources(gatt_status.c)
endif()
