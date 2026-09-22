# 论文实验绘图与 GPT Image 图示提示词

## 目录

- 两类图的执行边界
- 实验分析图：选图与统计表达
- 统一视觉规范
- 可复现交付与验收
- 框架图与流程图提示词协议
- 提示词示例与修订
- 阶段接入与参考依据

## 两类图的执行边界

“优秀论文标准”指事实准确、信息充分、缩印可读、风格一致、可追溯；不保证获奖，不以模仿某篇论文外观代替科学论证。

| 类型 | 制作方式 | 默认交付 |
| --- | --- | --- |
| 实验分析图：曲线、误差、比较、分布、热图等 | 从真实数据或明确标注的仿真结果，用 Python/Matplotlib、R 或既定科研工具生成 | 绘图代码、源数据定位、PNG、适合的 SVG、图注和检查记录 |
| 论文研究框架图、算法流程图、机制示意图 | 根据实际方法整理准确的结构，再编写 GPT Image 提示词 | 中文设计说明、节点/边清单、完整提示词、文字清单、图注建议、验收项 |

默认只给概念图提示词，不调用图像生成工具。用户以后明确要求生成或编辑图片时再按环境能力执行。严禁让图像模型生成实验曲线、坐标读数、置信带、热图数值、性能排名或显著性证据。混合图中的数据子图也必须由代码生成，示意部分不得遮盖或改变数据。

单独的绘图任务可以在对应上游结果有效时执行，不要求整篇论文先完成。未完成全部实验时可以产出研究用真实结果图；不得借绘图任务提前写论文正文或摘要。

## 实验分析图：选图与统计表达

先在 reports/figure_inventory.md 写清“对应要求—要检验的问题—图型—输入结果—预期读法”，再写代码。未观察到的数据趋势只能作为待检验假说。图的目的不是让主方案看起来最好。

| 论证目的 | 优先图型 | 必须核对 |
| --- | --- | --- |
| 方法性能比较 | 点区间图；有明确理由时用柱状图 | 相同划分、指标方向、预算；区间含义与样本单位 |
| 时间/迭代变化 | 折线、必要的区间带 | 时间间隔、缺口、收敛条件；同预算或明确说明预算差异 |
| 分布与稳定性 | 箱线图、散点；样本足够时用小提琴图 | 样本量、箱须定义、是否独立；不隐藏失败运行 |
| 预测误差 | 预测-实际散点及参考线、残差图 | 同单位；参考线 y=x；分组及偏差模式 |
| 敏感性/消融 | 参数响应曲线、变化量图、消融点区间图 | 参数范围、控制变量；不把单因素敏感性称为全局结论 |
| 矩阵与空间关系 | 热图、符合数据含义的空间图 | 色条、单位、缺失值；同类子图保持可比色标 |
| 多目标权衡 | 散点与经验证的非支配解集 | 目标方向、可行性；不把有限样本包络称为理论前沿 |
| 优化/仿真结果 | 调度图、轨迹、约束余量、守恒误差 | 与真实变量及边界一致；仿真设置可追溯 |

不得为了图多而机械添加雷达图、饼图、3D 柱状图或每问同一套图。维度、几何或空间关系确实需要三维时，给出可读视角及必要的二维补充。

统计与轴线规则：

1. 区分标准差 SD、标准误 SEM、置信区间 CI、预测区间。图注明确计算方法、置信水平（如适用）、样本量 n 及 n 的单位；重复种子、交叉验证折与独立样本不能混称。
2. 只有一个汇总值时不凭空加误差棒。若必要结论缺少重复试验，登记补实验任务；若当前范围仅绘图，保留单点并说明局限。
3. 不虚构 p 值、显著性星号或相关性；实际采用检验时记录假设、检验方法及多重比较处理（如适用）。相关关系不能画成已证实因果。
4. 交代筛选、聚合、平滑、归一化和异常值规则。显示原始数据或必要参照，禁止只选有利种子、区间与案例。
5. 用柱长表达量值的柱状图原则上从零开始；差值比较可另用点图。折线和散点不机械强制零起点，但范围需诚实、清晰且同类图可比。断轴必须显著标注并说明理由。
6. 对数轴说明底数，明确处理零和负数，不能静默丢弃。单位、变换、指标优劣方向写清楚；共享尺度只用于可比的同量纲变量。
7. 只有真实对应关系才能连线。缺失值不画成零，无理由不跨缺口插值。训练/验证/测试表现分开标注。

