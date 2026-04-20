# Milky Way Spot Scout

`Milky Way Spot Scout` 是一个面向银河摄影选点的 Codex Skill，用来比较候选拍摄地，并基于真实天气、月亮窗口、银河核心几何、光污染和出行风险给出结构化推荐。

这个仓库包含：

- `SKILL.md`
  Skill 主文档，定义使用场景、工作流、数据契约和输出契约。
- `references/`
  参考文档，包含数据源规范、研究检查清单和评分模型。
- `scripts/rank_spots.py`
  排名脚本，接收候选点 JSON，输出 Markdown / JSON / both 格式结果。
- `tests/`
  最小样例与回归测试。
- `agents/openai.yaml`
  Skill 的默认入口配置。

## 这个 Skill 解决什么问题

这个 Skill 用来回答一个更具体的问题：在给定的拍摄窗口内，几个候选点里哪一个更适合出发。

这个 Skill 重点解决：

- 明确拍摄窗口，而不是泛泛地按整晚条件判断
- 把月亮是否压窗作为硬门槛处理
- 强调实时/预报天气，避免用历史均值误导决策
- 把银河核心高度/方位和前景方向一起考虑
- 把交通、停车、步行风险纳入最终排序
- 输出可审计的分项分数和逐块来源

## 核心能力

- 比较多个银河摄影候选点
- 基于真实或预报天气进行排序
- 检查月亮是否干扰指定拍摄窗口
- 评估银河核心在窗口内的高度和方位
- 结合光污染、城市光害方向、海拔、地平线开阔度做基线判断
- 结合车程、停车风险、步行风险做实用性排序
- 输出中文结构化推荐结果

## 输入数据要点

每个候选点建议至少包含这些字段：

- 基础信息：`name`、`region`、`latitude`、`longitude`
- 观测窗口：`shooting_window_start_local`、`shooting_window_end_local`
- 月亮：`moonrise_local`、`moonset_local`、`moon_window_status`
- 天气：`cloud_cover_pct`、`humidity_pct`、`visibility_km`
- 天气附加风险：`smoke_risk_score`、`haze_risk_score`
- 暗空基线：`light_pollution_bortle` 或 `sqm`、`elevation_m`
- 城市光害：`city_glow_direction`、`city_glow_severity_score`
- 银河几何：`milky_way_core_altitude_deg`、`milky_way_core_azimuth_deg`
- 实用性：`drive_hours`、`access_score`、`safety_score`、`parking_risk_score`、`walking_risk_score`
- 元信息：`forecast_confidence`、`retrieved_at_local`、`sources_by_metric`

说明：

- `weather_data_kind` 必须是 `realtime`、`near-realtime` 或 `forecast` 之一
- 风险类字段支持 `0-100` 或 `1-5`
- 风险分值越高表示越差

## 输出特点

默认输出是中文结构化结果，包含：

- 排名摘要表
- 每个点的详细评分卡
- 每个评分块后的 `来源：...`
- 数据新鲜度说明

输出顺序优先展示天气，其次是暗空、月亮、银河几何和交通安全。短期出行决策里，天气和月亮窗口通常比暗空等级更重要。

## 使用方式

### 1. 直接运行脚本

```bash
python3 scripts/rank_spots.py input.json --format markdown
```

支持的输出格式：

- `markdown`
- `json`
- `both`

### 2. 运行测试

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```

### 3. 作为 Codex Skill 使用

把仓库中的 Skill 内容放到 Codex 的 skill 目录后，可以通过如下方式触发：

```text
Use $milky-way-spot-scout to compare Milky Way photography locations...
```

## 评分思路

默认分成五个大类：

- 天气：30
- 暗空基线：20
- 月亮窗口：20
- 银河几何：20
- 交通与安全：10

其中：

- 月亮窗口失败会触发总分封顶
- 天气不是实时/近实时/预报时，候选点不应被推荐
- 云量优先级高于其他天气指标
- 暗空分不会压过糟糕天气和压窗月亮

## 仓库结构

```text
.
├── SKILL.md
├── README.md
├── agents/
├── references/
├── scripts/
└── tests/
```

## 后续可优化方向

- 增加自动采集候选点数据的脚本
- 引入 schema 校验，提前发现字段缺失和格式错误
- 增加更多真实案例 fixture
- 提供更稳定的天气多源交叉校验
- 加入前景题材模板，例如湖面倒影、峡谷石林、草原天际线

## 适合谁

- 想在出发前做一次严谨银河选点的人
- 需要把“天气、月亮、暗空、交通”一起纳入判断的人
- 想把口头经验沉淀成可复用决策流程的人
