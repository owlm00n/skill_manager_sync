#!/usr/bin/env python3
"""
渐进式协议日志提取器 v2.0 - Progressive Protocol Log Extractor

v2.0 增强:
  - 双重索引排序 (kernel_ts + CPU + thread)
  - Pending/Delayed 状态变更合并与回链
  - PD Header 确定性解码 (hex → 消息类型/角色/数据对象数)
  - PDO/RDO 确定性解析
  - TCPM 状态机追踪
  - Hard Reset 阶段分组
  - PD 协商周期分组
  - 异常检测
  - 结构化 JSON 输出 (符合 extraction_output.schema.json)

输出: schema-compliant JSON with timeline + groups + anomalies
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

# ============================================================
# PD Protocol Constants
# ============================================================

# PD Message Type (bits 0-3 of header)
PD_MESSAGE_TYPES: dict[int, str] = {
    0x0: "RESERVED",
    0x1: "SOURCE_CAPABILITIES",
    0x2: "REQUEST",
    0x3: "BIST",
    0x4: "SINK_CAPABILITIES",
    0x5: "BATTERY_STATUS",
    0x6: "ALERT",
    0x7: "GET_COUNTRY_INFO",
    0x8: "ENTER_USB",
    0x9: "VDM",
    0xA: "UNSTRUCTURED_VDM",
    0xF: "VENDOR_DEFINED",
}

# PD Control Message Type — bits 0-4 of header, resolved when NDO==0
# Source: USB PD 3.1 spec Table 6-5 + Spreadtrum kernel SPRD_PD_CTRL_* macros
PD_CONTROL_TYPES: dict[int, str] = {
    0x00: "RESERVED",
    0x01: "GOOD_CRC",
    0x02: "GOTO_MIN",
    0x03: "ACCEPT",
    0x04: "REJECT",
    0x05: "PING",
    0x06: "PS_RDY",
    0x07: "GET_SOURCE_CAP",
    0x08: "GET_SINK_CAP",
    0x09: "DR_SWAP",
    0x0A: "PR_SWAP",
    0x0B: "VCONN_SWAP",
    0x0C: "WAIT",
    0x0D: "SOFT_RESET",
    0x0E: "DATA_RESET",
    0x0F: "DATA_RESET_COMPLETE",
    0x10: "NOT_SUPPORTED",       # Spreadtrum: SPRD_PD_CTRL_NOT_SUPP
    0x11: "GET_SOURCE_CAP_EXT",
    0x12: "GET_STATUS",
    0x13: "FR_SWAP",
    0x14: "GET_PPS_STATUS",
    0x15: "GET_COUNTRY_CODES",
    0x16: "GET_SINK_CAP_EXT",
    0x17: "GET_SOURCE_INFO",
    0x18: "GET_REVISION",
}

# PD Extended Message Type
PD_EXTENDED_TYPES: dict[int, str] = {
    0x0: "RESERVED",
    0x1: "SOURCE_CAPABILITIES_EXT",
    0x2: "STATUS",
    0x3: "GET_BATTERY_CAP",
    0x4: "GET_BATTERY_STATUS",
    0x5: "BATTERY_CAPABILITIES",
    0x6: "GET_MANUFACTURER_INFO",
    0x7: "MANUFACTURER_INFO",
    0x8: "SECURITY_REQUEST",
    0x9: "SECURITY_RESPONSE",
    0xA: "FIRMWARE_UPDATE_REQUEST",
    0xB: "FIRMWARE_UPDATE_RESPONSE",
    0xC: "PPS_STATUS",
    0xD: "COUNTRY_INFO",
    0xE: "COUNTRY_CODES",
    0xF: "SINK_CAPABILITIES_EXT",
}

# Spec Revision (bits 6-7 of header)
SPEC_REV: dict[int, str] = {
    0b00: "REV1.0",
    0b01: "REV2.0",
    0b10: "REV3.0",
    0b11: "RESERVED",
}

# PDO Type (bits 30-31 of 32-bit PDO)
PDO_TYPES: dict[int, str] = {
    0: "fixed",
    1: "battery",
    2: "variable",
    3: "apdo",
}

# SPRD TCPM state machine states (all observed states in sprd_tcpm_log)
TCPM_STATES: set[str] = {
    "TOGGLING",
    "SNK_ATTACH_WAIT", "SNK_DEBOUNCED", "SNK_ATTACHED",
    "SNK_STARTUP", "SNK_DISCOVERY", "SNK_WAIT_CAPABILITIES",
    "SNK_NEGOTIATE_CAPABILITIES", "SNK_TRANSITION_SINK",
    "SNK_READY", "SNK_UNATTACHED",
    "SRC_ATTACHED", "SRC_ATTACH_WAIT", "SRC_STARTUP",
    "SRC_DISCOVERY", "SRC_SEND_CAPABILITIES", "SRC_NEGOTIATE_CAPABILITIES",
    "SRC_TRANSITION_SUPPLY", "SRC_READY", "SRC_UNATTACHED",
    "HARD_RESET_SEND", "HARD_RESET_START",
    "SNK_HARD_RESET_SINK_OFF", "SNK_HARD_RESET_SINK_ON",
    "SOFT_RESET_SEND", "SOFT_RESET",
    "ERROR_RECOVERY",
}

# ============================================================
# Level 0: 特定格式提取器
# ============================================================

SPECIFIC_FORMATS = {
    "sprd_tcpm": {
        "patterns": [r"\[sprd_tcpm_log\]", r"\[sprd_pd_log\]", r"\[sc27xx-typec-pd[^\]]*\]"],
        "label": "展锐 SC27XX TCPM/PD",
        "min_hits": 5,
    },
    "generic_pd": {
        "patterns": [r"\[pd_protocol\]", r"\[pd_controller\]", r"\[pd_phy\]"],
        "label": "通用 PD Protocol",
        "min_hits": 3,
    },
    "generic_usb": {
        "patterns": [r"\[usb_core\]", r"\[usb_host\]", r"\[dwc3\]", r"\[xhci\]"],
        "label": "通用 USB Core",
        "min_hits": 3,
    },
    "generic_cc": {
        "patterns": [r"\[cc_protocol\]", r"\[cc_logic\]", r"\[cc_state\]"],
        "label": "通用 CC Protocol",
        "min_hits": 3,
    },
    "qcom_pd": {
        "patterns": [r"\[pmic_pd\]", r"\[qcom_pd\]", r"\[qpnp_pd\]", r"\[smb.*pd\]"],
        "label": "高通 PMIC PD",
        "min_hits": 3,
    },
    "mtk_tcpc": {
        "patterns": [r"\[mtk_tcpc\]", r"\[mtk_pd\]", r"\[mt6360\]", r"\[mt6370\]"],
        "label": "MTK TCPC",
        "min_hits": 3,
    },
    "fusb": {
        "patterns": [r"\[fusb302\]", r"\[fusb\]", r"\[tcpci\]"],
        "label": "FUSB302/TCPCI",
        "min_hits": 3,
    },
}

# ============================================================
# Level 1: 协议关键词（中置信度）
# ============================================================

PROTOCOL_KEYWORDS = [
    "SRC_CAP", "SNK_CAP", "SOURCE_CAP", "SINK_CAP",
    "PS_RDY", "PR_SWAP", "DR_SWAP", "FR_SWAP", "VCONN_SWAP",
    "HARD_RESET", "SOFT_RESET",
    "GET_SOURCE_CAP", "GET_SINK_CAP",
    "VDM", "VENDOR_DEFINED", "Discover Identity",
    "BIST", "PING", "WAIT",
    "PD TX", "PD RX", "PD_MSG",
    "PDO 0:", "PDO 1:", "PDO 2:", "PDO 3:", "PDO 4:", "PDO 5:",
    "APDO", "RDO",
    "pd_capable", "pd_connect", "pd_negotiation",
    "SNK_READY", "SNK_UNATTACHED", "SNK_ATTACHED",
    "SRC_READY", "SRC_UNATTACHED", "SRC_ATTACHED",
    "TOGGLING", "ATTACH_WAIT", "DEBOUNCED",
    "WAIT_CAPABILITIES", "NEGOTIATE_CAPABILITIES",
    "TRANSITION_SINK", "SNK_STARTUP", "SNK_DISCOVERY",
    "CC1:", "CC2:", "CC1 =", "CC2 =",
    "Rp=", "Rd=", "VCONN",
    "polarity", "current_capability", "get_rp_limit",
    "GET_DESCRIPTOR", "SET_ADDRESS", "SET_CONFIGURATION",
    "Device Descriptor", "Config Descriptor",
    "idVendor", "idProduct", "bcdUSB",
    "bDeviceClass", "bNumConfigurations",
    "enumeration", "enumerate",
    "header: 0x", "header = 0x", "msg header = 0x",
    "PD RX, header", "PD TX, header",
]

FALLBACK_KEYWORDS = [
    "charger", "charging", "charge",
    "battery", "batt", "VBUS", "vbus",
    "vbus_present", "vbus_online",
    "Setting voltage", "voltage/current limit",
    "typec", "type_c", "TYPE_C", "Type-C",
    "CC", "cc_state", "cc_protocol",
    "usb_core", "USB", "musb", "dwc3",
    "5000 mV", "9000 mV", "12000 mV", "15000 mV", "20000 mV",
    "5V", "9V", "12V", "15V", "20V",
    "3000 mA", "5000 mA",
    "timeout", "Timeout", "TIMEOUT",
    "retransmit", "Retransmit",
    "FAILED", "failed",
    "deadlock", "DEADLOCK",
    "hard reset loop", "Hard Reset loop",
    "debounce fail", "debounce timeout",
]

# ============================================================
# Regex patterns for log line parsing
# ============================================================

# Full sprd log line pattern (with sequence + inner timestamp)
RE_SPRD_FULL = re.compile(
    r'^[0-9A-Fa-f]+\s+< *\d+>\s*'          # prefix + log level
    r'\[\s*([\d.]+)\s*\]\s*'              # kernel_ts (outer)
    r'\[[\d\-:\s.]+\]\s*'                 # wall clock (skip, extracted separately)
    r'T(\d+)@C(\d+);\s*'                  # thread, cpu
    r'\[(\d+)\s*/\s*(\d+)\]\s*'          # seq_current / seq_total
    r'\[\s*([\d.]+)\s*\]\s*'             # inner_ts
    r'\[([^\]]+)\]\s*'                    # subsystem tag
    r'(.*)'                               # message content
)

# Simpler sprd log line (thread@cpu;message - no sequence)
RE_SPRD_SIMPLE = re.compile(
    r'^[0-9A-Fa-f]+\s+< *\d+>\s*'
    r'\[\s*([\d.]+)\s*\]\s*'
    r'\[[\d\-:\s.]+\]\s*'
    r'T(\d+)@C(\d+);\s*'
    r'(.*)'
)

# Wall clock extractor
RE_WALL_CLOCK = re.compile(r'\[(\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+)\]')

# Subsystem tag extractor (for simple lines)
RE_SUBSYSTEM = re.compile(r'\[([^\]]+)\]:?\s*(.*)')

# ============================================================
# Dataclasses
# ============================================================

@dataclass
class PdHeaderDecoded:
    """Decoded PD message header fields."""
    raw_hex: str = ""
    message_type: str = ""
    message_type_hex: str = ""
    spec_revision: str = ""
    port_power_role: str = ""
    port_data_role: str = ""
    number_of_data_objects: int = 0
    message_id: int = 0
    cable_plug: str = ""
    extended: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PdoEntry:
    """Decoded Power Data Object."""
    index: int = 0
    type: str = ""
    type_code: int = 0
    voltage_mv: int = 0
    current_ma: int = 0
    flags: list[str] = field(default_factory=list)
    raw_hex: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RdoDecoded:
    """Decoded Request Data Object."""
    object_position: int = 0
    operating_current_ma: int = 0
    max_current_ma: int = 0
    raw_hex: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CcInfo:
    """CC line state info."""
    cc1: int = 0
    cc2: int = 0
    cc1_from: int = 0
    cc1_to: int = 0
    cc2_from: int = 0
    cc2_to: int = 0
    state: str = ""
    polarity: int = 0
    connection_status: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None and v != "" and v != 0}


@dataclass
class ChargerInfo:
    """Charger manager info."""
    chgr_type: int = 0
    fchg_en: int = 0
    cp_running: int = 0
    max_chg_lmt_cur_ua: int = 0
    max_inpt_lmt_cur_ua: int = 0
    max_chg_volt_uv: int = 0
    adapter_chg_volt_mv: int = 0

    def to_dict(self) -> dict:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None and v != "" and v != 0}


@dataclass
class TimelineEvent:
    """Single event in the extraction timeline."""
    id: int = 0
    seq: str = ""
    kernel_ts: float = 0.0
    wall_clock: str = ""
    cpu: int = 0
    thread: str = ""
    subsystem: str = ""
    event_type: str = "other"
    content_raw: str = ""

    # State change fields
    state_from: str = ""
    state_to: str = ""
    delay_ms: int = 0
    is_pending: bool = False
    is_delayed: bool = False
    pending_target_event_id: int = 0

    # Decoded fields
    decoded: Optional[dict] = None
    charger_info: Optional[dict] = None
    cc_info: Optional[dict] = None
    voltage_mv: int = 0
    current_ma: int = 0

    # Flags
    flags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = {
            "id": self.id,
            "seq": self.seq,
            "kernel_ts": self.kernel_ts,
            "wall_clock": self.wall_clock,
            "cpu": self.cpu,
            "thread": self.thread,
            "subsystem": self.subsystem,
            "event_type": self.event_type,
            "content_raw": self.content_raw,
        }
        if self.state_from:
            d["state_from"] = self.state_from
        if self.state_to:
            d["state_to"] = self.state_to
        if self.delay_ms:
            d["delay_ms"] = self.delay_ms
        if self.is_pending:
            d["is_pending"] = True
        if self.is_delayed:
            d["is_delayed"] = True
        if self.pending_target_event_id:
            d["pending_target_event_id"] = self.pending_target_event_id
        if self.decoded:
            d["decoded"] = self.decoded
        if self.charger_info:
            d["charger_info"] = self.charger_info
        if self.cc_info:
            d["cc_info"] = self.cc_info
        if self.voltage_mv:
            d["voltage_mv"] = self.voltage_mv
        if self.current_ma:
            d["current_ma"] = self.current_ma
        if self.flags:
            d["flags"] = self.flags
        return d


# ============================================================
# PD Header Decoder (deterministic, no AI needed)
# ============================================================

def decode_pd_header(header_hex: str) -> PdHeaderDecoded:
    """
    Deterministically decode a PD message header from hex.

    Spreadtrum/SC2730 PHY header format (16 bits, matches USB PD spec):
      Bits 0-4:   Message Type (5 bits)
      Bit 5:      Port Data Role (0=UFP, 1=DFP/Host)
      Bits 6-7:   Specification Revision (0=Rev1.0, 1=Rev2.0, 2=Rev3.0)
      Bit 8:      Port Power Role (0=SINK, 1=SOURCE)
      Bits 9-11:  Message ID (3 bits, 0-7)
      Bits 12-14: Number of Data Objects (3 bits, 0-7)
                   0 = Control Message, >0 = Data Message
      Bit 15:     Extended Header flag

    Key disambiguation: NDO==0 → control message, NDO>0 → data message.
    e.g. type=3 with NDO=0 → ACCEPT, type=3 with NDO>0 → BIST
         type=6 with NDO=0 → PS_RDY, type=6 with NDO>0 → ALERT
    """
    result = PdHeaderDecoded(raw_hex=header_hex)

    try:
        if header_hex.startswith("0x") or header_hex.startswith("0X"):
            hdr = int(header_hex, 16)
        else:
            hdr = int(header_hex, 16)

        type_code = hdr & 0x1F         # bits 0-4: Message Type (5 bits)
        port_data_role_bit = (hdr >> 5) & 0x1  # bit 5: Data Role
        spec_rev = (hdr >> 6) & 0x3     # bits 6-7: Spec Revision
        port_power_role_bit = (hdr >> 8) & 0x1  # bit 8: Power Role
        msg_id = (hdr >> 9) & 0x7       # bits 9-11: Message ID
        ndo = (hdr >> 12) & 0x7         # bits 12-14: Number of Data Objects
        extended = bool(hdr & 0x8000)   # bit 15: Extended

        result.message_type_hex = f"0x{type_code:X}"
        result.number_of_data_objects = ndo
        result.message_id = msg_id
        result.extended = extended

        # Disambiguate: NDO==0 → control, NDO>0 → data
        if ndo == 0:
            result.message_type = PD_CONTROL_TYPES.get(type_code, f"CTRL_0x{type_code:02X}")
        else:
            result.message_type = PD_MESSAGE_TYPES.get(type_code, f"DATA_0x{type_code:02X}")

        if extended:
            # Extended messages use bits 4-8 (5 bits) for extended type
            ext_type = (hdr >> 4) & 0x1F
            result.message_type = PD_EXTENDED_TYPES.get(ext_type, f"EXT_0x{ext_type:X}")

        # Port Data Role (bit 5)
        result.port_data_role = "DFP" if port_data_role_bit else "UFP"

        # Spec Revision (bits 6-7)
        result.spec_revision = SPEC_REV.get(spec_rev, f"REV_UNKNOWN_{spec_rev}")

        # Port Power Role (bit 8)
        result.port_power_role = "SOURCE" if port_power_role_bit else "SINK"

    except (ValueError, IndexError):
        pass

    return result


def decode_pdo(pdo_hex: str, index: int = 0) -> PdoEntry:
    """
    Deterministically decode a 32-bit PDO from hex.

    Fixed PDO (type=0):
      Bits 0-9:   Max Current in 10mA units
      Bits 10-19: Voltage in 50mV units
      Bits 20-29: Reserved
      Bits 30-31: PDO Type (0=fixed)

    APDO (type=3):
      Bits 0-6:   Max Current in 50mA units
      Bits 7-7:   Reserved
      Bits 8-15:  Minimum Voltage in 100mV units
      Bits 16-24: Maximum Voltage in 100mV units
      Bits 30-31: PDO Type (3=APDO)
    """
    entry = PdoEntry(index=index, raw_hex=pdo_hex)

    try:
        if pdo_hex.startswith("0x") or pdo_hex.startswith("0X"):
            val = int(pdo_hex, 16)
        else:
            val = int(pdo_hex, 16)

        pdo_type = (val >> 30) & 0x3
        entry.type_code = pdo_type
        entry.type = PDO_TYPES.get(pdo_type, f"unknown_{pdo_type}")

        if pdo_type == 0:  # Fixed PDO
            max_current = (val & 0x3FF) * 10
            voltage = ((val >> 10) & 0x3FF) * 50
            entry.current_ma = max_current
            entry.voltage_mv = voltage

            # Flags
            if val & (1 << 26):
                entry.flags.append("DRP")
            if val & (1 << 27):
                entry.flags.append("USB_COMM_CAPABLE")
            if val & (1 << 28):
                entry.flags.append("DUAL_ROLE_DATA")
            if val & (1 << 29):
                entry.flags.append("UNCONSTRAINED_POWER")

        elif pdo_type == 1:  # Battery PDO
            max_power = (val & 0x3FF) * 250
            voltage = ((val >> 10) & 0x3FF) * 50
            entry.current_ma = max_power
            entry.voltage_mv = voltage

        elif pdo_type == 2:  # Variable PDO
            max_current = (val & 0x3FF) * 10
            voltage_min = ((val >> 10) & 0x3FF) * 50
            voltage_max = ((val >> 20) & 0x3FF) * 50
            entry.current_ma = max_current
            entry.voltage_mv = voltage_max

        elif pdo_type == 3:  # APDO (Augmented PDO, including PPS)
            max_current = (val & 0x7F) * 50
            voltage_min = ((val >> 8) & 0xFF) * 100
            voltage_max = ((val >> 16) & 0x1FF) * 100
            entry.current_ma = max_current
            entry.voltage_mv = voltage_max

            # Check if PPS (Programmable Power Supply)
            if (val >> 28) & 0x1:
                entry.type = "pps"
                entry.flags.append("PPS")

    except (ValueError, IndexError):
        pass

    return entry


def decode_rdo(rdo_hex: str) -> RdoDecoded:
    """
    Deterministically decode a 32-bit RDO from hex.

    Fixed PDO Request:
      Bits 0-9:   Max/Min Operating Current in 10mA units
      Bits 10-19: Operating Current in 10mA units
      Bits 20-27: Reserved
      Bits 28-30: Object Position (1-based)
      Bit 31:     Reserved
    """
    result = RdoDecoded(raw_hex=rdo_hex)

    try:
        if rdo_hex.startswith("0x") or rdo_hex.startswith("0X"):
            val = int(rdo_hex, 16)
        else:
            val = int(rdo_hex, 16)

        result.object_position = ((val >> 28) & 0x7) + 1
        result.operating_current_ma = ((val >> 10) & 0x3FF) * 10
        result.max_current_ma = (val & 0x3FF) * 10

    except (ValueError, IndexError):
        pass

    return result


# ============================================================
# Line Parser: raw log line → TimelineEvent
# ============================================================

def parse_sprd_line(line: str) -> Optional[TimelineEvent]:
    """Parse a single sprd-format log line into a TimelineEvent."""
    event = TimelineEvent()

    # Try full format first (with sequence numbers)
    m = RE_SPRD_FULL.match(line)
    if m:
        event.kernel_ts = float(m.group(1))
        event.thread = m.group(2)
        event.cpu = int(m.group(3))
        event.seq = f"{m.group(4)} / {m.group(5)}"
        inner_ts = float(m.group(6))
        subsystem_tag = m.group(7)
        message = m.group(8)
    else:
        # Try simple format
        m = RE_SPRD_SIMPLE.match(line)
        if not m:
            return None
        event.kernel_ts = float(m.group(1))
        event.thread = m.group(2)
        event.cpu = int(m.group(3))
        raw_rest = m.group(4)

        # Try to extract subsystem tag from the rest
        sm = RE_SUBSYSTEM.match(raw_rest)
        if sm and ("sprd_tcpm" in sm.group(1) or "sprd_pd" in sm.group(1)
                   or "sc27xx" in sm.group(1) or "charger-manager" in sm.group(1)
                   or "bc1p2" in sm.group(1) or "sprd-fgu" in sm.group(1)
                   or "bq2560" in sm.group(1) or "musb" in sm.group(1)
                   or "HealthLoop" in sm.group(1) or "healthd" in sm.group(1)
                   or "sprd_bcl" in sm.group(1)):
            subsystem_tag = sm.group(1)
            message = sm.group(2)
        else:
            subsystem_tag = "unknown"
            message = raw_rest

    # Map subsystem tag to canonical name
    if "sprd_tcpm_log" in subsystem_tag:
        event.subsystem = "sprd_tcpm_log"
    elif "sprd_pd_log" in subsystem_tag:
        event.subsystem = "sprd_pd_log"
    elif "charger-manager" in subsystem_tag:
        event.subsystem = "charger-manager"
    elif "sc27xx-typec-pd" in subsystem_tag:
        event.subsystem = "sc27xx-typec-pd"
    elif "sc27xx-typec" in subsystem_tag:
        event.subsystem = "sc27xx-typec"
    elif "healthd" in subsystem_tag or "HealthLoop" in subsystem_tag:
        event.subsystem = "healthd"
    else:
        event.subsystem = "other"

    event.content_raw = message.strip()

    # Extract wall clock
    wm = RE_WALL_CLOCK.search(line)
    if wm:
        event.wall_clock = wm.group(1)

    # Determine event type and extract structured fields
    _classify_event(event)

    return event


def _classify_event(event: TimelineEvent) -> None:
    """Classify event type and extract structured fields from content_raw."""
    msg = event.content_raw

    # --- State changes (highest priority classification) ---

    # Delayed state change: "state change X -> Y [delayed N ms]"
    m = re.search(r'state change\s+(\S+)\s*->\s*(\S+)\s*\[delayed\s+(\d+)', msg)
    if m:
        event.event_type = "delayed_state_change"
        event.state_from = m.group(1)
        event.state_to = m.group(2)
        event.delay_ms = int(m.group(3))
        event.is_delayed = True
        event.flags.append("DELAYED_TRIGGER")
        return

    # Pending state change: "pending state change X -> Y @ N ms"
    m = re.search(r'pending state change\s+(\S+)\s*->\s*(\S+)\s*@\s*(\d+)', msg)
    if m:
        event.event_type = "pending_state_change"
        event.state_from = m.group(1)
        event.state_to = m.group(2)
        event.delay_ms = int(m.group(3))
        event.is_pending = True
        event.flags.append("PENDING_ACTIVE")
        return

    # State change: "state change X -> Y"
    m = re.search(r'state change\s+(\S+)\s*->\s*(\S+)', msg)
    if m:
        event.event_type = "state_change"
        event.state_from = m.group(1)
        event.state_to = m.group(2)
        return

    # Start toggling
    if "Start toggling" in msg:
        event.event_type = "toggling"
        return

    # sprd_tcpm_reset_port
    if "sprd_tcpm_reset_port" in msg:
        event.event_type = "reset_port"
        return

    # --- PD RX/TX messages ---

    # PD RX with data objects: "PD RX, header: 0xXXXX [N][role]"
    m = re.search(r'PD RX, header:\s*(0x[0-9A-Fa-f]+)\s*\[(\d+)\]\[(\w+)\]', msg)
    if m:
        event.event_type = "pd_rx"
        header_raw = m.group(1)
        decoded = decode_pd_header(header_raw)
        event.decoded = {
            "pd_header_raw": header_raw,
            "pd_header_decoded": decoded.to_dict(),
        }
        event.flags.append("KEY_EVENT")
        return

    # PD RX (compact): "PD RX, header: 0xXXXX [N][role]" already matched above
    # Fallback: just "PD RX, header: 0xXXXX"
    m = re.search(r'PD RX, header:\s*(0x[0-9A-Fa-f]+)', msg)
    if m:
        event.event_type = "pd_rx"
        header_raw = m.group(1)
        decoded = decode_pd_header(header_raw)
        event.decoded = {
            "pd_header_raw": header_raw,
            "pd_header_decoded": decoded.to_dict(),
        }
        event.flags.append("KEY_EVENT")
        return

    # PD TX: "PD TX, header: 0xXXXX"
    m = re.search(r'PD TX, header:\s*(0x[0-9A-Fa-f]+)', msg)
    if m:
        event.event_type = "pd_tx"
        header_raw = m.group(1)
        decoded = decode_pd_header(header_raw)
        event.decoded = {
            "pd_header_raw": header_raw,
            "pd_header_decoded": decoded.to_dict(),
        }
        event.flags.append("KEY_EVENT")
        return

    # PD TX complete
    m = re.search(r'PD TX complete, status:\s*(\d+)', msg)
    if m:
        event.event_type = "pd_tx_complete"
        status = int(m.group(1))
        event.decoded = {"tx_status": status}
        if status == 0:
            event.flags.append("TX_COMPLETE")
        return

    # --- PD RX data objects in sprd_tcpm_log ---
    # "PD RX, data[N]=0xXXXXXX"
    m = re.search(r'PD RX, data\[(\d+)\]\s*=\s*(0x[0-9A-Fa-f]+)', msg)
    if m:
        event.event_type = "pd_rx_data"
        data_idx = int(m.group(1))
        data_val = m.group(2)
        if event.decoded is None:
            event.decoded = {}
        if "pd_data" not in event.decoded:
            event.decoded["pd_data"] = []
        event.decoded["pd_data"].append(data_val)
        return

    # --- PD header decode in sprd_pd_log ---
    # "header = 0xXXXX, msg header = 0xXXXX"
    m = re.search(r'header\s*=\s*(0x[0-9A-Fa-f]+).*msg header\s*=\s*(0x[0-9A-Fa-f]+)', msg)
    if m:
        event.event_type = "pd_header_raw"
        header_raw = m.group(1)
        decoded = decode_pd_header(header_raw)
        event.decoded = {
            "pd_header_raw": header_raw,
            "pd_header_decoded": decoded.to_dict(),
        }
        event.flags.append("KEY_EVENT")
        return

    # "header = 0xXXXX" (standalone)
    m = re.search(r'^header\s*=\s*(0x[0-9A-Fa-f]+)', msg)
    if m:
        event.event_type = "pd_header_raw"
        header_raw = m.group(1)
        decoded = decode_pd_header(header_raw)
        event.decoded = {
            "pd_header_raw": header_raw,
            "pd_header_decoded": decoded.to_dict(),
        }
        event.flags.append("KEY_EVENT")
        return

    # --- TX msg data in sprd_pd_log ---
    # "tx msg: header = 0xXXXX"
    m = re.search(r'tx msg: header\s*=\s*(0x[0-9A-Fa-f]+)', msg)
    if m:
        event.event_type = "pd_tx"
        header_raw = m.group(1)
        decoded = decode_pd_header(header_raw)
        event.decoded = {
            "pd_header_raw": header_raw,
            "pd_header_decoded": decoded.to_dict(),
        }
        event.flags.append("KEY_EVENT")
        return

    # "tx msg: data[N] = 0xXXXX"
    m = re.search(r'tx msg: data\[(\d+)\]\s*=\s*(0x[0-9A-Fa-f]+)', msg)
    if m:
        event.event_type = "pd_rx_data"
        data_val = m.group(2)
        if event.decoded is None:
            event.decoded = {}
        if "pd_data" not in event.decoded:
            event.decoded["pd_data"] = []
        event.decoded["pd_data"].append(data_val)
        return

    # --- PD IRQ ---
    m = re.search(r'pd irq: start handle irq.*irq\s*=\s*(\d+)', msg)
    if m:
        event.event_type = "pd_irq"
        return

    # "pd irq: int sts = 0xXXXX"
    m = re.search(r'pd irq: int sts\s*=\s*(0x[0-9A-Fa-f]+)', msg)
    if m and event.event_type == "other":
        event.event_type = "pd_irq"
        return

    # "pd irq: IRQ_HANDLED"
    if "IRQ_HANDLED" in msg:
        event.event_type = "pd_irq"
        return

    # "pd irq: ps rdy flag"
    if "ps rdy flag" in msg:
        event.event_type = "pd_irq"
        event.flags.append("PS_RDY_FLAG")
        return

    # --- PDO entries: "PDO N: type X, V mV, I mA [flags]" ---
    m = re.search(r'PDO\s+(\d+):\s*type\s+(\d+),\s*(\d+)\s*mV,\s*(\d+)\s*mA\s*(\[.*?\])?', msg)
    if m:
        event.event_type = "pdo_entry"
        pdo_idx = int(m.group(1))
        pdo_type = int(m.group(2))
        voltage = int(m.group(3))
        current = int(m.group(4))
        flags_str = m.group(5) or ""

        pdo = PdoEntry(
            index=pdo_idx,
            type=PDO_TYPES.get(pdo_type, f"type_{pdo_type}"),
            type_code=pdo_type,
            voltage_mv=voltage,
            current_ma=current,
        )
        # Parse flags
        flags_clean = flags_str.strip("[]")
        if flags_clean:
            pdo.flags = [f.strip() for f in flags_clean.split(",") if f.strip()]

        if event.decoded is None:
            event.decoded = {}
        if "pdos" not in event.decoded:
            event.decoded["pdos"] = []
        event.decoded["pdos"].append(pdo.to_dict())
        return

    # --- VBUS events (extended: extcon, vbus_connect_value, handle_vbus, bypass, etc.) ---
    if "VBUS on" in msg:
        event.event_type = "vbus_event"
        event.flags.append("KEY_EVENT")
        return
    if "VBUS off" in msg:
        event.event_type = "vbus_event"
        event.flags.append("KEY_EVENT")
        return

    # VBUS change via extcon: "sc27xx_pd_extcon_vbus_change_event, vbus_online: 0/1"
    m = re.search(r'extcon_vbus_change_event.*vbus_online:\s*(\d)', msg)
    if m:
        event.event_type = "vbus_event"
        event.decoded = {"vbus_online": int(m.group(1))}
        return

    # VBUS connect value: "vbus_connect_value:1"
    m = re.search(r'vbus_connect_value:\s*(\d)', msg)
    if m:
        event.event_type = "vbus_event"
        event.decoded = {"vbus_connect": int(m.group(1))}
        return

    # VBUS handle: "sc27xx_typec_handle_vbus event N" or "check vbus and cc"
    m = re.search(r'handle_vbus event\s+(\d)', msg)
    if m:
        event.event_type = "vbus_event"
        event.decoded = {"vbus_event_code": int(m.group(1))}
        return
    if "check vbus and cc" in msg:
        event.event_type = "vbus_event"
        return

    # VBUS bypass / VBUS notify from bc1p2
    if "vbus_ok_bypass" in msg:
        event.event_type = "vbus_event"
        return
    m = re.search(r'sprd_bc1p2_vbus_notify event\s*=\s*(\d)', msg)
    if m:
        event.event_type = "vbus_event"
        event.decoded = {"bc1p2_vbus_notify": int(m.group(1))}
        return
    if "musb-sprd" in msg and "vbus:" in msg:
        m = re.search(r'vbus:\s*(\d)\s*event received', msg)
        if m:
            event.event_type = "vbus_event"
            event.decoded = {"musb_vbus": int(m.group(1))}
            return

    # --- Type-C connection events ---
    if "use pdhub c2c typec plug in" in msg or "typec plug in" in msg:
        event.event_type = "typec_connect"
        event.flags.append("KEY_EVENT")
        return
    if "connect_set_status_use_pdhubc2c" in msg:
        event.event_type = "typec_connect"
        if "sink connect" in msg.lower():
            event.decoded = {"role": "sink"}
        elif "source connect" in msg.lower():
            event.decoded = {"role": "source"}
        return
    # DRP state: "now works as DRP and is in N state"
    m = re.search(r'now works as DRP.*in\s+(\d+)\s+state.*event\s+(\d+)', msg)
    if m:
        event.event_type = "typec_connect"
        event.decoded = {"drp_state": int(m.group(1)), "event": int(m.group(2))}
        return

    # --- PD engine state ---
    # "pd := on" / "pd := off"
    m = re.search(r'pd\s*:=\s*(on|off)', msg)
    if m:
        event.event_type = "pd_engine_state"
        event.decoded = {"pd_enabled": m.group(1) == "on"}
        return
    # "pd->state = N"
    m = re.search(r'pd->state\s*=\s*(\d+)', msg)
    if m:
        event.event_type = "pd_engine_state"
        event.decoded = {"pd_state_code": int(m.group(1))}
        return

    # --- RP value change ---
    m = re.search(r'rp_value_change_state.*value\s*=\s*(\d+)', msg)
    if m:
        event.event_type = "rp_change"
        event.decoded = {"rp_value": int(m.group(1))}
        return
    m = re.search(r'rp_value_change_state.*sink_capability\s*=\s*(\d+)', msg)
    if m:
        event.event_type = "rp_change"
        event.decoded = {"sink_capability": int(m.group(1))}
        return

    # --- Power role swap ---
    if "pd power role swap" in msg:
        event.event_type = "power_role"
        m = re.search(r'power role swap\s+(true|false)', msg)
        if m:
            event.decoded = {"swap": m.group(1)}
        return

    # --- CC polarity ---
    # Note: subsystem check instead of "sprd_tcpm" in msg because
    # content_raw = message.strip() (does NOT contain module prefix)
    m = re.search(r'polarity\s+(\d)', msg)
    if m and event.subsystem == "sprd_tcpm_log":
        event.event_type = "cc_polarity"
        event.decoded = {"polarity": int(m.group(1))}
        return

    # --- Vconn status ---
    if "vconn" in msg.lower():
        m = re.search(r'vconn\s*:=\s*(\S+)', msg)
        if m:
            event.event_type = "vconn_status"
            event.decoded = {"vconn_value": m.group(1)}
            return
        if "vconn NULL" in msg:
            event.event_type = "vconn_status"
            event.decoded = {"vconn_value": "NULL"}
            return

    # --- Read PD header ---
    m = re.search(r'read head,\s*head\s*=\s*(0x[0-9A-Fa-f]+)', msg)
    if m:
        event.event_type = "read_pd_header"
        header_raw = m.group(1)
        decoded = decode_pd_header(header_raw)
        event.decoded = {
            "pd_header_raw": header_raw,
            "pd_header_decoded": decoded.to_dict(),
        }
        return

    # --- Charger manager: vote callbacks ---
    m = re.search(r'cm_sprd_vote_callback,\s*VOTE_TYPE_(\w+),\s*(\d+)', msg)
    if m:
        event.event_type = "charger_vote"
        vote_type = m.group(1)
        vote_value = int(m.group(2))
        event.decoded = {"vote_type": f"VOTE_TYPE_{vote_type}", "vote_value": vote_value}
        event.flags.append("CHARGER_VOTE")
        return

    # --- Charger manager: JEITA status ---
    if "cm_manager_get_jeita_status" in msg:
        event.event_type = "charger_jeita"
        m = re.search(r'jeita_config\s*=\s*(\d+)', msg)
        if m:
            event.decoded = {"jeita_config": int(m.group(1))}
        else:
            event.decoded = {}
        return

    # --- Charger manager: state ---
    # "is_sink = 0, state = 1" or "is_sink = 1, is_source = 0"
    m = re.search(r'is_sink\s*=\s*(\d),\s*is_source\s*=\s*(\d)', msg)
    if m:
        event.event_type = "charger_state"
        event.decoded = {"is_sink": int(m.group(1)), "is_source": int(m.group(2))}
        return
    m = re.search(r'is_sink\s*=\s*(\d),\s*state\s*=\s*(\d)', msg)
    if m:
        event.event_type = "charger_state"
        event.decoded = {"is_sink": int(m.group(1)), "state": int(m.group(2))}
        return

    # --- Charger IC register dump ---
    if "bq2560x_dump_register" in msg:
        event.event_type = "charger_reg_dump"
        return

    # --- Charger PSY missing ---
    if "Cannot find power supply" in msg:
        event.event_type = "charger_psy"
        m = re.search(r"Cannot find power supply\s+\"(\S+)\"", msg)
        if m:
            event.decoded = {"psy_name": m.group(1)}
        return

    # --- USB current limit ---
    m = re.search(r'sprd_vchg.*usb_limit\s*=\s*(\d+)', msg)
    if m:
        event.event_type = "usb_current_limit"
        event.current_ma = int(m.group(1))
        return

    # --- Charger type status ---
    if "cm_update_charger_type_status" in msg:
        event.event_type = "charger_type"
        m = re.search(r'charger_status\s*=\s*(\d+)', msg)
        if m:
            event.decoded = {"charger_status": int(m.group(1))}
        return

    # --- BC1.2 detection ---
    if "bc1p2:" in msg and ("chg" in msg or "bc1p2_status" in msg or "detect" in msg):
        event.event_type = "bc1p2"
        if "chg entry" in msg:
            event.decoded = {"phase": "entry"}
        elif "absent bc1p2_status" in msg:
            event.decoded = {"phase": "absent"}
        elif "detect" in msg.lower():
            event.decoded = {"phase": "detect"}
        return

    # --- Vote governor ---
    m = re.search(r'vote_gov:\s*VOTE_TYPE_(\w+)\s+vote the same', msg)
    if m:
        event.event_type = "charger_vote"
        if event.decoded is None:
            event.decoded = {}
        event.decoded["vote_type"] = f"VOTE_TYPE_{m.group(1)}"
        event.decoded["vote_value"] = event.decoded.get("vote_value", 1)
        event.flags.append("CHARGER_VOTE")
        return

    # --- Charger vote (bracket format): "cm_sprd_vote_callback, VOTE_TYPE_IBUS[1000000]" ---
    m = re.search(r'cm_sprd_vote_callback,\s*VOTE_TYPE_(\w+)\[(-?\d+)\]', msg)
    if m:
        event.event_type = "charger_vote"
        event.decoded = {"vote_type": f"VOTE_TYPE_{m.group(1)}", "vote_value": int(m.group(2))}
        event.flags.append("CHARGER_VOTE")
        return

    # --- Charger manager: current limit work ---
    m = re.search(
        r'cm_limit_current_work:.*usb_limit\s+(-?\d+),\s*rp_limit\s+(\d+),\s*pd_req_cur_ua\s+(-?\d+).*limit_status\s+(\d+)',
        msg
    )
    if m:
        event.event_type = "charger_limit"
        event.decoded = {
            "usb_limit": int(m.group(1)),
            "rp_limit": int(m.group(2)),
            "pd_req_cur_ua": int(m.group(3)),
            "limit_status": int(m.group(4)),
        }
        event.current_ma = int(m.group(2)) // 1000  # rp_limit in uA → mA
        return

    # --- Charger manager: hard reset request ---
    if "sprd_vchg: receive USB PD hard reset request" in msg:
        event.event_type = "charger_state"
        event.decoded = {"event": "pd_hard_reset_request"}
        event.flags.append("HARD_RESET")
        return

    # --- Charger manager: charger type/online ---
    m = re.search(r'sprd_vchg: charger type\s*=\s*(\d+),\s*charger online\s*=\s*(\d+),\s*events\s*=\s*(\d+)', msg)
    if m:
        event.event_type = "charger_state"
        event.decoded = {
            "charger_type": int(m.group(1)),
            "charger_online": int(m.group(2)),
            "events": int(m.group(3)),
        }
        return

    # --- Charger manager: retry count ---
    m = re.search(r'retry_cnt\s*=\s*(\d+)', msg)
    if m and "charger-manager" in msg:
        event.event_type = "charger_state"
        event.decoded = {"retry_cnt": int(m.group(1))}
        return

    # --- Bare rp_value_change_state (no value= prefix) ---
    m = re.search(r'rp_value_change_state\s+(\d+)', msg)
    if m:
        event.event_type = "rp_change"
        event.decoded = {"rp_value": int(m.group(1))}
        return

    # --- sprd_tcpm_set_roles ---
    m = re.search(r'sprd_tcpm_set_roles.*set roles\s+\[(\w+):(\w+)\]', msg)
    if m:
        event.event_type = "tcpm_config"
        event.decoded = {"power_role": m.group(1), "data_role": m.group(2)}
        event.flags.append("KEY_EVENT")
        return

    # --- sprd_tcpm_snk_attach ---
    m = re.search(r'sprd_tcpm_snk_attach.*pd_capable\s+(\w+)', msg)
    if m:
        event.event_type = "tcpm_config"
        event.decoded = {"pd_capable": m.group(1)}
        return

    # --- sprd_tcpm_typec_connect ---
    m = re.search(r'sprd_tcpm_typec_connect.*(connected|pd_capable)\s*=\s*(\d+)', msg)
    if m:
        event.event_type = "tcpm_config"
        if event.decoded is None:
            event.decoded = {}
        event.decoded[m.group(1)] = int(m.group(2))
        return

    # --- sprd_tcpm_typec_pr_swap_no_chk_detach ---
    m = re.search(r'sprd_tcpm_typec_pr_swap_no_chk_detach.*cur state:\s*(\S+),\s*on:\s*(\d+)', msg)
    if m:
        event.event_type = "tcpm_config"
        event.decoded = {"cur_state": m.group(1), "on": int(m.group(2))}
        return

    # --- Requesting mux state ---
    m = re.search(r'Requesting mux state\s+(\d+),\s*usb-role\s+(\d+),\s*orientation\s+(\d+)', msg)
    if m:
        event.event_type = "tcpm_config"
        event.decoded = {"mux_state": int(m.group(1)), "usb_role": int(m.group(2)), "orientation": int(m.group(3))}
        return

    # --- PD PHY RX control: "set rx: on = 0/1" ---
    m = re.search(r'set rx:\s*on\s*=\s*(\d+),\s*sts1\s*=\s*(0x[0-9A-Fa-f]+)', msg)
    if m:
        event.event_type = "pd_phy_control"
        event.decoded = {"rx_on": int(m.group(1)), "sts1": m.group(2)}
        return

    # --- bq2560x charger current limit ---
    # Format with reg_val: "set limit_cur = N, reg_val = 0xX, actual_limit_cur = N"
    m = re.search(r'set limit_cur\s*=\s*(\d+),\s*reg_val\s*=\s*(0x[0-9A-Fa-f]+),\s*actual_limit_cur\s*=\s*(\d+)', msg)
    if m:
        event.event_type = "charger_limit"
        event.decoded = {"limit_cur": int(m.group(1)), "reg_val": m.group(2), "actual_limit_cur": int(m.group(3))}
        event.current_ma = int(m.group(3)) // 1000
        return
    # Bare format: "set limit current limit_cur = 1000000"
    m = re.search(r'set limit current\s+limit_cur\s*=\s*(\d+)', msg)
    if m:
        event.event_type = "charger_limit"
        event.decoded = {"limit_cur": int(m.group(1))}
        event.current_ma = int(m.group(1)) // 1000
        return

    # --- Typec status (standalone): "typec status = 2" ---
    m = re.search(r'^typec status\s*=\s*(\d+)', msg)
    if m:
        event.event_type = "typec_connect"
        event.decoded = {"typec_status": int(m.group(1))}
        return

    # --- Connect type (standalone): "connect, use_pdhub_c2c = 1" ---
    m = re.search(r'connect,\s*use_pdhub_c2c\s*=\s*(\d+)', msg)
    if m:
        event.event_type = "typec_connect"
        event.decoded = {"use_pdhub_c2c": int(m.group(1))}
        return

    # --- VBUS status poll ---
    m = re.search(r'vbus status\s*=\s*(0x[0-9A-Fa-f]+),\s*vbus_present\s*=\s*(\d+)', msg)
    if m:
        event.event_type = "vbus_event"
        event.decoded = {"vbus_status_reg": m.group(1), "vbus_present": int(m.group(2))}
        return
    if "online start to poll vbus status" in msg or "online finish to poll vbus status" in msg:
        event.event_type = "vbus_event"
        event.decoded = {"poll_phase": "start" if "start" in msg else "finish"}
        return

    # --- vbus/charge state: "vbus=0 charge:=1" ---
    m = re.search(r'vbus\s*=\s*(\d+)\s+charge\s*:=\s*(\d+)', msg)
    if m:
        event.event_type = "vbus_event"
        event.decoded = {"vbus": int(m.group(1)), "charge": int(m.group(2))}
        return

    # --- vbus is already Off ---
    if "vbus is already Off" in msg:
        event.event_type = "vbus_event"
        event.decoded = {"state": "already_off"}
        return

    # --- PD IRQ: receive hard reset ---
    if "pd irq: receive hard reset" in msg:
        event.event_type = "pd_irq"
        event.flags.append("HARD_RESET")
        return

    # --- Received hard reset (generic) ---
    if "Received hard reset" in msg:
        event.event_type = "pd_irq"
        event.flags.append("HARD_RESET")
        return

    # --- Charger detect finished ---
    m = re.search(r'charger detect finished with type:\s*(\d+)', msg)
    if m:
        event.event_type = "bc1p2"
        event.decoded = {"detected_type": int(m.group(1))}
        return

    # --- BC1.2 via musb ---
    if "use software bc1p2 to detect charger type" in msg:
        event.event_type = "bc1p2"
        event.decoded = {"method": "software"}
        return
    if "musb_sprd_retry_charger_detect" in msg:
        event.event_type = "bc1p2"
        event.decoded = {"phase": "retry"}
        return

    # --- USB charger absent ---
    if "usb_charger_absent" in msg:
        event.event_type = "bc1p2"
        event.decoded = {"status": "absent"}
        return

    # --- CC changes: "CC1: X -> Y, CC2: X -> Y [state ..., polarity ..., ...]" ---
    m = re.search(
        r'CC1:\s*(\d+)\s*->\s*(\d+),\s*CC2:\s*(\d+)\s*->\s*(\d+)\s*'
        r'\[state\s+(\S+),\s*polarity\s+(\d+),\s*(\w+)\]',
        msg
    )
    if m:
        event.event_type = "cc_change"
        event.cc_info = {
            "cc1_from": int(m.group(1)), "cc1_to": int(m.group(2)),
            "cc2_from": int(m.group(3)), "cc2_to": int(m.group(4)),
            "state": m.group(5),
            "polarity": int(m.group(6)),
            "connection_status": m.group(7),
        }
        # Fix cc1/cc2
        event.cc_info["cc1"] = int(m.group(1))
        event.cc_info["cc2"] = int(m.group(3))
        try:
            event.cc_info["cc1"] = int(m.group(2))  # to value is current
            event.cc_info["cc2"] = int(m.group(4))
        except Exception:
            pass
        event.flags.append("KEY_EVENT")
        return

    # --- Voltage/current limit ---
    m = re.search(r'Setting voltage/current limit\s+(\d+)\s*mV\s+(\d+)\s*mA', msg)
    if m:
        event.event_type = "voltage_current_limit"
        event.voltage_mv = int(m.group(1))
        event.current_ma = int(m.group(2))
        return

    # --- get_rp_limit ---
    m = re.search(r'get_rp_limit\s+(\d+)\s*mA', msg)
    if m:
        event.event_type = "rp_limit"
        event.current_ma = int(m.group(1))
        return

    # --- Caps update ---
    if "update head cfg spec rev" in msg or "update head" in msg:
        event.event_type = "caps_update"
        return

    # --- Charger manager ---
    # cm_check_pd_negotiated_limit_current
    m = re.search(
        r'Requesting APDO:\s*(\d+)\s*mV,\s*(\d+)\s*mA.*enable_limit:\s*(\d+)',
        msg
    )
    if m:
        event.event_type = "charger_limit"
        event.voltage_mv = int(m.group(1))
        event.current_ma = int(m.group(2))
        return

    # cm_update_charge_info
    m = re.search(
        r'adapter_chg_volt=\s*(\d+)mV',
        msg
    )
    if m and "cm_update_charge_info" in msg:
        event.event_type = "charger_info"
        ci = ChargerInfo()
        ci.adapter_chg_volt_mv = int(m.group(1))

        # Extract other fields
        for field, pattern, ctype in [
            ("chgr_type", r'chgr type=\s*(\d+)', int),
            ("fchg_en", r'fchg_en=\s*(\d+)', int),
            ("cp_running", r'cp_running=\s*(\d+)', int),
            ("max_chg_lmt_cur_ua", r'max chg_lmt_cur=\s*(\d+)uA', int),
            ("max_inpt_lmt_cur_ua", r'max inpt_lmt_cur=\s*(\d+)uA', int),
            ("max_chg_volt_uv", r'max chg_volt=\s*(\d+)uV', int),
        ]:
            fm = re.search(pattern, msg)
            if fm:
                setattr(ci, field, ctype(fm.group(1)))

        event.charger_info = ci.to_dict()
        return

    # --- Disconnect events ---
    if "typec plug out" in msg or "disconnect" in msg.lower() or "typec in or out" in msg:
        event.event_type = "disconnect"
        event.flags.append("DISCONNECT")
        return

    # --- Plug out ---
    if "plug out" in msg.lower():
        event.event_type = "plug_out"
        event.flags.append("DISCONNECT")
        return

    # --- Hard reset ---
    if "hardreset" in msg.lower():
        event.flags.append("HARD_RESET")

    # --- IRQ received hardreset ---
    if "IRQ: PD received hardreset" in msg:
        event.flags.append("HARD_RESET")

    # ================================================================
    # NEW CLASSIFIERS — added to reduce unmatched events
    # ================================================================

    # --- sprpd_pd_log: PD reset sequence ---
    # "sc27xx_pd_reset:line1008: clear_tx_id = 0/1"
    m = re.search(r'sc27xx_pd_reset:\w+:\s*clear_tx_id\s*=\s*(\d+)', msg)
    if m:
        event.event_type = "pd_reset"
        event.decoded = {"clear_tx_id": int(m.group(1))}
        return
    # "sc27xx_pd_reset:line1023: clear tx id"
    if "clear tx id" in msg and "sc27xx_pd_reset" in msg:
        event.event_type = "pd_reset"
        event.decoded = {"clear_tx_id": "done"}
        return

    # --- sprd_pd_log: RX flush ---
    # "sc27xx_pd_rx_flush:line971: start rx flush" / "line974: rx flush done"
    if "sc27xx_pd_rx_flush" in msg:
        if "start rx flush" in msg:
            event.event_type = "pd_rx_flush"
            event.decoded = {"phase": "start"}
            return
        if "rx flush done" in msg:
            event.event_type = "pd_rx_flush"
            event.decoded = {"phase": "done"}
            return

    # --- sprd_pd_log: PD IRQ delay ---
    # "pd irq: delay 500 us"
    m = re.search(r'pd irq:\s*delay\s+(\d+)\s*us', msg)
    if m:
        event.event_type = "pd_irq"
        event.decoded = {"delay_us": int(m.group(1))}
        return

    # --- sprd_pd_log: PD FIFO check ---
    # "sc27xx_pd_check_message_packages, reg_val = 0x2000, rx fifo data num = 0"
    m = re.search(r'sc27xx_pd_check_message_packages,\s*reg_val\s*=\s*(0x[0-9A-Fa-f]+),\s*rx fifo data num\s*=\s*(\d+)', msg)
    if m:
        event.event_type = "pd_rx_fifo"
        event.decoded = {"reg_val": m.group(1), "rx_fifo_data_num": int(m.group(2))}
        return

    # --- sprd_pd_log: TX msg header config ---
    # "tx msg: header cfg = 0x1082"
    m = re.search(r'tx msg:\s*header cfg\s*=\s*(0x[0-9A-Fa-f]+)', msg)
    if m:
        event.event_type = "pd_tx_cfg"
        header_raw = m.group(1)
        decoded = decode_pd_header(header_raw)
        event.decoded = {
            "pd_header_raw": header_raw,
            "pd_header_decoded": decoded.to_dict(),
        }
        return

    # --- sprd_pd_log: TX msg end ---
    if "tx msg end" in msg:
        event.event_type = "pd_tx_end"
        return

    # --- sprd_pd_log: PS_RDY message received (not flushed) ---
    # "first negotiate, ps rdy msg, not rx flush"
    if "ps rdy msg, not rx flush" in msg:
        event.event_type = "pd_ps_rdy"
        if "first negotiate" in msg:
            event.decoded = {"negotiate_type": "first", "rx_flushed": False}
        else:
            event.decoded = {"negotiate_type": "re_negotiate", "rx_flushed": False}
        return

    # --- sprd_tcpm_log: snk negotiate capabilities timing ---
    # "handle_snk_negotiate_capabilities:line4583 curr_time1 = 168753285 ms"
    m = re.search(r'handle_snk_negotiate_capabilities:\w+\s+curr_time1\s*=\s*(\d+)\s*ms', msg)
    if m:
        event.event_type = "pd_snk_negotiate"
        event.decoded = {"phase": "time1", "curr_time_ms": int(m.group(1))}
        return
    # "handle_snk_negotiate_capabilities:line4588 curr_time2 = ..."
    m = re.search(r'handle_snk_negotiate_capabilities:\w+\s+curr_time2\s*=\s*(\d+)\s*ms', msg)
    if m:
        event.event_type = "pd_snk_negotiate"
        event.decoded = {"phase": "time2", "curr_time_ms": int(m.group(1))}
        return
    # "handle_snk_negotiate_capabilities:line4590 duration = N ms"
    m = re.search(r'handle_snk_negotiate_capabilities:\w+\s+duration\s*=\s*(\d+)\s*ms', msg)
    if m:
        event.event_type = "pd_snk_negotiate"
        event.decoded = {"phase": "duration", "duration_ms": int(m.group(1))}
        return
    # "handle_snk_negotiate_capabilities:line4584 pd_capable true/false"
    m = re.search(r'handle_snk_negotiate_capabilities:\w+\s+pd_capable\s+(\w+)', msg)
    if m:
        event.event_type = "pd_snk_negotiate"
        event.decoded = {"phase": "pd_capable", "pd_capable": m.group(1) == "true"}
        return

    # --- sprd_tcpm_log: CC/VBUS snapshot at negotiation ---
    # "cc=0 cc1=5 cc2=0 vbus=0 vconn=sink polarity=0"
    m = re.search(r'cc=(\d+)\s+cc1=(\d+)\s+cc2=(\d+)\s+vbus=(\d+)\s+vconn=(\w+)\s+polarity=(\d+)', msg)
    if m:
        event.event_type = "cc_vbus_state"
        event.decoded = {
            "cc": int(m.group(1)),
            "cc1": int(m.group(2)),
            "cc2": int(m.group(3)),
            "vbus": int(m.group(4)),
            "vconn": m.group(5),
            "polarity": int(m.group(6)),
        }
        return

    # --- sprd_tcpm_log: Requesting PDO (actual selection) ---
    # "Requesting PDO 0: 5000 mV, 3000 mA"
    m = re.search(r'Requesting PDO\s+(\d+):\s*(\d+)\s*mV,\s*(\d+)\s*mA', msg)
    if m:
        event.event_type = "pdo_request"
        event.decoded = {
            "pdo_index": int(m.group(1)),
            "voltage_mv": int(m.group(2)),
            "current_ma": int(m.group(3)),
        }
        return

    # --- sprd_tcpm_log: TX complete timing ---
    # "sprd_tcpm_pd_transmit: tx_complete_curr_time = 168753286 ms"
    m = re.search(r'sprd_tcpm_pd_transmit:\s*tx_complete_curr_time\s*=\s*(\d+)\s*ms', msg)
    if m:
        event.event_type = "pd_tx_complete"
        event.decoded = {"tx_complete_time_ms": int(m.group(1))}
        return

    # --- sc27xx-typec-pd: PD received hardreset (IRQ format) ---
    # Note: This system message format differs from the srd_pd_log parsed format
    # "IRQ: PD received hardreset, ktime = 168751260 ms"
    m = re.search(r'IRQ:\s*PD received hardreset.*ktime\s*=\s*(\d+)', msg)
    if m:
        event.event_type = "pd_irq"
        event.decoded = {"ktime_ms": int(m.group(1))}
        event.flags.append("HARD_RESET")
        return

    # --- sc27xx-typec: typec interrupt ---
    if "sc27xx_typec_interrupt enter" in msg:
        event.event_type = "typec_interrupt"
        return

    # --- sc27xx-typec-pd: soc compatible ---
    if "soc compatible" in msg and "sc27xx-typec-pd" in msg:
        event.event_type = "pd_init"
        return

    # --- sc27xx-typec: typec connect, not vbusonly ---
    if "typec connect, not vbusonly" in msg:
        event.event_type = "typec_connect"
        event.decoded = {"vbus_only": False}
        return

    # --- sc27xx-typec: pr_swap_no_chk_detach (sc27xx-typec version) ---
    # "sc27xx_typec_pr_swap_no_chk_detach, on = 0"
    m = re.search(r'sc27xx_typec_pr_swap_no_chk_detach,\s*on\s*=\s*(\d+)', msg)
    if m:
        event.event_type = "tcpm_config"
        event.decoded = {"on": int(m.group(1)), "source": "sc27xx_typec"}
        return

    # --- bq2560x: interrupt ---
    if "bq2560x_chg" in msg and "interrupt occurs" in msg:
        event.event_type = "charger_ic_irq"
        return

    # --- bq2560x: start charge ---
    if "bq2560x_chg" in msg and "start charge" in msg:
        event.event_type = "charger_state"
        event.decoded = {"action": "start_charge"}
        return

    # --- bq2560x: set limit current (bare format, already handled by charger_limit?) ---
    # Actually some bq2560x are already handled; check for unhandled variant

    # --- charger-manager: jeita status (alternative format) ---
    # "current-last jeita status: cm_update_current_jeita_status 2-0, temperature: 295"
    m = re.search(r'current-last jeita status:\s*cm_update_current_jeita_status\s+(\d+-\d+),\s*temperature:\s*(\d+)', msg)
    if m:
        event.event_type = "charger_jeita"
        event.decoded = {"jeita_status": m.group(1), "temperature": int(m.group(2))}
        return

    # --- charger-manager: target voltage/current ---
    # "target terminate voltage = 4340000, target current = 1000000"
    m = re.search(r'target terminate voltage\s*=\s*(\d+),\s*target current\s*=\s*(\d+)', msg)
    if m:
        event.event_type = "charger_target"
        event.decoded = {"terminate_voltage_uv": int(m.group(1)), "target_current_ua": int(m.group(2))}
        event.current_ma = int(m.group(2)) // 1000
        return

    # --- charger-manager: default usb online / ac online ---
    if "default usb online" in msg:
        event.event_type = "charger_state"
        event.decoded = {"usb_online": True}
        return
    if "ac online" in msg:
        event.event_type = "charger_state"
        event.decoded = {"ac_online": True}
        return

    # --- charger-manager: wakelock ---
    if "acquire charger_manager_wakelock" in msg:
        event.event_type = "charger_state"
        event.decoded = {"wakelock": "acquired"}
        return

    # --- charger-manager: IR compensation ---
    m = re.search(r'cm_ir_compensation_enable\s+(enable|disable)', msg)
    if m:
        event.event_type = "charger_config"
        event.decoded = {"ir_compensation": m.group(1)}
        return
    m = re.search(r'cm_ir_compensation,\s*us\s*=\s*(\d+),\s*rc\s*=\s*(\d+)', msg)
    if m:
        event.event_type = "charger_config"
        event.decoded = {
            "ir_compensation_us": int(m.group(1)),
            "ir_compensation_rc": int(m.group(2)),
        }
        # Also extract optional fields
        for field, pattern in [
            ("upper_limit", r'upper_limit\s*=\s*(\d+)'),
            ("lower_limit", r'lower_limit\s*=\s*(\d+)'),
            ("target_cccv", r'target_cccv\s*=\s*(\d+)'),
            ("ibat_avg", r'ibat_avg\s*=\s*(\d+)'),
        ]:
            fm = re.search(pattern, msg)
            if fm:
                event.decoded[field] = int(fm.group(1))
        return

    # --- charger-manager: target/charging_status ---
    # "target 1, charging_status 0"
    m = re.search(r'target\s+(\d+),\s*charging_status\s+(\d+)', msg)
    if m:
        event.event_type = "charger_state"
        event.decoded = {"target": int(m.group(1)), "charging_status": int(m.group(2))}
        return

    # --- charger-manager: thermal charge power limit ---
    m = re.search(r'thermal set charge power limit,\s*thm_pwr\s*=\s*(\d+)mW', msg)
    if m:
        event.event_type = "charger_limit"
        event.decoded = {"thermal_power_limit_mw": int(m.group(1))}
        return

    # --- charger-manager: fast charge handler ---
    # "fast_charge_handler, fast_charger_type = 4, cp_running = 0, charger_enabled = 1, ext_pwr_online = 1"
    m = re.search(r'fast_charge_handler,\s*fast_charger_type\s*=\s*(\d+),\s*cp_running\s*=\s*(\d+),\s*charger_enabled\s*=\s*(\d+),\s*ext_pwr_online\s*=\s*(\d+)', msg)
    if m:
        event.event_type = "charger_fchg"
        event.decoded = {
            "fast_charger_type": int(m.group(1)),
            "cp_running": int(m.group(2)),
            "charger_enabled": int(m.group(3)),
            "ext_pwr_online": int(m.group(4)),
        }
        return

    # --- charger-manager: fchg change ---
    if "sprd_fchg_change, pps or pd extcon" in msg:
        event.event_type = "charger_fchg"
        event.decoded = {"trigger": "pps_or_pd_extcon"}
        return

    # --- charger-manager: fchg work ---
    # "sprd_fchg_work, pd_extcon = 1, sfcp_extcon = 0, customized_extcon = 0, fchg type = 3"
    m = re.search(r'sprd_fchg_work,\s*pd_extcon\s*=\s*(\d+),\s*sfcp_extcon\s*=\s*(\d+),\s*customized_extcon\s*=\s*(\d+),\s*fchg type\s*=\s*(\d+)', msg)
    if m:
        event.event_type = "charger_fchg"
        event.decoded = {
            "pd_extcon": int(m.group(1)),
            "sfcp_extcon": int(m.group(2)),
            "customized_extcon": int(m.group(3)),
            "fchg_type": int(m.group(4)),
        }
        return

    # --- charger-manager: start fixed fchg ---
    if "cm_start_fixed_fchg" in msg:
        event.event_type = "charger_fchg"
        event.decoded = {"action": "start_fixed_fchg"}
        return

    # --- charger-manager: charge monitoring data ---
    # "vbat: 4140000, vbat_avg: 4137000, OCV: 3804000, ibat: 3027000, ibat_avg: ..., ibus: -22, vbus: 8007000, msoc: 235, chg_sts:"
    m = re.search(r'vbat:\s*(\d+),\s*vbat_avg:\s*(\d+),\s*OCV:\s*(\d+),\s*ibat:\s*(\d+),\s*ibat_avg:\s*(\d+),\s*ibus:\s*(-?\d+),\s*vbus:\s*(\d+),\s*msoc:\s*(\d+)', msg)
    if m:
        event.event_type = "charger_monitor"
        event.decoded = {
            "vbat_uv": int(m.group(1)),
            "vbat_avg_uv": int(m.group(2)),
            "ocv_uv": int(m.group(3)),
            "ibat_ua": int(m.group(4)),
            "ibat_avg_ua": int(m.group(5)),
            "ibus_ua": int(m.group(6)),
            "vbus_uv": int(m.group(7)),
            "msoc": int(m.group(8)),
        }
        return

    # --- charger-manager: UI SOC update ---
    # "new_uisoc = 235, old_uisoc = 235, work_cycle = 8s, cap_one_time = 16s"
    m = re.search(r'new_uisoc\s*=\s*(\d+),\s*old_uisoc\s*=\s*(\d+),\s*work_cycle\s*=\s*(\d+)s,\s*cap_one_time\s*=\s*(\d+)s', msg)
    if m:
        event.event_type = "charger_monitor"
        event.decoded = {
            "new_uisoc": int(m.group(1)),
            "old_uisoc": int(m.group(2)),
            "work_cycle_s": int(m.group(3)),
            "cap_one_time_s": int(m.group(4)),
        }
        return

    # --- charger-manager: charger type polling ---
    # "cm_charger_type_polling: update charger type:1"
    m = re.search(r'cm_charger_type_polling:\s*update charger type:\s*(\d+)', msg)
    if m:
        event.event_type = "bc1p2"
        event.decoded = {"charger_type": int(m.group(1)), "method": "polling"}
        return

    # --- charger-manager: sprd_update_vchg_info ---
    # "sprd_vchg, sprd_update_vchg_info, usb_limit: 500000"
    m = re.search(r'sprd_update_vchg_info,\s*usb_limit:\s*(\d+)', msg)
    if m:
        event.event_type = "charger_limit"
        event.decoded = {"usb_limit_ua": int(m.group(1))}
        event.current_ma = int(m.group(1)) // 1000
        return
    # "sprd_vchg, usb_limit = -22uA"
    m = re.search(r'sprd_vchg,\s*usb_limit\s*=\s*(-?\d+)uA', msg)
    if m:
        event.event_type = "charger_limit"
        event.decoded = {"usb_limit_ua": int(m.group(1))}
        return

    # --- charger-manager: wireless charge config ---
    if "cm_wlc_ovp_enable" in msg:
        event.event_type = "charger_config"
        m = re.search(r'wlc_ovp_mode:\s*(\d+),\s*cmd:\s*(\d+)', msg)
        if m:
            event.decoded = {"wlc_ovp_mode": int(m.group(1)), "cmd": int(m.group(2))}
        return
    m = re.search(r'cm_set_primary_charge_wirless_type,\s*psy_name:\s*"([^"]+)".*set wirless type\s*=\s*(\d+)', msg)
    if m:
        event.event_type = "charger_config"
        event.decoded = {"psy_name": m.group(1), "wireless_type": int(m.group(2))}
        return

    # --- musb-sprd: resume/suspend ---
    if "musb-sprd" in msg and ("runtime_resume enter" in msg or "resume enter" in msg):
        event.event_type = "musb_resume"
        return
    if "musb-sprd" in msg and "resume_work enter" in msg:
        event.event_type = "musb_resume"
        event.decoded = {"phase": "work"}
        return

    # --- musb-sprd: external event (vbus, id, etc.) ---
    # "ext event: id 2, vbus 1, b_susp 0, a_recover 0, b_data 1"
    m = re.search(r'ext event:\s*id\s+(\d+),\s*vbus\s+(\d+),\s*b_susp\s+(\d+),\s*a_recover\s+(\d+),\s*b_data\s+(\d+)', msg)
    if m:
        event.event_type = "musb_extcon"
        event.decoded = {
            "id": int(m.group(1)),
            "vbus": int(m.group(2)),
            "b_susp": int(m.group(3)),
            "a_recover": int(m.group(4)),
            "b_data": int(m.group(5)),
        }
        return

    # --- musb-sprd: state machine ---
    m = re.search(r'sm_work:\s*(\S+)\s+state', msg)
    if m:
        event.event_type = "musb_state"
        event.decoded = {"state": m.group(1)}
        return

    # --- musb-sprd: waiting glue suspended ---
    if "waiting glue suspended" in msg:
        event.event_type = "musb_state"
        event.decoded = {"state": "waiting_glue_suspended"}
        return

    # --- musb-sprd: gadget control ---
    m = re.search(r'musb_sprd_otg_start_peripheral:\s*turn\s+(on|off)\s+gadget\s+(\S+)', msg)
    if m:
        event.event_type = "musb_gadget"
        event.decoded = {"action": m.group(1), "gadget": m.group(2)}
        return

    # --- musb-sprd: charger detection ---
    if "musb_sprd_chg_detect_work" in msg or "musb_sprd_retry_charger_detect" in msg:
        event.event_type = "musb_chg_detect"
        m = re.search(r'vbus_active\s+(\d+)', msg)
        if m:
            event.decoded = {"vbus_active": int(m.group(1))}
        return

    # --- musb-hdrc: runtime resume ---
    if "musb-hdrc" in msg and "runtime resume" in msg:
        event.event_type = "musb_state"
        event.decoded = {"state": "runtime_resume"}
        return

    # --- musb-hdrc: D+ pullup ---
    m = re.search(r'gadget D\+\s*pullup\s+(on|off)', msg)
    if m:
        event.event_type = "usb_pullup"
        event.decoded = {"d_plus_pullup": m.group(1) == "on"}
        return

    # --- sc27xx-typec: RP level ---
    # "sc27xx_typec_set_rp_level cc:3!"
    m = re.search(r'sc27xx_typec_set_rp_level\s*(\w+):(\d+)!', msg)
    if m:
        event.event_type = "typec_config"
        event.decoded = {"rp_config_dir": m.group(1), "rp_level": int(m.group(2))}
        return
    # "rp level: 80UA"
    m = re.search(r'rp level:\s*(\w+)', msg)
    if m:
        event.event_type = "typec_config"
        event.decoded = {"rp_level": m.group(1)}
        return

    # --- sc27xx-typec: timing ---
    # "SC27XX_MIN_TERR_CNT = 2737: 85 ms"
    m = re.search(r'SC27XX_MIN_TERR_CNT\s*=\s*(\d+):\s*(\d+)\s*ms', msg)
    if m:
        event.event_type = "typec_timing"
        event.decoded = {"terr_cnt": int(m.group(1)), "terr_ms": int(m.group(2))}
        return

    # --- Requesting new orientation (mux) ---
    m = re.search(r'Requesting new orientation\s+(\d+),\s*old orientation\s+(\d+)', msg)
    if m:
        event.event_type = "tcpm_config"
        event.decoded = {"new_orientation": int(m.group(1)), "old_orientation": int(m.group(2))}
        return

    # --- charger-manager: charged coulomb counter ---
    # "charged:  charge_set_batt_cc_uah: store raw_batt_cc_uah = 22900 to miscdata"
    m = re.search(r'charge_set_batt_cc_uah:\s*store raw_batt_cc_uah\s*=\s*(\d+)', msg)
    if m:
        event.event_type = "charger_monitor"
        event.decoded = {"raw_batt_cc_uah": int(m.group(1))}
        event.flags.append("COULOMB_COUNTER")
        return

    # --- sprd-hsphy: HS PHY init (noise — physical layer, not PD protocol) ---
    # These are handled by the noise filter in _extract_timeline

    # --- First negotiate ---
    if "first negotiate" in msg:
        event.flags.append("FIRST_NEGOTIATE")

    # --- PPS negotiation ---
    if "Requesting PDO" in msg and "9000 mV" in msg:
        event.flags.append("PPS_NEGOTIATE")


# ============================================================
# Extraction v2: Structured output
# ============================================================

def _detect_platform(raw_text: str) -> str:
    """Detect platform from log content."""
    if "sprd_tcpm_log" in raw_text or "sprd_pd_log" in raw_text:
        return "sprd"
    if "qcom_pd" in raw_text or "pmic_pd" in raw_text:
        return "qcom"
    if "mtk_tcpc" in raw_text or "mtk_pd" in raw_text:
        return "mtk"
    return "generic"


def _extract_timeline(all_lines: list[str]) -> list[TimelineEvent]:
    """Parse all log lines into TimelineEvent objects, filtering for protocol-relevant lines."""
    events = []
    only_noise_since = -1  # track consecutive noise lines

    for line in all_lines:
        event = parse_sprd_line(line)
        if event is None:
            continue

        # Skip events classified as "other" that are clearly noise
        # (GPU, audio, mmc, f2fs, display, etc.)
        if event.event_type == "other" and event.subsystem == "other":
            # Check if this is protocol noise or platform noise
            noise_keywords = [
                "GPU_DVFS", "mali GPU", "ASoC", "mmc", "f2fs",
                "type=1400", "gpu shader", "sprd_bcl", "sprd_pdbg",
                "healthd", "HealthLoop",
                "sprd-fgu", "audio_mem", "aud_smsg",
                "lpm_pwr_stats", "SPRD_PDBG", "battery l=",
                "sprd-sensor", "NVT-ts", "drm", "iolimit",
                "servicemanager", "ucp1301", "SPRD_PDBG",
                "sprd-dpdm", "unisoc_f2fs_stat", "Audio",
                "PCM]", "SIPC]", "Kcontrol]", "SC2730]",
                "SettingsProvide", "ScheduleBatteryUpdate",
                "tbat_bcl_level", "soc_temp_level", "soc_lvl",
                "bat_temp", "battery", "mem_type", "playback",
                "Caller(pid=", "buf=5",
                # Added 2026-10-12: more noise patterns
                "sprd_tp_panel_notifier", "sprd-hsphy",
                "it has processed", "|_iowait:",
                "unisoc_fsio_tp:", "unisoc_fragment:",
                "systemserver cmd", "sprd_hostphy_set",
            ]
            content = event.content_raw
            is_noise = False

            # Check noise keywords for events that remain unclassified
            for nk in noise_keywords:
                if nk in content:
                    is_noise = True
                    break

            if is_noise and event.subsystem == "other":
                continue

        events.append(event)

    # Assign sequential IDs
    for i, event in enumerate(events):
        event.id = i + 1

    return events


def _merge_pending_delayed(events: list[TimelineEvent]) -> list[TimelineEvent]:
    """
    Merge pending state changes with their corresponding delayed triggers.
    Sets pending_target_event_id on pending events to point to the delayed event.
    """
    # Build index: for each delayed event, find its matching pending
    # Match by (state_from, state_to) pair

    pending_map: dict[tuple[str, str], list[int]] = {}
    for evt in events:
        if evt.is_pending and evt.state_from and evt.state_to:
            key = (evt.state_from, evt.state_to)
            if key not in pending_map:
                pending_map[key] = []
            pending_map[key].append(evt.id)

    for evt in events:
        if evt.is_delayed and evt.state_from and evt.state_to:
            key = (evt.state_from, evt.state_to)
            if key in pending_map and pending_map[key]:
                pending_id = pending_map[key].pop(0)
                # Set backlink on pending event
                for pe in events:
                    if pe.id == pending_id:
                        pe.pending_target_event_id = evt.id
                        break

    return events


def _sort_timeline(events: list[TimelineEvent]) -> list[TimelineEvent]:
    """Sort by (kernel_ts ASC, cpu ASC, thread ASC)."""
    return sorted(events, key=lambda e: (e.kernel_ts, e.cpu, int(e.thread) if e.thread.isdigit() else 0))


def _group_hard_reset_phases(events: list[TimelineEvent]) -> list[dict]:
    """
    Group events into Hard Reset phases.

    A complete Hard Reset cycle consists of:
      1. HARD_RESET_SEND — the trigger (e.g., SourceCaps timeout)
      2. HARD_RESET_START → SNK_HARD_RESET_SINK_OFF → (pending delay) →
         SNK_HARD_RESET_SINK_ON
      3. Post-HR recovery: STARTUP → DISCOVERY → WAIT_CAPABILITIES (sub-phase)

    Pre-attach phases (VBUS_ON, ATTACH, TOGGLING, DEBOUNCE, ATTACHED) are
    NOT Hard Reset phases. Only HR-triggering and HR-state events are grouped.
    """
    phases = []

    # Collect only HR-related events
    hr_events = []
    for evt in events:
        state_str = f"{evt.state_from} -> {evt.state_to}" if evt.state_to else evt.content_raw
        is_hr = False
        for hr_state in ("HARD_RESET_SEND", "HARD_RESET_START",
                         "SNK_HARD_RESET_SINK_OFF", "SNK_HARD_RESET_SINK_ON"):
            if hr_state in state_str:
                is_hr = True
                break
        if is_hr or "HARD_RESET" in evt.flags:
            hr_events.append(evt)

    if not hr_events:
        return phases

    # Group consecutive HR events into cycles
    # A new cycle starts with HARD_RESET_SEND or HARD_RESET_START
    current_cycle = None

    for evt in hr_events:
        state_str = f"{evt.state_from} -> {evt.state_to}" if evt.state_to else evt.content_raw

        # Detect start of a new HR cycle
        is_new_cycle = False
        if "HARD_RESET_START" in state_str:
            if current_cycle is None:
                is_new_cycle = True
            elif current_cycle.get("has_sink_on"):
                is_new_cycle = True  # Previous cycle completed, new one starting
        elif "HARD_RESET_SEND" in state_str:
            if current_cycle is None:
                is_new_cycle = True

        if is_new_cycle:
            if current_cycle and current_cycle.get("event_ids"):
                phases.append(_finalize_hr_cycle(current_cycle, events))
            current_cycle = {
                "event_ids": [],
                "start_ts": evt.kernel_ts,
                "has_hard_reset_send": False,
                "has_hard_reset_start": False,
                "has_sink_off": False,
                "has_sink_on": False,
                "sub_phases": [],
            }

        if current_cycle is not None:
            current_cycle["event_ids"].append(evt.id)
            current_cycle["end_ts"] = evt.kernel_ts
            if "HARD_RESET_SEND" in state_str:
                current_cycle["has_hard_reset_send"] = True
            if "HARD_RESET_START" in state_str:
                current_cycle["has_hard_reset_start"] = True
            if "SNK_HARD_RESET_SINK_OFF" in state_str:
                current_cycle["has_sink_off"] = True
            if "SNK_HARD_RESET_SINK_ON" in state_str:
                current_cycle["has_sink_on"] = True

    # After the last HR state transition, find post-HR recovery sub-phases
    if current_cycle and current_cycle.get("has_sink_on"):
        _find_post_hr_recovery(current_cycle, events)

    # Flush last cycle
    if current_cycle and current_cycle.get("event_ids"):
        phases.append(_finalize_hr_cycle(current_cycle, events))

    return phases


def _find_post_hr_recovery(cycle: dict, events: list[TimelineEvent]) -> None:
    """Find post-HR recovery state transitions: STARTUP → DISCOVERY → WAIT_CAPABILITIES.

    These states come immediately after SNK_HARD_RESET_SINK_ON and represent
    the PD stack re-initializing after a Hard Reset.
    """
    last_hr_id = max(cycle["event_ids"])
    recovery_ids = []
    recovery_start = None

    for evt in events:
        if evt.id <= last_hr_id:
            continue
        if evt.event_type in ("state_change", "delayed_state_change"):
            state_to = evt.state_to or ""
            if state_to in ("SNK_STARTUP", "SNK_DISCOVERY", "SNK_WAIT_CAPABILITIES"):
                if recovery_start is None:
                    recovery_start = evt.kernel_ts
                recovery_ids.append(evt.id)
                cycle["event_ids"].append(evt.id)
                cycle["end_ts"] = evt.kernel_ts
            elif state_to == "SNK_READY":
                break  # Recovery complete, normal negotiation starts
            elif recovery_ids and state_to not in ("SNK_STARTUP", "SNK_DISCOVERY",
                                                     "SNK_WAIT_CAPABILITIES"):
                break  # Hit a non-recovery state

    if recovery_ids:
        cycle["sub_phases"].append({
            "phase_name": "POST_HR_RECOVERY",
            "event_ids": recovery_ids,
            "start_ts": recovery_start,
            "end_ts": events[recovery_ids[-1] - 1].kernel_ts if recovery_ids else 0,
        })


def _finalize_hr_cycle(cycle: dict, events: list[TimelineEvent]) -> dict:
    """Build the final hard_reset_phase dict from a raw cycle."""
    if cycle.get("has_sink_on"):
        phase_name = "HARD_RESET_COMPLETE"
    elif cycle.get("has_sink_off"):
        phase_name = "HARD_RESET_IN_PROGRESS"
    elif cycle.get("has_hard_reset_start"):
        phase_name = "HARD_RESET_STARTED"
    else:
        phase_name = "HARD_RESET_SEND"

    # Calculate delay for pending transitions within the cycle
    delay_ms = 0
    for eid in cycle["event_ids"]:
        evt = events[eid - 1] if eid <= len(events) else None
        if evt and evt.delay_ms:
            delay_ms = max(delay_ms, evt.delay_ms)

    description_parts = []
    sub_names = [sp["phase_name"] for sp in cycle.get("sub_phases", [])]
    if sub_names:
        description_parts.append(f"recovery={'→'.join(sub_names)}")

    return {
        "phase_name": phase_name,
        "event_ids": cycle["event_ids"],
        "start_ts": cycle["start_ts"],
        "end_ts": cycle["end_ts"],
        "delay_ms": delay_ms,
        "description": ", ".join(description_parts),
        "sub_phases": cycle.get("sub_phases", []),
    }


def _build_neg_cycle(events: list[TimelineEvent], neg_ids: list[int], cycle: int) -> dict:
    """Build a pd_negotiation dict from collected event IDs."""
    first_id = neg_ids[0]
    last_id = neg_ids[-1]
    start_ts = events[first_id - 1].kernel_ts if first_id <= len(events) else 0
    end_ts = events[last_id - 1].kernel_ts if last_id <= len(events) else 0

    neg = {
        "cycle": cycle,
        "label": f"PD Negotiation Round {cycle}",
        "event_ids": neg_ids,
        "start_ts": start_ts,
        "end_ts": end_ts,
    }

    # Find key messages within this negotiation
    for evt_id in neg_ids:
        evt = events[evt_id - 1] if evt_id <= len(events) else None
        if evt is None or not evt.decoded or not evt.decoded.get("pd_header_decoded"):
            continue

        hdr = evt.decoded["pd_header_decoded"]
        msg_type = hdr.get("message_type", "")

        # Determine direction from original log line content
        is_rx = "RX" in evt.content_raw
        is_tx = "TX" in evt.content_raw or "tx msg" in evt.content_raw

        if is_rx:
            if msg_type == "SOURCE_CAPABILITIES" and "source_cap" not in neg:
                neg["source_cap"] = _build_neg_message(evt)
            elif msg_type == "ACCEPT" and "accept" not in neg:
                neg["accept"] = _build_neg_message(evt)
            elif msg_type == "PS_RDY" and "ps_rdy" not in neg:
                neg["ps_rdy"] = _build_neg_message(evt)
        elif is_tx:
            if msg_type == "REQUEST" and "request" not in neg:
                neg["request"] = _build_neg_message(evt)

    # Determine result and label from last state
    last_state = ""
    for evt_id in reversed(neg_ids):
        evt = events[evt_id - 1] if evt_id <= len(events) else None
        if evt and evt.state_to:
            last_state = evt.state_to
            break

    if last_state == "SNK_READY":
        neg["label"] = f"PD Negotiation Round {cycle} ✓"
        for evt_id in reversed(neg_ids):
            evt = events[evt_id - 1] if evt_id <= len(events) else None
            if evt and evt.event_type == "voltage_current_limit":
                neg["result"] = {
                    "voltage_mv": evt.voltage_mv,
                    "current_ma": evt.current_ma,
                    "success": True,
                    "final_state": "SNK_READY",
                }
                if evt.voltage_mv == 9000:
                    neg["label"] = "PPS 9V Re-negotiation ✓"
                elif evt.voltage_mv == 5000:
                    neg["label"] = "5V Fixed PDO Negotiation ✓"
                break

    return neg


def _group_pd_negotiations(events: list[TimelineEvent]) -> list[dict]:
    """
    Group events into non-overlapping PD negotiation cycles.

    A negotiation cycle starts with SOURCE_CAPABILITIES (RX) and ends at
    SNK_READY or the next SOURCE_CAPABILITIES. PPS re-negotiation that
    happens AFTER SNK_READY (without a new SourceCaps) is detected by
    scanning for orphaned Request events.
    """
    negotiations = []

    # Find all SourceCaps event indices, deduplicating same-header duplicates
    # (same PD header appears from both sprd_tcpm_log and sprd_pd_log)
    src_cap_indices = []
    last_src_cap_raw = None
    last_src_cap_idx = -1
    for i, evt in enumerate(events):
        if evt.decoded and evt.decoded.get("pd_header_decoded", {}).get("message_type") == "SOURCE_CAPABILITIES":
            raw = evt.decoded.get("pd_header_raw", "")
            # Skip duplicate SourceCaps: same raw header within 10 events
            if raw and raw == last_src_cap_raw and (i - last_src_cap_idx) <= 10:
                continue
            src_cap_indices.append(i)
            last_src_cap_raw = raw
            last_src_cap_idx = i

    if not src_cap_indices:
        return negotiations

    src_cap_set = set(src_cap_indices)  # For O(1) boundary check in main loop

    NUKE_EVENT_TYPES = ("pd_rx", "pd_tx", "pd_header_raw", "pdo_entry",
                        "state_change", "delayed_state_change",
                        "pd_tx_complete", "pd_irq",
                        "voltage_current_limit", "charger_limit")

    covered_until = -1
    cycle = 0

    for src_idx in src_cap_indices:
        if src_idx <= covered_until:
            continue

        cycle += 1
        neg_ids = []

        for i in range(src_idx, len(events)):
            evt = events[i]

            # Stop BEFORE adding boundary event — use src_cap_set so
            # deduped duplicate SourceCaps don't prematurely cut the cycle
            if (i > src_idx and i in src_cap_set):
                covered_until = i - 1
                break
            if evt.event_type in ("state_change", "delayed_state_change") and evt.state_to == "SNK_READY":
                neg_ids.append(evt.id)
                covered_until = i
                break

            if evt.event_type in NUKE_EVENT_TYPES:
                neg_ids.append(evt.id)
        else:
            covered_until = len(events) - 1

        if not neg_ids:
            continue

        negotiations.append(_build_neg_cycle(events, neg_ids, cycle))

    # === PPS re-negotiation: scan for Request events after covered_until ===
    # PPS re-negotiation reuses APDOs from original SourceCaps, so there's no
    # new SourceCaps event. Detect by finding orphaned Request→Accept→PS_RDY
    # sequences that happen after the last covered SNK_READY.
    for i in range(covered_until + 1, len(events)):
        # Skip events already covered by a previous PPS cycle
        if i <= covered_until:
            continue
        evt = events[i]
        if (evt.decoded and evt.decoded.get("pd_header_decoded", {}).get("message_type") == "REQUEST"
                and evt.event_type not in ("pd_header_raw",)):
            # Backtrack to find the state transition that started this re-negotiation
            start_i = i
            for j in range(i - 1, covered_until, -1):
                if events[j].event_type in ("state_change", "delayed_state_change"):
                    if events[j].state_to in ("SNK_NEGOTIATE_CAPABILITIES",):
                        start_i = j
                        break
                    elif events[j].state_to == "SNK_READY":
                        break  # Don't cross SNK_READY boundary

            cycle += 1
            neg_ids = []

            for j in range(start_i, len(events)):
                ej = events[j]
                if ej.event_type in NUKE_EVENT_TYPES:
                    neg_ids.append(ej.id)

                # Stop at SNK_READY — re-negotiation complete
                if ej.event_type in ("state_change", "delayed_state_change") and ej.state_to == "SNK_READY":
                    covered_until = max(covered_until, j)
                    break
                # Stop at next SourceCaps — new independent negotiation
                if (j > start_i and ej.decoded
                        and ej.decoded.get("pd_header_decoded", {}).get("message_type") == "SOURCE_CAPABILITIES"):
                    break
            else:
                covered_until = len(events) - 1

            if not neg_ids:
                continue

            negotiations.append(_build_neg_cycle(events, neg_ids, cycle))

    return negotiations


def _build_neg_message(evt: TimelineEvent) -> dict:
    """Build a pd_negotiation_message dict from a timeline event."""
    msg = {
        "event_id": evt.id,
        "ts": evt.kernel_ts,
    }
    if evt.decoded:
        if evt.decoded.get("pd_header_raw"):
            msg["header_raw"] = evt.decoded["pd_header_raw"]
        if evt.decoded.get("pd_header_decoded"):
            msg["header_decoded"] = evt.decoded["pd_header_decoded"]
            msg["message_type"] = evt.decoded["pd_header_decoded"].get("message_type", "")
        if evt.decoded.get("pd_data"):
            msg["data_raw"] = evt.decoded["pd_data"]
        if evt.decoded.get("pdos"):
            msg["pdos"] = evt.decoded["pdos"]
    return msg


def _build_state_machine_summary(events: list[TimelineEvent]) -> dict:
    """Build state machine summary from timeline events."""
    states_visited = []
    transitions = []

    for evt in events:
        if evt.state_to and (not evt.is_pending):
            if evt.state_to not in states_visited:
                states_visited.append(evt.state_to)
            transitions.append({
                "from": evt.state_from,
                "to": evt.state_to,
                "event_id": evt.id,
                "ts": evt.kernel_ts,
                "delay_ms": evt.delay_ms,
                "is_delayed": evt.is_delayed,
                "is_pending": evt.is_pending,
            })

    return {
        "states_visited": states_visited,
        "transitions": transitions,
    }


def _detect_anomalies(events: list[TimelineEvent]) -> list[dict]:
    """Detect anomalies in the timeline."""
    anomalies = []

    # Hard Reset detection
    for evt in events:
        if "HARD_RESET" in evt.flags:
            if evt.event_type in ("delayed_state_change", "state_change") and "HARD_RESET" in evt.state_to:
                anomalies.append({
                    "type": "hard_reset",
                    "severity": "warning",
                    "event_id": evt.id,
                    "description": f"Hard Reset triggered: {evt.state_from} → {evt.state_to}",
                    "detail": evt.content_raw,
                })

    # Pending timeout detection
    pending_hard_reset_events = [e for e in events if e.is_pending and "HARD_RESET" in e.state_to]
    for pe in pending_hard_reset_events:
        anomalies.append({
            "type": "warning",
            "severity": "info",
            "event_id": pe.id,
            "description": f"Hard Reset timeout scheduled: {pe.state_from} → {pe.state_to} after {pe.delay_ms}ms",
            "detail": pe.content_raw,
        })

    # Disconnect detection
    for evt in events:
        if "DISCONNECT" in evt.flags:
            anomalies.append({
                "type": "disconnect",
                "severity": "info",
                "event_id": evt.id,
                "description": f"Device disconnected at ts={evt.kernel_ts:.3f}s",
                "detail": evt.content_raw,
            })

    return anomalies


def _build_charger_summary(events: list[TimelineEvent]) -> dict:
    """Build charger summary from charger_info events."""
    summary = {}
    for evt in events:
        if evt.event_type == "charger_info" and evt.charger_info:
            summary = {**summary, **evt.charger_info}
        if evt.event_type == "voltage_current_limit":
            summary["final_voltage_mv"] = evt.voltage_mv
            summary["final_current_ma"] = evt.current_ma

    return summary if summary else {}


# ============================================================
# Main extraction function (v2)
# ============================================================

def extract_structured(filepath: str, max_lines: int = 2000) -> dict:
    """
    Extract protocol events from a kernel log file and return structured JSON.

    Returns a dict conforming to schemas/extraction_output.schema.json
    """
    path = Path(filepath)
    if not path.exists():
        return {
            "metadata": {"error": f"File not found: {filepath}"},
            "timeline": [],
        }

    raw_text = path.read_text(encoding="utf-8", errors="replace")
    all_lines = raw_text.splitlines()
    total_lines = len(all_lines)

    # Detect platform
    platform = _detect_platform(raw_text)

    # Extract timeline
    events = _extract_timeline(all_lines)
    if len(events) > max_lines:
        events = events[:max_lines]

    # Sort by dual-index
    events = _sort_timeline(events)

    # Merge pending/delayed
    events = _merge_pending_delayed(events)

    # Build groups
    hard_reset_phases = _group_hard_reset_phases(events)
    pd_negotiations = _group_pd_negotiations(events)
    state_machine_summary = _build_state_machine_summary(events)
    anomalies = _detect_anomalies(events)
    charger_summary = _build_charger_summary(events)

    # Determine extraction confidence
    fmt_name = None
    fmt_label = "unknown"
    confidence = "unknown"

    for fname, fcfg in SPECIFIC_FORMATS.items():
        hits = sum(1 for line in all_lines if any(re.search(p, line) for p in fcfg["patterns"]))
        if hits >= fcfg["min_hits"]:
            fmt_name = fname
            fmt_label = fcfg["label"]
            confidence = "high"
            break

    if confidence == "unknown":
        # Check keyword matching
        kw_hits = sum(1 for line in all_lines if any(kw in line for kw in PROTOCOL_KEYWORDS))
        if kw_hits >= 10:
            confidence = "medium"
            fmt_label = "关键词匹配"

    # Build metadata
    time_range = {}
    if events:
        time_range["start_kernel_ts"] = events[0].kernel_ts
        time_range["end_kernel_ts"] = events[-1].kernel_ts
        if events[0].wall_clock:
            time_range["start_wall"] = events[0].wall_clock
        if events[-1].wall_clock:
            time_range["end_wall"] = events[-1].wall_clock

    # Detect chip
    chip = ""
    if "sc27xx" in raw_text.lower():
        chip = "SC2730"

    # Detect protocol types
    protocol_types = []
    pd_markers = ["PD TX", "PD RX", "SOURCE_CAPABILITIES", "REQUEST", "PS_RDY", "ACCEPT"]
    cc_markers = ["CC1:", "CC2:", "TOGGLING", "ATTACH_WAIT"]
    if any(m in raw_text for m in pd_markers):
        protocol_types.append("PD")
    if any(m in raw_text for m in cc_markers):
        protocol_types.append("CC")
    if "charger-manager" in raw_text:
        protocol_types.append("CHARGER")
    if not protocol_types:
        protocol_types.append("UNKNOWN")

    result = {
        "metadata": {
            "source_file": filepath,
            "platform": platform,
            "chip": chip,
            "extraction_level": confidence,
            "matched_format": fmt_name,
            "format_label": fmt_label,
            "total_log_lines": total_lines,
            "extracted_event_count": len(events),
            "protocol_types": protocol_types,
            "time_range": time_range,
        },
        "timeline": [e.to_dict() for e in events],
        "hard_reset_phases": hard_reset_phases,
        "pd_negotiations": pd_negotiations,
        "state_machine_summary": state_machine_summary,
        "anomalies": anomalies,
    }

    if charger_summary:
        result["charger_summary"] = charger_summary

    return result


# ============================================================
# Legacy API (backward compatible)
# ============================================================

def clean_line(line: str, matched_format: Optional[str] = None) -> str:
    """Legacy line cleaner. Kept for backward compatibility."""
    m = re.search(r'\[sprd_tcpm_log\]\s*(.+)', line)
    if m:
        return f"[TCPM] {m.group(1)}"
    m = re.search(r'\[sprd_pd_log\]\s*(.+)', line)
    if m:
        return f"[PD] {m.group(1)}"
    m = re.search(r'\[sc27xx-typec-pd[^\]]*\]\s*(.+)', line)
    if m:
        return f"[SC27XX] {m.group(1)}"
    m = re.search(r'\[charger-manager[^\]]*\]\s*(.+)', line)
    if m:
        return f"[CHG] {m.group(1)}"
    m = re.search(r'power_supply\s+\S+:\s*(.+)', line)
    if m:
        return f"[PSY] {m.group(1)}"
    line = re.sub(r'^[0-9A-Fa-f]+\s+< *\d+>\s*', '', line)
    line = re.sub(r'^\[\s*[\d.]+\s*\](?:\s*\[[\d\-:\s.]+\]\s*)?T\d+@C\d+;\s*', '', line)
    line = re.sub(r'^\[\d+\s*/\s*\d+\]\s*', '', line)
    return line.strip()


def extract_timestamp(line: str) -> Optional[float]:
    """Legacy timestamp extractor."""
    m = re.search(r'\[\s*([\d.]+)\s*\]', line)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass
    m = re.search(r'\[(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+)\]', line)
    if m:
        from datetime import datetime
        try:
            dt = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S.%f")
            return dt.timestamp()
        except ValueError:
            pass
    return None


def _sort_and_join(lines: list[str]) -> str:
    """Legacy sort-and-join."""
    timed = []
    for line in lines:
        ts = extract_timestamp(line)
        timed.append((ts if ts is not None else 0, line))
    timed.sort(key=lambda x: x[0])
    return "\n".join(line for _, line in timed)


def _detect_types(text: str) -> list[str]:
    """Legacy protocol type detector."""
    types = []
    pd_markers = [
        "SRC_CAP", "SNK_CAP", "PS_RDY", "PR_SWAP", "PD TX", "PD RX",
        "PDO", "pd_protocol", "sprd_pd_log", "sprd_tcpm_log",
        "header: 0x", "header = 0x", "REQUEST", "ACCEPT",
    ]
    cc_markers = [
        "CC1:", "CC2:", "TOGGLING", "ATTACH_WAIT", "ATTACHED",
        "typec", "type_c", "VCONN", "Rp=", "Rd=",
        "SNK_UNATTACHED", "SNK_READY", "polarity",
    ]
    usb_markers = [
        "GET_DESCRIPTOR", "SET_ADDRESS", "Device Descriptor",
        "enumeration", "idVendor", "idProduct", "bcdUSB",
        "usb_core", "Config Descriptor",
    ]
    if any(m in text for m in pd_markers):
        types.append("PD")
    if any(m in text for m in cc_markers):
        types.append("CC")
    if any(m in text for m in usb_markers):
        types.append("USB")
    return types if types else ["UNKNOWN"]


def extract(filepath: str, max_lines: int = 1000) -> dict:
    """Legacy extraction API. Kept for backward compatibility."""
    path = Path(filepath)
    if not path.exists():
        return {
            "confidence": "unknown",
            "error": f"File not found: {filepath}",
            "text": "",
        }

    raw_text = path.read_text(encoding="utf-8", errors="replace")
    all_lines = raw_text.splitlines()
    total_lines = len(all_lines)

    # Level 0: Specific format
    for fmt_name, fmt_cfg in SPECIFIC_FORMATS.items():
        matched = []
        for line in all_lines:
            if any(re.search(p, line) for p in fmt_cfg["patterns"]):
                matched.append(line)
        if len(matched) >= fmt_cfg["min_hits"]:
            cleaned = [clean_line(l, fmt_name) for l in matched]
            text = _sort_and_join(cleaned)
            return {
                "confidence": "high",
                "matched_format": fmt_name,
                "format_label": fmt_cfg["label"],
                "total_lines": total_lines,
                "filtered_lines": len(cleaned),
                "protocol_types": _detect_types(text),
                "text": text,
            }

    # Level 1: Keyword match
    matched = []
    for line in all_lines:
        for kw in PROTOCOL_KEYWORDS:
            if kw in line:
                matched.append(line)
                break
        if len(matched) >= max_lines:
            break

    if len(matched) >= 10:
        cleaned = [clean_line(l) for l in matched]
        text = _sort_and_join(cleaned)
        return {
            "confidence": "medium",
            "matched_format": "keyword_match",
            "format_label": "关键词匹配",
            "total_lines": total_lines,
            "filtered_lines": len(cleaned),
            "protocol_types": _detect_types(text),
            "text": text,
            "warnings": ["未命中特定格式提取器，使用关键词匹配（中置信度）"],
        }

    # Level 2: Fallback
    matched = []
    for line in all_lines:
        line_lower = line.lower()
        for kw in FALLBACK_KEYWORDS:
            if kw.lower() in line_lower:
                matched.append(line)
                break
        if len(matched) >= max_lines:
            break

    if len(matched) > 0:
        cleaned = [clean_line(l) for l in matched]
        text = _sort_and_join(cleaned)
        return {
            "confidence": "low",
            "matched_format": "fallback",
            "format_label": "超宽匹配（兜底）",
            "total_lines": total_lines,
            "filtered_lines": len(cleaned),
            "protocol_types": _detect_types(text),
            "text": text,
            "warnings": [
                "未命中特定格式和关键词提取器",
                "使用超宽匹配，可能包含大量噪音",
                "建议人工确认提取结果",
            ],
        }

    # Level 3: Raw tail
    tail_lines = all_lines[-200:]
    text = "\n".join(tail_lines)
    return {
        "confidence": "unknown",
        "matched_format": "raw_tail",
        "format_label": "裸传（尾部200行）",
        "total_lines": total_lines,
        "filtered_lines": len(tail_lines),
        "protocol_types": [],
        "text": text,
        "warnings": [
            "⚠️ 所有提取器均未命中！",
            "已返回日志尾部 200 行原始内容",
            "请 AI 判断是否包含协议交互内容",
        ],
    }


# ============================================================
# CLI
# ============================================================

def main():
    if len(sys.argv) < 2:
        print("协议日志提取器 v2.0")
        print()
        print("用法: python smart_extractor.py <logfile> [--v2] [--max N] [--text]")
        print()
        print("模式:")
        print("  --v2       结构化提取（推荐），输出 schema-compliant JSON")
        print("  (默认)     渐进式提取（向后兼容），输出 legacy JSON")
        print()
        print("选项:")
        print("  --max N    最大提取行数 (默认: v2=2000, legacy=1000)")
        print("  --text     仅输出文本（legacy 模式）")
        print("  --pretty   JSON 格式化输出 (v2 模式)")
        sys.exit(1)

    logfile = sys.argv[1]
    use_v2 = "--v2" in sys.argv
    max_lines = 2000 if use_v2 else 1000
    text_only = "--text" in sys.argv
    pretty = "--pretty" in sys.argv

    for i, arg in enumerate(sys.argv):
        if arg == "--max" and i + 1 < len(sys.argv):
            max_lines = int(sys.argv[i + 1])

    if use_v2:
        result = extract_structured(logfile, max_lines)
        indent = 2 if pretty else None
        print(json.dumps(result, ensure_ascii=False, indent=indent, default=str))
    else:
        result = extract(logfile, max_lines)
        if text_only:
            print(result.get("text", ""))
            if result.get("warnings"):
                print("\n--- 警告 ---")
                for w in result["warnings"]:
                    print(f"  {w}")
        else:
            output = {k: v for k, v in result.items() if k != "text"}
            output["text_preview"] = result.get("text", "")[:500]
            output["text_length"] = len(result.get("text", ""))
            print(json.dumps(output, ensure_ascii=False, indent=2))
            print("\n--- 完整文本请用 --text 参数输出 ---")


if __name__ == "__main__":
    main()