"""Domain lexicons and the adjacency graph.

The graph is the heart of the joke. Two domains are adjacent when they share a
*property* (mixing, curing, cycles, diagnosis) but not an *ontology*. The agent
uses the shared property to stay relevant and the ontological gap to be wrong.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Domain:
    key: str
    name: str
    entities: tuple[str, ...]
    predicates: tuple[str, ...]
    units: tuple[str, ...]
    standards: tuple[str, ...]
    metrics: tuple[str, ...]
    failures: tuple[str, ...]
    states: tuple[str, ...]
    neighbors: tuple[tuple[str, str], ...] = ()


DOMAINS: dict[str, Domain] = {
    "civil": Domain(
        key="civil",
        name="土木工程",
        entities=("混凝土", "钢筋", "模板", "承台", "梁柱", "试块", "骨料", "砂浆", "膨胀剂", "水化热"),
        predicates=("浇筑", "养护", "拆模", "振捣", "配筋", "回填", "张拉", "收面", "沉降"),
        units=("MPa", "kN", "mm", "m³", "d", "%"),
        standards=("GB/T 2024-42", "JGJ 55-2011", "GB 50010-2010", "CECS 220:2007"),
        metrics=("抗压强度", "坍落度", "弹性模量", "水灰比", "养护龄期"),
        failures=("蜂窝麻面", "离析", "泌水", "裂缝", "碳化", "冻融破坏"),
        states=("初凝", "终凝", "表面成型", "内部水化"),
        neighbors=(("cooking", "配比与养护"), ("finance", "周期与风险"), ("printing", "模板与成型")),
    ),
    "cooking": Domain(
        key="cooking",
        name="烹饪",
        entities=("面团", "高汤", "黄油", "酵母", "淀粉", "蛋白霜", "意面", "铸铁锅", "烤箱", "保鲜膜"),
        predicates=("醒面", "焯水", "收汁", "打发", "发酵", "过筛", "腌制", "回温"),
        units=("℃", "分钟", "克", "毫升", "卡路里"),
        standards=("GB 2760-2024", "ISO 22000", "QB/T 2024-7"),
        metrics=("含水量", "筋度", "糖度", "中心温度", "美拉德反应程度"),
        failures=("塌陷", "回缩", "出水", "夹生", "糊底"),
        states=("断生", "上色", "起筋", "乳化"),
        neighbors=(("civil", "配比与凝固"), ("agriculture", "生长与采收"), ("music", "层次与节奏")),
    ),
    "finance": Domain(
        key="finance",
        name="金融",
        entities=("现金流", "杠杆", "久期", "保证金", "基差", "期权", "资产负债表", "流动性"),
        predicates=("对冲", "平仓", "加杠杆", "折现", "计提", "展期", "套保"),
        units=("bp", "%", "倍", "元", "天"),
        standards=("IFRS 9", "Basel III", "GB/T 2024-88"),
        metrics=("夏普比率", "最大回撤", "久期缺口", "流动比率", "隐含波动率"),
        failures=("挤兑", "穿仓", "流动性枯竭", "期限错配"),
        states=("敞口", "净值", "估值"),
        neighbors=(("weather", "周期与预测"), ("agriculture", "周期与收成"), ("civil", "杠杆与结构")),
    ),
    "weather": Domain(
        key="weather",
        name="气象",
        entities=("冷锋", "副热带高压", "积雨云", "露点", "气压梯度", "急流", "逆温层"),
        predicates=("过境", "抬升", "凝结", "辐合", "平流", "消散"),
        units=("hPa", "℃", "m/s", "mm", "%"),
        standards=("WMO-No. 8", "GB/T 35221-2017"),
        metrics=("相对湿度", "露点温度", "风速切变", "降水概率"),
        failures=("预报偏差", "模式漂移", "空报", "漏报"),
        states=("不稳定", "饱和", "过冷"),
        neighbors=(("finance", "预测与风险"), ("astronomy", "观测与模型"), ("agriculture", "积温与降水")),
    ),
    "auto": Domain(
        key="auto",
        name="汽车维修",
        entities=("火花塞", "变速箱", "节气门", "三元催化", "悬挂", "刹车片", "ECU", "正时皮带"),
        predicates=("点火", "换挡", "标定", "举升", "四轮定位", "路试"),
        units=("N·m", "km", "L/100km", "V", "Ω"),
        standards=("ISO 26262", "GB 7258-2017", "SAE J1930"),
        metrics=("缸压", "点火提前角", "空燃比", "刹车片厚度"),
        failures=("爆震", "失火", "异响", "拖刹", "烧机油"),
        states=("怠速", "闭环", "开环", "热车"),
        neighbors=(("medicine", "诊断与保养"), ("programming", "标定与故障"), ("sports", "负荷与恢复")),
    ),
    "law": Domain(
        key="law",
        name="法律",
        entities=("条款", "管辖", "诉讼时效", "举证责任", "合同相对性", "善意取得"),
        predicates=("起诉", "抗辩", "送达", "保全", "释明", "上诉"),
        units=("日", "年", "元", "次"),
        standards=("民法典第 2024 条", "民诉法解释第 42 条"),
        metrics=("胜诉率", "赔偿额", "审理周期"),
        failures=("超过时效", "主体不适格", "管辖异议"),
        states=("生效", "待决", "已决"),
        neighbors=(("gardening", "边界与修剪"), ("printing", "条款与版本"), ("civil", "结构与责任")),
    ),
    "gardening": Domain(
        key="gardening",
        name="园艺",
        entities=("砧木", "接穗", "腐殖土", "根系", "花芽", "菌根", "覆盖物"),
        predicates=("嫁接", "修剪", "换盆", "扦插", "追肥", "控水"),
        units=("pH", "℃", "天", "厘米", "升"),
        standards=("NY/T 2024-3", "GB/T 8321"),
        metrics=("成活率", "坐果率", "土壤 EC 值", "叶面积指数"),
        failures=("徒长", "烂根", "黄化", "僵苗"),
        states=("缓苗", "抽梢", "休眠"),
        neighbors=(("law", "边界与修剪"), ("agriculture", "土壤与生长"), ("medicine", "修剪与愈合")),
    ),
    "programming": Domain(
        key="programming",
        name="软件工程",
        entities=("缓存", "线程池", "垃圾回收", "索引", "事务", "编译器", "序列化", "内存页"),
        predicates=("编译", "反序列化", "加锁", "回滚", "预热", "分片", "限流"),
        units=("MB", "ms", "QPS", "核", "GB"),
        standards=("RFC 9110", "POSIX", "GB/T 2024-11"),
        metrics=("吞吐量", "P99 延迟", "缓存命中率", "GC 停顿"),
        failures=("死锁", "内存泄漏", "缓存击穿", "惊群"),
        states=("冷启动", "热加载", "阻塞"),
        neighbors=(("printing", "排版与版本"), ("auto", "标定与故障"), ("finance", "事务与一致性")),
    ),
    "printing": Domain(
        key="printing",
        name="印刷",
        entities=("印版", "铅字", "装订线", "出血", "网目", "油墨", "折页", "书脊"),
        predicates=("排版", "晒版", "套印", "锁线", "覆膜", "裁切"),
        units=("gsm", "dpi", "mm", "色", "印"),
        standards=("ISO 12647", "GB/T 9851"),
        metrics=("套准精度", "墨层厚度", "折页误差"),
        failures=("重影", "墨杠", "透印", "爬移"),
        states=("单色", "四色", "过油"),
        neighbors=(("programming", "版本与排版"), ("music", "频谱与套印"), ("law", "条款与版本")),
    ),
    "astronomy": Domain(
        key="astronomy",
        name="天文学",
        entities=("轨道", "红移", "视星等", "主序带", "引力透镜", "暗物质晕"),
        predicates=("观测", "定标", "拟合", "巡天", "掩星"),
        units=("AU", "pc", "光年", "等", "km/s"),
        standards=("IAU 2015", "IAU 2024-42"),
        metrics=("光度", "周期", "轨道半长轴", "金属丰度"),
        failures=("视差误差", "消光", "混叠"),
        states=("主序", "红巨", "白矮"),
        neighbors=(("weather", "观测与模型"), ("sports", "周期与极限"), ("finance", "周期与风险")),
    ),
    "music": Domain(
        key="music",
        name="音乐",
        entities=("泛音", "拍号", "混响", "动态范围", "音色", "声部"),
        predicates=("编曲", "混音", "母带", "移调", "对位"),
        units=("BPM", "dB", "Hz", "小节"),
        standards=("MIDI 2.0", "ITU-R BS.1770"),
        metrics=("响度", "动态范围", "频谱重心"),
        failures=("削波", "相位抵消", "混浊"),
        states=("干声", "湿声", "过载"),
        neighbors=(("printing", "频谱与套印"), ("cooking", "层次与节奏"), ("sports", "节奏与负荷")),
    ),
    "agriculture": Domain(
        key="agriculture",
        name="农业",
        entities=("土壤墒情", "氮肥", "灌溉", "根系", "光合作用", "积温", "轮作"),
        predicates=("施肥", "灌溉", "播种", "收割", "覆膜", "间作"),
        units=("kg/亩", "℃", "mm", "%", "天"),
        standards=("NY/T 2024-9", "GB/T 33469"),
        metrics=("产量", "千粒重", "叶绿素含量", "土壤有机质"),
        failures=("倒伏", "贪青", "烧苗", "板结"),
        states=("分蘖", "拔节", "灌浆"),
        neighbors=(("gardening", "生长与土壤"), ("weather", "积温与降水"), ("finance", "周期与收成")),
    ),
    "medicine": Domain(
        key="medicine",
        name="医学",
        entities=("炎症", "代谢", "免疫", "剂量", "病程", "指标"),
        predicates=("诊断", "用药", "复查", "干预"),
        units=("mg", "ml", "mmol/L"),
        standards=("临床指南 2024",),
        metrics=("血压", "血糖", "白细胞"),
        failures=("误诊", "耐药", "并发症"),
        states=("急性", "慢性", "缓解"),
        neighbors=(("auto", "诊断与保养"), ("sports", "负荷与恢复"), ("gardening", "修剪与愈合")),
    ),
    "sports": Domain(
        key="sports",
        name="运动训练",
        entities=("最大摄氧量", "乳酸阈值", "训练负荷", "肌腱", "核心", "周期化"),
        predicates=("热身", "拉伸", "冲刺", "恢复", "减量"),
        units=("bpm", "km", "周", "%"),
        standards=("ACSM 2024", "ISSN 2024"),
        metrics=("心率漂移", "配速", "功率体重比"),
        failures=("过度训练", "拉伤", "平台期"),
        states=("有氧", "无氧", "恢复"),
        neighbors=(("medicine", "负荷与恢复"), ("auto", "调校与极限"), ("astronomy", "周期与极限")),
    ),
}


# Terms that are useful for domain detection but are not the domain's core
# entities. Longer keys win when two terms overlap.
ALIASES: dict[str, str] = {
    "水泥": "civil",
    "工地": "civil",
    "装修": "civil",
    "承重墙": "civil",
    "面条": "cooking",
    "厨房": "cooking",
    "菜谱": "cooking",
    "股票": "finance",
    "基金": "finance",
    "理财": "finance",
    "下雨": "weather",
    "台风": "weather",
    "天气预报": "weather",
    "汽车": "auto",
    "发动机": "auto",
    "保养": "auto",
    "合同": "law",
    "律师": "law",
    "官司": "law",
    "养花": "gardening",
    "植物": "gardening",
    "代码": "programming",
    "程序": "programming",
    "数据库": "programming",
    "python": "programming",
    "java": "programming",
    "docker": "programming",
    "git": "programming",
    "排版": "printing",
    "印刷": "printing",
    "星星": "astronomy",
    "宇宙": "astronomy",
    "音乐": "music",
    "编曲": "music",
    "种地": "agriculture",
    "施肥": "agriculture",
    "医生": "medicine",
    "健康": "medicine",
    "跑步": "sports",
    "健身": "sports",
}


def _build_term_index() -> dict[str, str]:
    index: dict[str, str] = {}
    for domain in DOMAINS.values():
        for term in (
            domain.entities
            + domain.metrics
            + domain.failures
            + domain.states
            + domain.predicates
        ):
            index[term] = domain.key
    index.update(ALIASES)
    # Longest-first lookup is handled by the parser.
    return index


TERM_TO_DOMAIN: dict[str, str] = _build_term_index()

SAFE_DOMAIN_KEYS: tuple[str, ...] = (
    "civil",
    "cooking",
    "finance",
    "weather",
    "auto",
    "law",
    "gardening",
    "programming",
    "printing",
    "astronomy",
    "music",
    "agriculture",
    "sports",
)


def get_domain(key: str) -> Domain:
    return DOMAINS[key]


def neighbors_of(key: str) -> tuple[tuple[str, str], ...]:
    return DOMAINS[key].neighbors
