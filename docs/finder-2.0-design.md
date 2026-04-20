# Finder 2.0 设计方案

## 1. 设计结论

`ai-goofish-finder` 不应继续被设计成“带一个 radar 页的监控系统”，而应升级为：

> 一个围绕“方向 → 扩词 → 验证 → 推荐 → 学习”闭环运转的关键词自动发现引擎。

用户不再需要手动准备大量关键词，只需要给一个大体方向，例如：

- AI 绘画变现
- 小红书运营
- 考研资料
- 抖音剪辑副业
- 自动发货虚拟商品

系统负责完成：

1. 自动扩展候选关键词
2. 自动抓取并验证市场证据
3. 自动筛出值得测试的词
4. 自动生成任务草稿或实验任务
5. 持续根据运行结果学习和修正推荐

---

## 2. Finder 与 Monitor 的边界

### 2.1 Monitor 的职责

`ai-goofish-monitor` 的核心是“任务执行器”：

- 用户提供关键词 / 规则
- 系统按任务抓取商品
- AI 或规则判断推荐结果
- 结果展示、通知、导出

它优化的是：**任务执行稳定性与结果可见性**。

### 2.2 Finder 的职责

`ai-goofish-finder` 的核心应是“机会发现器”：

- 用户只提供方向
- 系统自己构造候选词图谱
- 系统自己分析近期市场信号
- 系统输出“下一批值得测试的词”
- 系统把高潜词送到任务系统做验证

它优化的是：**从原始商品流里持续提炼出可执行的关键词机会**。

### 2.3 一句话边界

- `monitor`：管任务
- `finder`：管机会

任务只是 finder 的下游执行器，不应再是 finder 的中心对象。

---

## 3. 当前仓库已经具备的基础能力

当前 `ai-goofish-finder` 已经有非常好的 1.5 阶段基础，可直接复用：

### 3.1 已有后端能力

- `src/services/result_storage_service.py`
  - 已把抓取结果沉淀到 `result_items`
- `src/infrastructure/persistence/sqlite_bootstrap.py`
  - 已完成 JSONL → SQLite 的迁移基座
- `src/services/radar_service.py`
  - 已支持关键词聚合、标注、词池、快照、推荐
- `src/services/task_generation_service.py`
  - 已支持 AI 任务生成作业状态
- `src/api/routes/tasks.py`
  - 已支持任务草稿与任务创建

### 3.2 已有前端能力

- `web-ui/src/views/RadarView.vue`
  - 已具备雷达页、推荐、标注、词池、任务草稿跳转
- `web-ui/src/composables/useRadar.ts`
  - 已封装 radar 的数据读写流程

### 3.3 已有数据层能力

当前 SQLite 已有如下关键表：

- `tasks`
- `result_items`
- `price_snapshots`
- `keyword_annotations`
- `radar_keyword_pool`
- `radar_snapshot_runs`
- `radar_snapshot_keywords`
- `radar_keyword_recommendations`

这些能力说明：

> Finder 不需要从零开始重构，而是要把现有 radar 从“关键词统计页”升级成“方向驱动的发现闭环”。

---

## 4. 当前版本的核心问题

### 4.1 缺少“方向”这个顶层对象

现在系统默认从“关键词任务”出发，而不是从“用户方向”出发。

问题：

- 用户仍然需要先想到关键词
- radar 只能在已有关键词上做二次聚合
- 无法明确一组词为什么属于同一个研究主题

### 4.2 推荐词更像静态拼词，而不是实验假设

当前推荐逻辑主要根据 signal term 拼接变体词，这个 MVP 是有效的，但还不够：

- 没有候选词生命周期
- 没有明确的“待验证 / 已验证 / 已放弃”状态
- 没有把推荐结果和后续任务效果绑定起来

### 4.3 评分是单分值，解释能力有限

当前 `opportunity_score` 已经能工作，但仅靠一个分数会有问题：

