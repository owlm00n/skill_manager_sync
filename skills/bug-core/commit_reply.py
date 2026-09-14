import sys
sys.path.insert(0, r'C:\Users\xianjun.zeng\.claude\skills\bug-core')
from bug_core import bug_commit

comment = """针对PATCH20012527

Q: 这个change修改内容是什么？影响模块有哪些？
A: 修改内容包含两部分：
1. efuse API接口替换（Pmic_Efuse_Por_Read -> EfiPmicEfuseRead），接口参数和功能完全等价，无功能变化；同时修复了DCDC ZCD校准循环中shft变量未重算的问题，确保每个DCDC通道的校准值写入到正确的寄存器bit位；
2. 新增pmic_oc_level_reinit()函数，从efuse block 23读取vendor ID，仅当vendor_id==0x02（tps510g版本）时修改CPU DCDC过流保护level。

影响模块：bootloader edk2阶段PMIC regulator初始化，修改文件Regulator2730.c。

Q: 修改的具体影响是什么？
A: 0001 patch的efuse接口替换功能等价，无实际影响；shft修复确保ZCD校准值写入正确bit位。0002 patch仅对tps510g版本PMIC的CPU DCDC过流保护阈值做调整，非tps510g版本不受影响。

Q: 需要做哪些测试以及压力测试？
A: 多次开关机验证PMIC上电正常即可。若PMIC为tps510g版本，建议增加CPU高负载压力测试验证OCP不会误触发。

Q: 该项目和SomaliaA项目共线，是否影响老的项目？如果影响需要做哪些测试？
A: 基本不影响。efuse接口替换功能等价，对SomaliaA无实质影响。OCP level修改仅在SomaliaA PMIC为tps510g版本时生效。建议SomaliaA做开关机验证即可，若为tps510g版本增加CPU压力测试。"""

result = bug_commit(
    bug_id='SPCSS01698559',
    comment_text=comment,
    new_status='needinfo',
    instance='unisoc',
    use_combined=True,
)
print(result)