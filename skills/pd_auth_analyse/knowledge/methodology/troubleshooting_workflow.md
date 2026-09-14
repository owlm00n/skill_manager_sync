# PD认证问题 — 排查工作流

## 第1步: 确认CC检测状态
```
查看kernel log中Type-C CC检测日志:
  sc27xx-typec: now works as DRP and is in X state, event Y
  → 确认CC1/CC2引脚检测值与实际连接方式一致
  → 若CC未检测到，检查PMIC Type-C中断注册、GPIO配置
```

## 第2步: 确认PD消息收发
```
抓取PD协议分析仪(Lecroy/M310e) trace:
  → 检查SourceCap/SinkCap/Request/PS_RDY消息序列
  → 验证tTypeCSendSourceCap等时序参数
  → 确认GoodCRC是否正确回复
```

## 第3步: PD Controller IC驱动检查
```
查看I2C probe日志 + TCPCI寄存器:
  → 确认PD IC detect/probe成功
  → 检查tcpci_transmit/tcpci_read/tcpci_write日志
  → 验证TCPCI Alert中断处理是否及时
```

## 第4步: BC1.2干扰排查
```
  → 确认BC1.2检测与PD通信的时序关系
  → 检查vbos_ok_work delay是否合理
  → 尝试禁用BC1.2检测验证是否改善
```

## 第5步: 认证Patch版本比对
```
  → Gerrit搜索认证相关提交: typec认证 / pd认证 / 欧代认证
  → 比对认证实验室提供的测试脚本版本
  → 确认patch合入完整且无冲突
```

## 日志抓取关键字
```
kernel log: sc27xx-typec|sprd_tcpm|tcpci|cc1|cc2|pd_notify
PD trace:   Lecroy/M310e协议分析仪 .usb trace文件
I2C:        /sys/bus/i2c/devices/*/ 下PD IC节点
charger:    sgm41512_set_vinlimit|musb_gadget_vbus_draw|charger_manager
```