- 无法解释为什么推荐它
- 无法知道分数变化来自哪一维
- 后续难以做学习与调参

### 4.4 Radar Service 已经开始膨胀

`src/services/radar_service.py` 同时承担了：

- 聚合
- 评分
- 标注
- 词池管理
- 推荐生成
- 快照读写

继续追加“方向、候选词、实验、反馈学习”后，这个文件会迅速失控。

---

## 5. Finder 2.0 的产品目标

### 5.1 核心目标

让用户只输入一个大体方向，系统就能自动完成：

`方向输入 -> 候选词扩展 -> 市场验证 -> 推荐行动 -> 创建实验任务 -> 回收结果 -> 学习更新`

### 5.2 成功标准

系统应该能回答下面这些问题：

- 这个方向最近跑出了哪些新词？
- 哪些词值得立刻测试？
- 哪些词虽然热，但竞争太挤？
- 哪些词适合做商品型，哪些适合做服务型？
- 哪些词已经验证有效，可以转长期任务？

### 5.3 非目标

Finder 2.0 不负责替代全部执行逻辑：

- 不替代现有 `spider_v2.py` 的抓取执行
- 不替代任务调度器
- 不替代通知系统
- 不把整个产品改成纯 AI agent 系统

Finder 2.0 应建立在现有执行基座之上。

---

## 6. 核心闭环

Finder 2.0 的主循环应明确为：

`Direction -> Candidate -> Evidence -> Opportunity State -> Recommendation -> Experiment -> Feedback -> Learning`

### 6.1 Direction

用户给的大方向，是研究主题。

示例：

- 小红书运营
- AI 绘画副业
- 考公资料

### 6.2 Candidate

系统扩展出来的候选关键词，是待验证假设。

示例：

- 小红书起号教程
- 小红书代运营
- 小红书起号脚本
- 小红书自动发货资料

### 6.3 Evidence

系统从商品流中收集的证据：

- 样本量
- 时间分布
- 卖家分布
- 价格带
- 标题信号
- AI 推荐率 / 规则命中率

### 6.4 Opportunity State

对某个词在某个时点形成的完整状态判断：

- 热度
- 增速
- 商业化信号
- 竞争压力
- 风险
- 是否值得测试

### 6.5 Recommendation

系统输出下一步建议：

- 加入观察
- 创建测试任务
- 转正式监控
- 放弃

### 6.6 Experiment

推荐词进入实验或测试任务，验证真实市场表现。

### 6.7 Feedback

记录：

- 用户是否接受推荐
- 是否创建任务
- 任务结果如何
- 后续是否持续有效

### 6.8 Learning

基于反馈更新扩词、评分和推荐权重。

---

## 7. 领域模型重构

Finder 2.0 的中心对象不再是 `task` 或 `result file`，而是：

> `Keyword Opportunity State`（关键词机会状态）

建议引入以下顶层模型。

### 7.1 Direction

表示用户输入的方向。

关键字段：

- `id`
- `name`
- `seed_topic`
- `user_goal`
- `preferred_variants`（product/service/delivery 等）
- `risk_level`
- `status`
- `created_at`
- `updated_at`

### 7.2 Candidate Keyword

表示某个方向下系统生成的候选词。

关键字段：

- `id`
- `direction_id`
- `keyword`
- `source_type`（seed / rule / cooccurrence / llm / user）
- `source_detail`
- `lifecycle_status`（seed / candidate / validating / validated / rejected / archived）
- `variant_type`（product / service / delivery / generic）
- `confidence`
- `created_at`
- `updated_at`

### 7.3 Candidate Evidence

表示某次验证周期内的聚合证据。

关键字段：

- `id`
- `candidate_id`
- `window_start`
- `window_end`
- `sample_count`
- `recent_items_24h`
- `previous_items_24h`
- `unique_sellers`
- `median_price`
- `price_spread`
- `signal_terms_json`
- `recommended_items`
- `ai_recommended_items`
- `competition_score`
- `raw_metrics_json`

