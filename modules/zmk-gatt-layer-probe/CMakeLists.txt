if(CONFIG_ZMK_GATT_LAYER_PROBE)
  zephyr_library()
  zephyr_library_sources(src/layer_gatt.c)
endif()
