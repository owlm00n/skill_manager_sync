# Bug 3476234 — Log 分析

## 结论

- **分析器**：`log-analyzer`
- **log 文件数**：42
- **关键字数**：15
- **命中事件数**：14998
- **按候选根因分布**：
  - CC检测与PD通信时序配合: 14646 次
  - PD协议栈状态机实现缺陷: 352 次

## 关键事件时间线

| # | 时间戳 | 文件 | 行号 | 命中关键字 | 归属假设 | 原文 |
|---|--------|------|------|------------|----------|------|
| 1 | 01-01 08:00:00.100 | android.log | 44 | state | CC检测与PD通信时序配合 | 01-01 08:00:00.100   370   370 W auditd  : type=2000 audit(0.0:1): state=initialized audit_enabled=0 res=1 |
| 2 | 01-01 08:00:00.100 | android.log | 44 | state | CC检测与PD通信时序配合 | 01-01 08:00:00.100   370   370 W auditd  : type=2000 audit(0.0:1): state=initialized audit_enabled=0 res=1 |
| 3 | 07-01 08:13:37.035 | android.log | 9 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.035   371   371 I lowmemorykiller: kmem_event: No kernel kmem_pressure_level support (errno=2) |
| 4 | 07-01 08:13:37.035 | android.log | 10 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.035   371   371 E lowmemorykiller: Kernel does not support kernel memory events |
| 5 | 07-01 08:13:37.035 | android.log | 9 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.035   371   371 I lowmemorykiller: kmem_event: No kernel kmem_pressure_level support (errno=2) |
| 6 | 07-01 08:13:37.035 | android.log | 10 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.035   371   371 E lowmemorykiller: Kernel does not support kernel memory events |
| 7 | 07-01 08:13:37.060 | android.log | 30 | state | CC检测与PD通信时序配合 | 07-01 08:13:37.060   373   373 W hwservicemanager: addDirectoryManifests dir:/system/etc/vintf/manifest/ file: manifest_services_android.frameworks.de |
| 8 | 07-01 08:13:37.060 | android.log | 30 | state | CC检测与PD通信时序配合 | 07-01 08:13:37.060   373   373 W hwservicemanager: addDirectoryManifests dir:/system/etc/vintf/manifest/ file: manifest_services_android.frameworks.de |
| 9 | 07-01 08:13:37.205 | android.log | 314 | state | CC检测与PD通信时序配合 | 07-01 08:13:37.205   374   374 D _V_VivoConfigStore: parse vivo feature section=vivo.opt.notification.superx_state_changed_support_broadcast,keyNum=0, |
| 10 | 07-01 08:13:37.205 | android.log | 315 | state | CC检测与PD通信时序配合 | 07-01 08:13:37.205   374   374 D _V_VivoConfigStore: add default attribute key=vivo.opt.notification.superx_state_changed_support_broadcast:vivo-suppo |
| 11 | 07-01 08:13:37.205 | android.log | 314 | state | CC检测与PD通信时序配合 | 07-01 08:13:37.205   374   374 D _V_VivoConfigStore: parse vivo feature section=vivo.opt.notification.superx_state_changed_support_broadcast,keyNum=0, |
| 12 | 07-01 08:13:37.205 | android.log | 315 | state | CC检测与PD通信时序配合 | 07-01 08:13:37.205   374   374 D _V_VivoConfigStore: add default attribute key=vivo.opt.notification.superx_state_changed_support_broadcast:vivo-suppo |
| 13 | 07-01 08:13:37.487 | android.log | 388 | state | CC检测与PD通信时序配合 | 07-01 08:13:37.487   395   395 I vold    : emulated;0 setState to: 0 |
| 14 | 07-01 08:13:37.487 | android.log | 388 | state | CC检测与PD通信时序配合 | 07-01 08:13:37.487   395   395 I vold    : emulated;0 setState to: 0 |
| 15 | 07-01 08:13:37.496 | android.log | 402 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.496   395   419 D vold    : handleBlockEvent with action 1 |
| 16 | 07-01 08:13:37.496 | android.log | 402 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.496   395   419 D vold    : handleBlockEvent with action 1 |
| 17 | 07-01 08:13:37.497 | android.log | 403 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.497   395   419 D NetlinkEvent: NL param 'DEVPATH=/devices/virtual/block/dm-20' |
| 18 | 07-01 08:13:37.497 | android.log | 404 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.497   395   419 D NetlinkEvent: NL param 'SYNTH_UUID=0' |
| 19 | 07-01 08:13:37.497 | android.log | 405 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.497   395   419 D NetlinkEvent: NL param 'MAJOR=254' |
| 20 | 07-01 08:13:37.497 | android.log | 406 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.497   395   419 D NetlinkEvent: NL param 'MINOR=20' |
| 21 | 07-01 08:13:37.497 | android.log | 407 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.497   395   419 D NetlinkEvent: NL param 'DEVNAME=dm-20' |
| 22 | 07-01 08:13:37.497 | android.log | 408 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.497   395   419 D NetlinkEvent: NL param 'DEVTYPE=disk' |
| 23 | 07-01 08:13:37.497 | android.log | 409 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.497   395   419 D NetlinkEvent: NL param 'DISKSEQ=82' |
| 24 | 07-01 08:13:37.497 | android.log | 411 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.497   395   419 D vold    : handleBlockEvent with action 1 |
| 25 | 07-01 08:13:37.497 | android.log | 412 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.497   395   419 D NetlinkEvent: NL param 'DEVPATH=/devices/virtual/block/loop1' |
| 26 | 07-01 08:13:37.497 | android.log | 413 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.497   395   419 D NetlinkEvent: NL param 'SYNTH_UUID=0' |
| 27 | 07-01 08:13:37.497 | android.log | 403 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.497   395   419 D NetlinkEvent: NL param 'DEVPATH=/devices/virtual/block/dm-20' |
| 28 | 07-01 08:13:37.497 | android.log | 404 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.497   395   419 D NetlinkEvent: NL param 'SYNTH_UUID=0' |
| 29 | 07-01 08:13:37.497 | android.log | 405 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.497   395   419 D NetlinkEvent: NL param 'MAJOR=254' |
| 30 | 07-01 08:13:37.497 | android.log | 406 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.497   395   419 D NetlinkEvent: NL param 'MINOR=20' |
| 31 | 07-01 08:13:37.497 | android.log | 407 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.497   395   419 D NetlinkEvent: NL param 'DEVNAME=dm-20' |
| 32 | 07-01 08:13:37.497 | android.log | 408 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.497   395   419 D NetlinkEvent: NL param 'DEVTYPE=disk' |
| 33 | 07-01 08:13:37.497 | android.log | 409 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.497   395   419 D NetlinkEvent: NL param 'DISKSEQ=82' |
| 34 | 07-01 08:13:37.497 | android.log | 411 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.497   395   419 D vold    : handleBlockEvent with action 1 |
| 35 | 07-01 08:13:37.497 | android.log | 412 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.497   395   419 D NetlinkEvent: NL param 'DEVPATH=/devices/virtual/block/loop1' |
| 36 | 07-01 08:13:37.497 | android.log | 413 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.497   395   419 D NetlinkEvent: NL param 'SYNTH_UUID=0' |
| 37 | 07-01 08:13:37.498 | android.log | 414 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.498   395   419 D NetlinkEvent: NL param 'MAJOR=7' |
| 38 | 07-01 08:13:37.498 | android.log | 415 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.498   395   419 D NetlinkEvent: NL param 'MINOR=8' |
| 39 | 07-01 08:13:37.498 | android.log | 416 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.498   395   419 D NetlinkEvent: NL param 'DEVNAME=loop1' |
| 40 | 07-01 08:13:37.498 | android.log | 417 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.498   395   419 D NetlinkEvent: NL param 'DEVTYPE=disk' |
| 41 | 07-01 08:13:37.498 | android.log | 418 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.498   395   419 D NetlinkEvent: NL param 'DISKSEQ=117' |
| 42 | 07-01 08:13:37.498 | android.log | 420 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.498   395   419 D vold    : handleBlockEvent with action 1 |
| 43 | 07-01 08:13:37.498 | android.log | 421 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.498   395   419 D NetlinkEvent: NL param 'DEVPATH=/devices/virtual/block/loop29' |
| 44 | 07-01 08:13:37.498 | android.log | 422 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.498   395   419 D NetlinkEvent: NL param 'SYNTH_UUID=0' |
| 45 | 07-01 08:13:37.498 | android.log | 423 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.498   395   419 D NetlinkEvent: NL param 'MAJOR=7' |
| 46 | 07-01 08:13:37.498 | android.log | 424 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.498   395   419 D NetlinkEvent: NL param 'MINOR=232' |
| 47 | 07-01 08:13:37.498 | android.log | 425 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.498   395   419 D NetlinkEvent: NL param 'DEVNAME=loop29' |
| 48 | 07-01 08:13:37.498 | android.log | 426 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.498   395   419 D NetlinkEvent: NL param 'DEVTYPE=disk' |
| 49 | 07-01 08:13:37.498 | android.log | 427 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.498   395   419 D NetlinkEvent: NL param 'DISKSEQ=68' |
| 50 | 07-01 08:13:37.498 | android.log | 429 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.498   395   419 D vold    : handleBlockEvent with action 1 |
| 51 | 07-01 08:13:37.498 | android.log | 430 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.498   395   419 D NetlinkEvent: NL param 'DEVPATH=/devices/virtual/block/loop168' |
| 52 | 07-01 08:13:37.498 | android.log | 431 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.498   395   419 D NetlinkEvent: NL param 'SYNTH_UUID=0' |
| 53 | 07-01 08:13:37.498 | android.log | 432 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.498   395   419 D NetlinkEvent: NL param 'MAJOR=7' |
| 54 | 07-01 08:13:37.498 | android.log | 433 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.498   395   419 D NetlinkEvent: NL param 'MINOR=1344' |
| 55 | 07-01 08:13:37.498 | android.log | 414 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.498   395   419 D NetlinkEvent: NL param 'MAJOR=7' |
| 56 | 07-01 08:13:37.498 | android.log | 415 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.498   395   419 D NetlinkEvent: NL param 'MINOR=8' |
| 57 | 07-01 08:13:37.498 | android.log | 416 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.498   395   419 D NetlinkEvent: NL param 'DEVNAME=loop1' |
| 58 | 07-01 08:13:37.498 | android.log | 417 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.498   395   419 D NetlinkEvent: NL param 'DEVTYPE=disk' |
| 59 | 07-01 08:13:37.498 | android.log | 418 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.498   395   419 D NetlinkEvent: NL param 'DISKSEQ=117' |
| 60 | 07-01 08:13:37.498 | android.log | 420 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.498   395   419 D vold    : handleBlockEvent with action 1 |
| 61 | 07-01 08:13:37.498 | android.log | 421 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.498   395   419 D NetlinkEvent: NL param 'DEVPATH=/devices/virtual/block/loop29' |
| 62 | 07-01 08:13:37.498 | android.log | 422 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.498   395   419 D NetlinkEvent: NL param 'SYNTH_UUID=0' |
| 63 | 07-01 08:13:37.498 | android.log | 423 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.498   395   419 D NetlinkEvent: NL param 'MAJOR=7' |
| 64 | 07-01 08:13:37.498 | android.log | 424 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.498   395   419 D NetlinkEvent: NL param 'MINOR=232' |
| 65 | 07-01 08:13:37.498 | android.log | 425 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.498   395   419 D NetlinkEvent: NL param 'DEVNAME=loop29' |
| 66 | 07-01 08:13:37.498 | android.log | 426 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.498   395   419 D NetlinkEvent: NL param 'DEVTYPE=disk' |
| 67 | 07-01 08:13:37.498 | android.log | 427 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.498   395   419 D NetlinkEvent: NL param 'DISKSEQ=68' |
| 68 | 07-01 08:13:37.498 | android.log | 429 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.498   395   419 D vold    : handleBlockEvent with action 1 |
| 69 | 07-01 08:13:37.498 | android.log | 430 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.498   395   419 D NetlinkEvent: NL param 'DEVPATH=/devices/virtual/block/loop168' |
| 70 | 07-01 08:13:37.498 | android.log | 431 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.498   395   419 D NetlinkEvent: NL param 'SYNTH_UUID=0' |
| 71 | 07-01 08:13:37.498 | android.log | 432 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.498   395   419 D NetlinkEvent: NL param 'MAJOR=7' |
| 72 | 07-01 08:13:37.498 | android.log | 433 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.498   395   419 D NetlinkEvent: NL param 'MINOR=1344' |
| 73 | 07-01 08:13:37.499 | android.log | 434 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'DEVNAME=loop168' |
| 74 | 07-01 08:13:37.499 | android.log | 435 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'DEVTYPE=disk' |
| 75 | 07-01 08:13:37.499 | android.log | 436 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'DISKSEQ=121' |
| 76 | 07-01 08:13:37.499 | android.log | 438 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D vold    : handleBlockEvent with action 1 |
| 77 | 07-01 08:13:37.499 | android.log | 439 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'DEVPATH=/devices/virtual/block/dm-1' |
| 78 | 07-01 08:13:37.499 | android.log | 440 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'SYNTH_UUID=0' |
| 79 | 07-01 08:13:37.499 | android.log | 441 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'MAJOR=254' |
| 80 | 07-01 08:13:37.499 | android.log | 442 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'MINOR=1' |
| 81 | 07-01 08:13:37.499 | android.log | 443 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'DEVNAME=dm-1' |
| 82 | 07-01 08:13:37.499 | android.log | 444 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'DEVTYPE=disk' |
| 83 | 07-01 08:13:37.499 | android.log | 445 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'DISKSEQ=38' |
| 84 | 07-01 08:13:37.499 | android.log | 447 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D vold    : handleBlockEvent with action 1 |
| 85 | 07-01 08:13:37.499 | android.log | 448 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'DEVPATH=/devices/virtual/block/dm-49' |
| 86 | 07-01 08:13:37.499 | android.log | 449 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'SYNTH_UUID=0' |
| 87 | 07-01 08:13:37.499 | android.log | 450 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'MAJOR=254' |
| 88 | 07-01 08:13:37.499 | android.log | 451 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'MINOR=49' |
| 89 | 07-01 08:13:37.499 | android.log | 452 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'DEVNAME=dm-49' |
| 90 | 07-01 08:13:37.499 | android.log | 453 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'DEVTYPE=disk' |
| 91 | 07-01 08:13:37.499 | android.log | 454 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'DISKSEQ=111' |
| 92 | 07-01 08:13:37.499 | android.log | 456 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D vold    : handleBlockEvent with action 1 |
| 93 | 07-01 08:13:37.499 | android.log | 457 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'DEVPATH=/devices/virtual/block/dm-10' |
| 94 | 07-01 08:13:37.499 | android.log | 458 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'SYNTH_UUID=0' |
| 95 | 07-01 08:13:37.499 | android.log | 459 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'MAJOR=254' |
| 96 | 07-01 08:13:37.499 | android.log | 460 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'MINOR=10' |
| 97 | 07-01 08:13:37.499 | android.log | 461 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'DEVNAME=dm-10' |
| 98 | 07-01 08:13:37.499 | android.log | 462 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'DEVTYPE=disk' |
| 99 | 07-01 08:13:37.499 | android.log | 463 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'DISKSEQ=47' |
| 100 | 07-01 08:13:37.499 | android.log | 465 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D vold    : handleBlockEvent with action 1 |
| 101 | 07-01 08:13:37.499 | android.log | 466 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'DEVPATH=/devices/virtual/block/loop19' |
| 102 | 07-01 08:13:37.499 | android.log | 467 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'SYNTH_UUID=0' |
| 103 | 07-01 08:13:37.499 | android.log | 468 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'MAJOR=7' |
| 104 | 07-01 08:13:37.499 | android.log | 469 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'MINOR=152' |
| 105 | 07-01 08:13:37.499 | android.log | 470 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'DEVNAME=loop19' |
| 106 | 07-01 08:13:37.499 | android.log | 471 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'DEVTYPE=disk' |
| 107 | 07-01 08:13:37.499 | android.log | 472 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'DISKSEQ=58' |
| 108 | 07-01 08:13:37.499 | android.log | 474 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D vold    : handleBlockEvent with action 1 |
| 109 | 07-01 08:13:37.499 | android.log | 475 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'DEVPATH=/devices/virtual/block/dm-39' |
| 110 | 07-01 08:13:37.499 | android.log | 476 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'SYNTH_UUID=0' |
| 111 | 07-01 08:13:37.499 | android.log | 477 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'MAJOR=254' |
| 112 | 07-01 08:13:37.499 | android.log | 478 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'MINOR=39' |
| 113 | 07-01 08:13:37.499 | android.log | 479 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'DEVNAME=dm-39' |
| 114 | 07-01 08:13:37.499 | android.log | 480 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'DEVTYPE=disk' |
| 115 | 07-01 08:13:37.499 | android.log | 481 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'DISKSEQ=101' |
| 116 | 07-01 08:13:37.499 | android.log | 483 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D vold    : handleBlockEvent with action 1 |
| 117 | 07-01 08:13:37.499 | android.log | 484 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'DEVPATH=/devices/virtual/block/ram2' |
| 118 | 07-01 08:13:37.499 | android.log | 485 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'SYNTH_UUID=0' |
| 119 | 07-01 08:13:37.499 | android.log | 486 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'MAJOR=1' |
| 120 | 07-01 08:13:37.499 | android.log | 487 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'MINOR=2' |
| 121 | 07-01 08:13:37.499 | android.log | 488 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'DEVNAME=ram2' |
| 122 | 07-01 08:13:37.499 | android.log | 489 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'DEVTYPE=disk' |
| 123 | 07-01 08:13:37.499 | android.log | 490 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'DISKSEQ=3' |
| 124 | 07-01 08:13:37.499 | android.log | 492 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D vold    : handleBlockEvent with action 1 |
| 125 | 07-01 08:13:37.499 | android.log | 434 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'DEVNAME=loop168' |
| 126 | 07-01 08:13:37.499 | android.log | 435 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'DEVTYPE=disk' |
| 127 | 07-01 08:13:37.499 | android.log | 436 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'DISKSEQ=121' |
| 128 | 07-01 08:13:37.499 | android.log | 438 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D vold    : handleBlockEvent with action 1 |
| 129 | 07-01 08:13:37.499 | android.log | 439 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'DEVPATH=/devices/virtual/block/dm-1' |
| 130 | 07-01 08:13:37.499 | android.log | 440 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'SYNTH_UUID=0' |
| 131 | 07-01 08:13:37.499 | android.log | 441 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'MAJOR=254' |
| 132 | 07-01 08:13:37.499 | android.log | 442 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'MINOR=1' |
| 133 | 07-01 08:13:37.499 | android.log | 443 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'DEVNAME=dm-1' |
| 134 | 07-01 08:13:37.499 | android.log | 444 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'DEVTYPE=disk' |
| 135 | 07-01 08:13:37.499 | android.log | 445 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'DISKSEQ=38' |
| 136 | 07-01 08:13:37.499 | android.log | 447 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D vold    : handleBlockEvent with action 1 |
| 137 | 07-01 08:13:37.499 | android.log | 448 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'DEVPATH=/devices/virtual/block/dm-49' |
| 138 | 07-01 08:13:37.499 | android.log | 449 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'SYNTH_UUID=0' |
| 139 | 07-01 08:13:37.499 | android.log | 450 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'MAJOR=254' |
| 140 | 07-01 08:13:37.499 | android.log | 451 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'MINOR=49' |
| 141 | 07-01 08:13:37.499 | android.log | 452 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'DEVNAME=dm-49' |
| 142 | 07-01 08:13:37.499 | android.log | 453 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'DEVTYPE=disk' |
| 143 | 07-01 08:13:37.499 | android.log | 454 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'DISKSEQ=111' |
| 144 | 07-01 08:13:37.499 | android.log | 456 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D vold    : handleBlockEvent with action 1 |
| 145 | 07-01 08:13:37.499 | android.log | 457 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'DEVPATH=/devices/virtual/block/dm-10' |
| 146 | 07-01 08:13:37.499 | android.log | 458 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'SYNTH_UUID=0' |
| 147 | 07-01 08:13:37.499 | android.log | 459 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'MAJOR=254' |
| 148 | 07-01 08:13:37.499 | android.log | 460 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'MINOR=10' |
| 149 | 07-01 08:13:37.499 | android.log | 461 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'DEVNAME=dm-10' |
| 150 | 07-01 08:13:37.499 | android.log | 462 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'DEVTYPE=disk' |
| 151 | 07-01 08:13:37.499 | android.log | 463 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'DISKSEQ=47' |
| 152 | 07-01 08:13:37.499 | android.log | 465 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D vold    : handleBlockEvent with action 1 |
| 153 | 07-01 08:13:37.499 | android.log | 466 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'DEVPATH=/devices/virtual/block/loop19' |
| 154 | 07-01 08:13:37.499 | android.log | 467 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'SYNTH_UUID=0' |
| 155 | 07-01 08:13:37.499 | android.log | 468 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'MAJOR=7' |
| 156 | 07-01 08:13:37.499 | android.log | 469 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'MINOR=152' |
| 157 | 07-01 08:13:37.499 | android.log | 470 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'DEVNAME=loop19' |
| 158 | 07-01 08:13:37.499 | android.log | 471 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'DEVTYPE=disk' |
| 159 | 07-01 08:13:37.499 | android.log | 472 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'DISKSEQ=58' |
| 160 | 07-01 08:13:37.499 | android.log | 474 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D vold    : handleBlockEvent with action 1 |
| 161 | 07-01 08:13:37.499 | android.log | 475 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'DEVPATH=/devices/virtual/block/dm-39' |
| 162 | 07-01 08:13:37.499 | android.log | 476 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'SYNTH_UUID=0' |
| 163 | 07-01 08:13:37.499 | android.log | 477 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'MAJOR=254' |
| 164 | 07-01 08:13:37.499 | android.log | 478 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'MINOR=39' |
| 165 | 07-01 08:13:37.499 | android.log | 479 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'DEVNAME=dm-39' |
| 166 | 07-01 08:13:37.499 | android.log | 480 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'DEVTYPE=disk' |
| 167 | 07-01 08:13:37.499 | android.log | 481 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'DISKSEQ=101' |
| 168 | 07-01 08:13:37.499 | android.log | 483 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D vold    : handleBlockEvent with action 1 |
| 169 | 07-01 08:13:37.499 | android.log | 484 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'DEVPATH=/devices/virtual/block/ram2' |
| 170 | 07-01 08:13:37.499 | android.log | 485 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'SYNTH_UUID=0' |
| 171 | 07-01 08:13:37.499 | android.log | 486 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'MAJOR=1' |
| 172 | 07-01 08:13:37.499 | android.log | 487 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'MINOR=2' |
| 173 | 07-01 08:13:37.499 | android.log | 488 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'DEVNAME=ram2' |
| 174 | 07-01 08:13:37.499 | android.log | 489 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'DEVTYPE=disk' |
| 175 | 07-01 08:13:37.499 | android.log | 490 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D NetlinkEvent: NL param 'DISKSEQ=3' |
| 176 | 07-01 08:13:37.499 | android.log | 492 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.499   395   419 D vold    : handleBlockEvent with action 1 |
| 177 | 07-01 08:13:37.500 | android.log | 493 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.500   395   419 D NetlinkEvent: NL param 'DEVPATH=/devices/virtual/block/dm-29' |
| 178 | 07-01 08:13:37.500 | android.log | 494 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.500   395   419 D NetlinkEvent: NL param 'SYNTH_UUID=0' |
| 179 | 07-01 08:13:37.500 | android.log | 495 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.500   395   419 D NetlinkEvent: NL param 'MAJOR=254' |
| 180 | 07-01 08:13:37.500 | android.log | 496 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.500   395   419 D NetlinkEvent: NL param 'MINOR=29' |
| 181 | 07-01 08:13:37.500 | android.log | 497 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.500   395   419 D NetlinkEvent: NL param 'DEVNAME=dm-29' |
| 182 | 07-01 08:13:37.500 | android.log | 498 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.500   395   419 D NetlinkEvent: NL param 'DEVTYPE=disk' |
| 183 | 07-01 08:13:37.500 | android.log | 499 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.500   395   419 D NetlinkEvent: NL param 'DISKSEQ=91' |
| 184 | 07-01 08:13:37.500 | android.log | 501 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.500   395   419 D vold    : handleBlockEvent with action 1 |
| 185 | 07-01 08:13:37.500 | android.log | 502 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.500   395   419 D NetlinkEvent: NL param 'DEVPATH=/devices/virtual/block/loop37' |
| 186 | 07-01 08:13:37.500 | android.log | 503 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.500   395   419 D NetlinkEvent: NL param 'SYNTH_UUID=0' |
| 187 | 07-01 08:13:37.500 | android.log | 504 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.500   395   419 D NetlinkEvent: NL param 'MAJOR=7' |
| 188 | 07-01 08:13:37.500 | android.log | 505 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.500   395   419 D NetlinkEvent: NL param 'MINOR=296' |
| 189 | 07-01 08:13:37.500 | android.log | 506 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.500   395   419 D NetlinkEvent: NL param 'DEVNAME=loop37' |
| 190 | 07-01 08:13:37.500 | android.log | 507 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.500   395   419 D NetlinkEvent: NL param 'DEVTYPE=disk' |
| 191 | 07-01 08:13:37.500 | android.log | 508 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.500   395   419 D NetlinkEvent: NL param 'DISKSEQ=76' |
| 192 | 07-01 08:13:37.500 | android.log | 493 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.500   395   419 D NetlinkEvent: NL param 'DEVPATH=/devices/virtual/block/dm-29' |
| 193 | 07-01 08:13:37.500 | android.log | 494 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.500   395   419 D NetlinkEvent: NL param 'SYNTH_UUID=0' |
| 194 | 07-01 08:13:37.500 | android.log | 495 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.500   395   419 D NetlinkEvent: NL param 'MAJOR=254' |
| 195 | 07-01 08:13:37.500 | android.log | 496 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.500   395   419 D NetlinkEvent: NL param 'MINOR=29' |
| 196 | 07-01 08:13:37.500 | android.log | 497 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.500   395   419 D NetlinkEvent: NL param 'DEVNAME=dm-29' |
| 197 | 07-01 08:13:37.500 | android.log | 498 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.500   395   419 D NetlinkEvent: NL param 'DEVTYPE=disk' |
| 198 | 07-01 08:13:37.500 | android.log | 499 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.500   395   419 D NetlinkEvent: NL param 'DISKSEQ=91' |
| 199 | 07-01 08:13:37.500 | android.log | 501 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.500   395   419 D vold    : handleBlockEvent with action 1 |
| 200 | 07-01 08:13:37.500 | android.log | 502 | event | CC检测与PD通信时序配合 | 07-01 08:13:37.500   395   419 D NetlinkEvent: NL param 'DEVPATH=/devices/virtual/block/loop37' |