### 7.4 Opportunity State

表示候选词当前可执行判断。

关键字段：

- `candidate_id`
- `relevance_score`
- `heat_score`
- `momentum_score`
- `commercial_score`
- `competition_score`
- `execution_score`
- `confidence_score`
- `opportunity_score`
- `risk_status`
- `suggested_action`
- `score_version`
- `updated_at`

### 7.5 Experiment

表示某个推荐词被送去验证的执行实例。

关键字段：

- `id`
- `candidate_id`
- `task_id`
- `experiment_type`（draft / shadow / live）
- `status`（pending / running / completed / failed / cancelled）
- `started_at`
- `ended_at`
- `result_summary_json`

### 7.6 Recommendation Decision

表示系统推荐和用户/系统的后续处理。

关键字段：

- `id`
- `candidate_id`
- `recommendation_reason`
- `recommended_action`
- `status`（pending / accepted / dismissed / converted / expired）
- `accepted_by`
- `created_at`
- `updated_at`

### 7.7 Learning Feedback

表示学习闭环样本。

关键字段：

- `id`
- `candidate_id`
- `feedback_type`（user_accept / user_reject / task_good / task_bad / false_positive）
- `feedback_value`
- `feedback_note`
- `created_at`

---

## 8. 数据库设计建议

下面是基于现有 schema 的增量设计。

### 8.1 保留并复用的表

保留：

- `tasks`
- `result_items`
- `price_snapshots`
- `keyword_annotations`
- `radar_snapshot_runs`
- `radar_snapshot_keywords`

其中：

- `result_items` 继续作为商品证据事实表
- `price_snapshots` 继续作为价格时序样本表
- `tasks` 继续作为执行层配置表

### 8.2 建议新增的表

#### `radar_directions`

用于存储用户研究方向。

#### `radar_direction_seeds`

用于存储方向下的种子词，方便区分用户原始输入与系统扩展词。

#### `radar_keyword_candidates`

用于存储候选词及其生命周期状态。

#### `radar_candidate_evidence`

用于存储按时间窗口沉淀的证据快照，而不是每次查询时临时从 `result_items` 全量聚合。

#### `radar_opportunity_states`

用于保存机会状态与多维评分结果。

#### `radar_experiments`

用于把推荐词与真实任务/实验绑定。

#### `radar_learning_feedback`

用于记录学习反馈样本。

### 8.3 建议调整的现有表

#### `radar_keyword_recommendations`

建议补字段：

- `candidate_id`
- `direction_id`
- `variant_type`
- `recommended_action`
- `score_version`
- `expires_at`

原因：

当前表结构更像“一个推荐结果缓存表”，而不是完整推荐决策对象。

#### `radar_keyword_pool`

建议重新定位为：

- “用户确认长期跟踪的机会池”
- 不再承担所有候选词状态管理职责

---

## 9. 自动化扩词引擎设计

扩词建议采用三路并行策略。

### 9.1 规则扩词

使用固定模板，将方向和已知词扩成结构化候选词。

示例模板：

- `{topic} 教程`
- `{topic} 资料`
- `{topic} 模板`
- `{topic} 脚本`
- `{topic} 源码`
- `{topic} 代做`
- `{topic} 陪跑`
- `{topic} 自动发货`

优点：

- 可控
- 便宜
- 易解释

### 9.2 共现扩词

从 `result_items.title` 中抽取与方向高相关的共现词。

方法建议：

- 对标题做分词/短语抽取
- 计算方向词与候选短语的共现频率
- 过滤停用词与低价值平台词

优点：

- 真正贴近市场现状
- 能挖出人类没预设的长尾表达

### 9.3 LLM 语义扩词

用 LLM 在“规则扩词 + 共现扩词”基础上补齐语义变体。

用法应受约束：