## 统一视觉规范

以下为本 skill 的项目默认值，不是 Nature、PLOS 或比赛统一硬性要求。以实际 Markdown 展示宽度、信息密度和用户明确要求调整；调整后整篇一致。正式投稿另核对目标渠道要求。

| 项目 | 默认与检查 |
| --- | --- |
| 背景与装饰 | 白底，深灰/黑色文字；去阴影、浮雕和无信息渐变。网格默认关闭，确有读数需要时仅保留淡灰主网格 |
| 尺寸 | 用最终阅读尺寸设计；单幅可从 85–90 mm 宽、跨栏式组合从 170–180 mm 宽起步；Markdown 无固定栏宽，必须再按实际显示检查 |
| 字体 | 一致的无衬线字体；英文可用 Arial/DejaVu Sans，中文选择环境实际安装的思源黑体/Noto Sans CJK 等；检查中文、负号和上下标，不静默接受方框乱码 |
| 字号 | 最终尺寸下刻度/图例约 8–10 pt、轴名约 9–11 pt 作为起点；密集时简化内容或拆图，不无限缩字 |
| 线与点 | 曲线约 1–1.5 pt、标记约 3–5 pt、轴线约 0.6–0.8 pt；缩印后仍区分实线/虚线与点形 |
| 配色 | 候选色：蓝 #0072B2、橙 #E69F00、绿 #009E73、紫 #CC79A7、灰 #7F7F7F；按需要选用，不能仅靠颜色区分 |
| 语义一致 | 同一模型在所有图中保持相同颜色、线型与名称；主方案适度突出，基线仍清楚可辨；突出不等于宣称最优 |
| 连续色标 | 非负或单向量使用感知较均匀的顺序色标，如 viridis/cividis；相对零偏差等有中心含义时用发散色标；避免彩虹色制造虚假边界 |
| 图例与标注 | 不遮盖数据；顺序与阅读/方法顺序一致；必要时在线尾直接标注。避免图内大标题，解释放图注 |
| 组合图 | (a)、(b) 等面板标号统一；边距对齐；同类轴与色标可比；共用图例只在含义一致时使用 |
| 输出 | 适合矢量的图保留 SVG，另输出 Markdown 通用的白底 PNG；PNG 通常 300 dpi，密集线图可 600 dpi，同时检查实际像素和最终尺寸 |

色板只是起点。做灰度可辨识检查，有能力时做色觉缺陷模拟；没有执行不得声称已验证。用点形、线型、直接标注作冗余编码。浅色线与背景对比不足时调整，不能仅因为色号“色盲友好”就通过。

DPI 标签本身不能增加像素；例如 90 mm 宽图在 300 dpi 下约需 1063 像素宽。禁止把小图放大或把 PNG 包进 SVG 就声称得到高清矢量图。含密集散点/图像的图可合理栅格化局部，保留能保留的矢量文字与线条。不要由此生成 PDF 论文。

绘图实现时统一建立项目级样式文件，如 code/plot_style.py 或 configs/figure_style.json。这是按需创建的项目产物，不是 skill 已内置的渲染器。保留输出时实际使用的尺寸、字体、色标、导出参数和依赖版本；避免针对每张图随意改主题。

## 可复现交付与验收

每幅图的登记信息至少包含：figure_id、关联题目要求、科学问题、源实验 ID、输入文件与指标位置、样本/划分/单位、聚合与筛选规则、绘图脚本、运行命令、样式配置、输出文件、图注、检查状态和证据。按现有 state 规则关联任务及真实运行记录，不擅自新增脚本不支持的 CLI 参数或自动判定字段。

执行次序：核验源数据 → 制图清单 → 统一样式 → 代码生成 → 数值对照 → 打开实际图检查 → 修改 → 登记产物与状态。依据真实结果回答“图显示什么、支持什么、不能说明什么”；S5 写入结果报告，S6 才整合论文解释。

reports/figure_review.md 逐图记录：

- 数值、排序、坐标、单位、点数/样本量和区间与源结果一致；重算必要的聚合，不能只看外观。
- 图注说明对象、条件、样本、统计定义、面板及必要局限；单独看图与图注可理解。
- 以预计论文显示宽度检查文字、图例、曲线、边缘裁切、重叠、灰度及色标。
- 论文图片相对 paper/paper.md，如 ../figures/q1_error.png；使用文字说明或替代文字帮助理解。路径正确不等于图像已视觉验收。
- 输入或模型变动后，把受影响图与结论标记 STALE。更改统计口径须重验结果；纯样式更改只重画并检查受影响产物。