- 输入现有方向、已有高分词、signal term
- 输出结构化候选词及分类说明
- 不允许直接无约束发散

优点：

- 能补足模板盲区
- 适合发现“服务表达”“人群表达”“变现场景词”

### 9.4 候选词生成策略

建议将候选词分层：

- `L1`：紧邻方向词的保守扩展
- `L2`：商品 / 服务 / 交付结构扩展
- `L3`：跨域语义扩展

优先推荐 L1 + L2，L3 作为探索层。

---

## 10. 评分体系设计

Finder 2.0 不应只保留一个总分，建议内部维护以下维度。

### 10.1 `relevance_score`

候选词与方向相关度。

来源：

- 词面相似度
- 来源路径可信度
- LLM/规则解释一致性

### 10.2 `heat_score`

近期样本量与活跃度。

### 10.3 `momentum_score`

最近 24h / 48h / 7d 的增长变化。

### 10.4 `commercial_score`

商业化信号强弱，例如：

- 教程
- 模板
- 自动发货
- 代搭建
- 永久
- 秒发

### 10.5 `competition_score`

竞争压力或拥挤度。

来源：

- 卖家数量
- 标题同质化程度
- 价格带压缩情况

### 10.6 `execution_score`

是否适合当前系统和用户能力去验证：

- 商品型更适合关键词模式
- 服务型更适合 AI 模式
- 自动交付型更适合低成本快速试验

### 10.7 `confidence_score`

证据充分性。

来源：

- 样本数量是否够
- 是否跨多个卖家
- 是否连续多窗口稳定出现

### 10.8 `opportunity_score`

最终综合分，仅作为排序与推荐门槛。

建议规则：

- 前端展示总分
- 后端保留各分项与 `score_version`
- 快照和推荐都保存评分版本号，便于回溯

---

## 11. 服务拆分建议

当前 `radar_service.py` 建议拆成以下模块。

### 11.1 `direction_service.py`

职责：

- 创建/更新方向
- 维护方向状态
- 查询方向详情

### 11.2 `keyword_expansion_service.py`

职责：

- 规则扩词
- 共现扩词
- LLM 扩词
- 候选词去重与归一化

### 11.3 `keyword_evidence_service.py`

职责：

- 从 `result_items` / `price_snapshots` 聚合候选词证据
- 生成时间窗口级证据快照

### 11.4 `opportunity_scoring_service.py`

职责：

- 计算多维评分
- 生成机会状态
- 管理 `score_version`

### 11.5 `recommendation_service.py`

职责：

- 从候选词和机会状态生成推荐
- 推荐状态变更
- 推荐过期 / 再生策略

### 11.6 `experiment_service.py`

职责：

- 把推荐词转成任务草稿或实验任务
- 追踪实验状态
- 回收执行结果

### 11.7 `learning_service.py`

职责：

- 汇总用户接受/拒绝与任务结果
- 输出策略调参依据

### 11.8 `radar_query_service.py`

职责：

- 对前端提供聚合查询接口
- 页面读模型聚合

也就是说，未来的 `radar_service.py` 应更多变成 facade，而不是所有逻辑堆放点。

---

## 12. API 设计建议

### 12.1 Direction API

#### `POST /api/finder/directions`
创建方向。

请求示例：

```json
{
  "name": "小红书起号",
  "seed_topic": "小红书运营",
  "user_goal": "找到适合自动交付或轻服务的虚拟商品词",
  "preferred_variants": ["product", "service", "delivery"],
  "risk_level": "medium"
}
```

#### `GET /api/finder/directions`
获取方向列表。

#### `GET /api/finder/directions/{direction_id}`
获取方向详情与摘要指标。

#### `PATCH /api/finder/directions/{direction_id}`
更新方向。

### 12.2 Candidate API

#### `POST /api/finder/directions/{direction_id}/expand`
触发一次扩词任务。