无视觉查看能力则明确“视觉检查未执行”，保留必要待办。将实际图像、绘图代码、所需输入、提示词及检查记录按交付范围加入 state.delivery_files；现有审计只检查其支持的文件、哈希、路径和记录，不自动证明配色、图中文字或拓扑正确。

## 框架图与流程图提示词协议

先确定图要说明的关系，而不是先挑视觉模板。论文方法框架不等于 S0—S8 的比赛工作流；除非用户要画工作流，不把 skill 阶段名画入论文。

1. 读取实际题目、模型、代码与已采用方法。整理节点 ID、精确标签、输入/输出、分组；整理有向边的起点、终点、含义，以及分支条件、循环与停止条件。
2. 区分数据流、控制流和用于评价的关系；只有实际存在的反馈才能画成反馈箭头。未实现/弃用模块不放进“最终方法图”。
3. 选择横向或纵向阅读顺序、画幅比例、主次层级和分组；概览过密则拆成总体框架与局部流程。矩形表示处理，菱形表示判断，起止形状一致，不为了美观改变逻辑。
4. 默认交付 prompts/framework_gptimage.md 或 prompts/workflow_gptimage.md，包含设计说明、精确节点/边表、可直接复制的完整提示词、标签清单、图注建议、生成后核验项及修订提示词。目录与文件按需创建，初始化脚本不会自动生成它们。
5. 提示词可用英文叙述布局，标签默认中文；用户要求英文图时才改为英文标签。要求逐字保留标签，节点 ID 仅用于指定结构，非必要不画进图片。缺乏结构依据时先完成事实清单，不能把通用占位词当最终项目内容。
6. 采用白底、扁平、矢量风格外观、克制的 2–4 组语义色、深色文字、统一细线与箭头、整齐间距及留白。禁止无关图标、3D、霓虹、阴影、纹理与装饰性渐变。线不穿字，箭头端点和方向明确。
7. 写清“不新增节点、不增删连线、不添加数值/性能曲线/参考文献/徽标、不声称未验证效果”；仅画科学上有依据的结构。不要把优秀论文风格解释成复制某篇论文的独特布局或图像。
8. 提示词中的画幅与字号意图是设计要求，不声称任意接口支持指定尺寸、精确字体或真正 SVG。GPT Image 图片是栅格产物；“vector-like”只指外观。
9. 长中文、复杂公式或密集标签难以准确生成时，提供“无文字底图提示词 + 精确标签和位置表”，供后续人工/代码叠字；保留清楚的节点 ID 映射。后续叠字不改变图中科学内容。
10. 图片生成后逐字核对标签，逐边核对方向、分支及停止条件，缩印检查。未通过的图片不能作为最终论文图；可生成修订提示词或按相同结构另行制作可编辑图。审查通过前只标为候选。

仅交付提示词时，不在论文中插入不存在的图片路径，也不标记“图片已生成/已验收”。若该图为必要任务，生成与验收保持 TODO；若可选，明确当前交付不含成图，不以提示词文件充当图片文件。

## 提示词示例与修订

以下是明确的教学示例，不是任何真实赛题的方法。实际执行时必须依据当前项目重写并填实全部节点和连线。

### 示例 A：数据处理与优化框架

假设方法确实包含数据检查、参数估计、优化和可行性检验。节点：A 原始数据；B 数据检查；C 参数估计；D 优化求解；E 可行性检验；F 方案输出。边：A→B、B→C、C→D、D→E、E→F；E→F 指检验通过的方案，不能暗示失败方案也输出。

~~~text
Create a clean academic method framework diagram with a white background,
flat vector-like appearance and a landscape 3:2 composition.
Use two aligned rows of three modules with a clear reading order.
Row 1 from left to right: A, B, C. Row 2 from right to left: D, E, F.
Render only these exact Chinese labels inside the modules:
A: 原始数据; B: 数据检查; C: 参数估计;
D: 优化求解; E: 可行性检验; F: 方案输出.
IDs A–F are layout references; do not print them.
Draw exactly these directed arrows: A->B, B->C, C->D, D->E, E->F.
Label only E->F with the exact text “通过”.
This is a high-level framework, not a complete failure-handling flowchart.
Do not add feedback arrows or imply that unsuccessful solutions are accepted.
Use pale blue fills for A–B, pale green for C–D, and pale orange for E–F,
with dark readable text, consistent thin borders and modest arrowheads.
Use generous whitespace, aligned boxes and consistent sans-serif typography.
Keep labels legible when displayed at approximately 180 mm wide.
No extra nodes, arrows, numbers, equations, data charts, logos or decorative icons.
No 3D, glow, shadows, textures or gradients. Do not add a title or caption inside the image.
Preserve all labels character for character. Visual polish must not alter the topology.
~~~