#### `GET /api/finder/directions/{direction_id}/candidates`
获取候选词列表。

支持筛选：

- lifecycle_status
- variant_type
- min_score
- suggested_action

#### `PATCH /api/finder/candidates/{candidate_id}`
更新候选词状态或人工标签。

### 12.3 Evidence / State API

#### `POST /api/finder/directions/{direction_id}/refresh`
刷新方向下所有候选词的证据与评分。

#### `GET /api/finder/candidates/{candidate_id}/evidence`
获取候选词证据详情。

#### `GET /api/finder/candidates/{candidate_id}/state`
获取机会状态详情。

### 12.4 Recommendation API

#### `GET /api/finder/directions/{direction_id}/recommendations`
获取方向下推荐结果。

#### `PATCH /api/finder/recommendations/{recommendation_id}`
接受 / 拒绝 / 转实验。

### 12.5 Experiment API

#### `POST /api/finder/candidates/{candidate_id}/experiments`
创建实验任务。

模式：

- `draft`
- `shadow`
- `live`

#### `GET /api/finder/experiments/{experiment_id}`
查看实验进度与结果。

### 12.6 Learning API

#### `POST /api/finder/candidates/{candidate_id}/feedback`
写入学习反馈。

#### `GET /api/finder/directions/{direction_id}/learning-summary`
查看这个方向的学习摘要。

---

## 13. 页面信息架构

当前 `RadarView` 建议逐步演进成以下结构。

### 13.1 Directions 页面

展示：

- 我的方向列表
- 每个方向的最近新发现数
- 今日推荐数
- 已验证词数
- 实验中词数

### 13.2 Direction Overview 页面

展示某个方向的总览：

- 方向摘要
- 今日新发现
- 高潜词
- 竞争拥挤词
- 最新实验结果

### 13.3 Candidates 页面

展示候选词流水线：

- seed
- candidate
- validating
- validated
- rejected

### 13.4 Recommendations 页面

展示可执行推荐卡：

- 推荐词
- 推荐原因
- 分项评分
- 证据摘要
- 建议动作
- 接受 / 拒绝 / 创建实验

### 13.5 Experiments 页面

展示推荐词验证进度：

- 已创建任务
- 当前状态
- 初步效果
- 是否转正式监控

### 13.6 Snapshot / Diff 页面

展示时间变化：

- 今日 vs 昨日
- 近 7 日变化
- 新出现词
- 下滑词
- signal term 变化

---

## 14. 自动化运行策略

### 14.1 定时流程

建议引入定时流水线：

1. 方向巡检
2. 候选词扩展
3. 证据刷新
4. 机会评分更新
5. 推荐重算
6. 实验结果回收
7. 学习反馈更新

### 14.2 节流策略

为了控制成本与噪音，建议：

- 新方向默认只跑 L1 + L2 扩词
- L3 扩词需要方向已有足够证据
- 对低证据候选词设置冷却时间
- 推荐词设置有效期和重新推荐间隔

### 14.3 噪音防护

建议加入：

- 停用词表
- 平台词白名单 / 黑名单
- 低价值信号词过滤
- 标题模板同质化惩罚
- 过度泛化词惩罚

---

## 15. 与现有任务系统的打通方式

Finder 2.0 不应绕开当前 `tasks` 能力，而应利用它做实验执行。

### 15.1 实验任务草稿映射

候选词 → 任务草稿的映射建议如下：

- `product` 候选词
  - 默认 `decision_mode=keyword` 或轻量 AI
- `service` 候选词
  - 默认 `decision_mode=ai`
- `delivery` 候选词
  - 默认 `decision_mode=keyword`

### 15.2 任务回写

实验任务完成后，应回写给 Finder：

- 新增样本数
- 推荐率
- AI 推荐率
- 持续活跃天数
- 是否被人工接受为正式机会

### 15.3 复用现有能力

直接复用：

- `TaskCreate`
- `TaskGenerateRequest`
- `/api/tasks/generate`
- `/api/tasks/draft`
- `TaskGenerationService`

也就是 Finder 只新增上游智能，不重写执行器。

---

## 16. 实施路线图

### Phase 1：方向模型落地

目标：让系统从“关键词任务入口”切到“方向入口”。

工作项：

- 新增 `radar_directions`
- 新增方向 CRUD API
- 新增 Directions 页面
- 允许方向绑定种子词和偏好配置

### Phase 2：候选词引擎落地

目标：系统自动扩词。

工作项：

- 新增 `radar_keyword_candidates`
- 实现规则扩词与共现扩词
- 抽离 `keyword_expansion_service`
- 增加候选词列表页

### Phase 3：证据与机会状态落地

目标：每个词有稳定、可解释的状态。

工作项：

- 新增 `radar_candidate_evidence`
- 新增 `radar_opportunity_states`
- 引入分项评分和 `score_version`
- 增加候选词详情页

### Phase 4：推荐与实验闭环落地

目标：系统从“推荐词”升级为“推荐动作”。

工作项：

- 重构 `radar_keyword_recommendations`
- 新增 `radar_experiments`
- 推荐词一键生成实验任务
- 实验结果回写 finder

### Phase 5：学习闭环落地

目标：系统根据历史推荐效果越来越聪明。

工作项：

- 新增 `radar_learning_feedback`
- 汇总接受/拒绝/实验结果
- 调整扩词和推荐权重
- 输出学习摘要面板

---

## 17. 当前代码改造顺序建议

为了降低风险，建议按下面顺序改造：

1. **先新增，不替换**
   - 新增方向模型和页面，不急着删除现有 radar
2. **先沉淀状态，再做智能**
   - 先有 `direction/candidate/evidence/state`，再做更复杂的推荐
3. **先打通任务闭环，再做学习**
   - 没有实验回写，学习模块会是空转
4. **先拆服务，再增逻辑**
   - 先把 `radar_service.py` 拆薄，否则后续难维护

---

## 18. 首批可交付里程碑

建议将 Finder 2.0 的第一个可见里程碑定义为：

> 用户创建一个方向后，系统能自动生成候选词、自动刷新证据、自动输出推荐，并允许一键创建实验任务。

具体验收标准：

- 能创建方向
- 能为方向自动扩出不少于 20 个候选词
- 每个候选词都有证据摘要与多维评分
- 系统能给出“立即测试 / 继续观察 / 放弃”的建议
- 推荐词可以一键生成任务草稿

这一步完成后，Finder 就已经从“雷达页”升级成“自动发现器”了。

---

## 19. 风险与注意事项

### 19.1 噪音风险

如果扩词完全放开，候选词会爆炸式增长。

应对：

- 分层扩词
- 候选词生命周期
- 推荐有效期
- 证据门槛

### 19.2 成本风险

LLM 扩词和 AI 验证如果过度触发，成本会很高。

应对：

- 先规则，后 LLM
- 小样本先筛再深分析
- 为方向设置刷新频率

### 19.3 可解释性风险

如果系统只能给“总分”，用户很难信任。

应对：

- 显示分项评分
- 显示推荐原因
- 显示来源信号和样本摘要

### 19.4 架构膨胀风险

如果继续把所有逻辑放在 `radar_service.py`，维护成本会迅速上升。

应对：

- 提前拆分服务层
- 区分写模型和读模型
- 给评分与推荐做版本化

---

## 20. 最终定位

Finder 2.0 的最终定位应明确为：

> 一个用户只需给出方向，系统就能自动发现、验证、推荐并学习关键词机会的选品 intelligence layer。

它的长期壁垒不在爬虫本身，而在：

- 方向建模
- 候选词生成
- 证据沉淀
- 推荐闭环
- 学习反馈

也就是说，Finder 不是“抓更多”，而是“越来越会找”。