实际交付时另附中文图注建议、上述标签表与五条边的核验清单；图注仅描述结构，不附虚构效果。

### 示例 B：有停止条件的迭代流程

教学假设：可行初值与可行性保持更新已经成立。节点 A 可行初值；B 计算目标值；C 满足收敛条件？；D 达到迭代上限？；E 执行可行性保持更新；F 输出收敛解；G 输出当前可行解（未收敛）。边 A→B→C，C是→F，C否→D，D是→G，D否→E，E→B。实际算法不满足前提时不得照搬。

~~~text
Create a precise academic algorithm flowchart on a white portrait 3:4 canvas,
using flat vector-like shapes, aligned spacing and a restrained blue-gray palette.
Render these exact labels, without printing their reference IDs:
A “可行初值”, B “计算目标值”, C “满足收敛条件？”,
D “达到迭代上限？”, E “执行可行性保持更新”,
F “输出收敛解”, G “输出当前可行解（未收敛）”.
Use diamonds for C and D, rectangles for B and E, and rounded terminals for A, F and G.
Draw exactly: A->B; B->C; C->F labeled “是”; C->D labeled “否”;
D->G labeled “是”; D->E labeled “否”; E->B with an external return arrow.
Place A, B, C and D in a central top-to-bottom column.
Place F to the right of C, G to the right of D, and E below D.
Route E->B around the left margin. Keep arrows away from all text.
Preserve both distinct terminal outcomes, including the explicit non-convergence label.
Use dark legible Chinese text, equal border weights and consistent arrowheads.
No invented operations, stopping thresholds, numerical results or extra connections.
No performance curves, icons, 3D, shadows, gradients or embedded title.
~~~

### 修订提示词规则

同时提供原图和明确纠错清单，逐条写出错误位置、现有内容、正确内容；要求保留其余正确结构与风格。文字持续错误时改为无文字底图加标签表，不反复接受近似字。示例：

~~~text
Revise the supplied diagram only as follows:
1. Replace the label in node G with exactly “输出当前可行解（未收敛）”.
2. Ensure the arrow from D to G is labeled “是” and points into G.
Keep all other verified nodes, edges, colors and spacing unchanged.
Do not add scientific content or numerical results. Maintain a white background.
~~~

## 阶段接入与参考依据

- S3：制定图表计划与比较协议。明确要求时可交付标为“拟议方法”的结构提示词，不称为最终论文图，不开始论文。
- S4/S5：随真实结果生成分析图并检查；G5 依据包括图与数值一致、统计解释和主要结论支持情况。
- S6：写作前提满足后统一论文图表，并按最终实际方法交付框架/流程图提示词；图像生成另按用户请求处理。G6 检查图注、文字、方法一致性和阅读效果。
- S7：核对全篇命名、图号、单位、配色、相对路径、图中文字及连线；G7 审查真实记录。没有新增 G9，也不声称现有脚本自动审美评分。
- 每轮将制图、数值核对、提示词准备、成图生成（如请求）、视觉验收拆成独立 todo，写出依赖、产出与完成证据。完成提示词不等于完成最终图片。

参考的是清晰性、可访问性、数据表达与输出质量原则。以下出版方的具体规格各有适用场景，本 skill 的默认尺寸与字号是独立的项目选择。查阅日期：2026-09-22。

- [Nature：Preparing figures—our specifications](https://research-figure-guide.nature.com/figures/preparing-figures-our-specifications/)：轴与单位、清晰文字、可辨识配色及去除无关装饰。
- [Nature：Building and exporting figure panels](https://research-figure-guide.nature.com/figures/building-and-exporting-figure-panels/)：组合图、可读性和输出。
- [PLOS One：Figures](https://journals.plos.org/plosone/s/figures)：按最终尺寸考虑图像分辨率与图文件质量。不是本项目的投稿格式要求。
