# 实验、数值与验收记录

## 记录含义与职责

state.json 是任务与证据索引，结果文件是指标原始来源，plan解释决策，todo是状态的可读视图。脚本只核对已记录的信息；不得以生成一个PASS声明代替实际审查。

所有路径相对于项目根。将要用到的外部本地输入按用户授权放入项目或保存可追溯副本，原始资料保持不变。证据文件应按版本保存，不能覆盖后让旧实验继续引用。保存包版本、实际硬件、随机种子、求解器参数和具体运行命令。

## state.json 的主要数组

- tasks：阶段任务，格式见planning.md。
- requirements：全部具体要求，含id、question、description、source、status、evidence、paper_anchor。
- 仅分析规划时，用requirements[].analysis的status和evidence单独记录分析完成情况；不提前把题目解答status改为DONE。
- checks：审查结论与被检查文件快照，初始化自动创建当前范围的必要G检查。
- experiments：实际运行或有明确推导记录的结果。
- claims：论文每次数值引用的绑定。
- delivery_files：额外交付文件的项目相对路径。

requirements_complete只有逐项对照完整原题和补充要求后才设true；requirements_source记录完整题面出处。增加、修改或删除要求后重新检查G1。

## 真实实验登记

先实际执行，再记录；record-run不会替你运行命令。

~~~bash
python3 <技能目录>/scripts/project.py record-run --root <项目目录> --id E001 --status SUCCEEDED --kind execution --command "python code/q1.py" --input code/q1.py --input data/clean.csv --output results/e001.json --log results/e001.log
~~~

--input和--output可重复。完整输入包括使用的代码、配置、数据和上游输出；不能仅记录主脚本而漏掉实际影响结果的依赖文件。日志记录退出状态、命令、关键设置及重要输出。

推导型结果使用kind=derivation，--command写实际推导/验算方法，日志为推导或核验记录，输入为题设与推导依据。不得以derivation绕过本来需要执行的实验。

失败运行用FAILED，保留日志；它可以作为失败分析依据，但不能支撑成功数值结论。新尝试使用新ID。历史实验若不再支撑当前成果，设置retired=true并写retirement_reason；仍用于基线对比的实验保持有效并保存输入版本。

## 数值源格式

对将进入论文的关键指标，求解程序在JSON中保存数值、单位和所属任务/场景。示意结构：

~~~json
{
  "metrics": {
    "accuracy": {
      "value": 0.92,
      "unit": "1",
      "context": {
        "requirement_id": "Q2.a",
        "split": "test",
        "method": "baseline"
      }
    }
  }
}
~~~

上例仅说明格式，不是当前赛题结果。无量纲单位使用1，其他单位如元、小时、%。百分比或万元等转换先在程序输出中明确完成，不能由写作阶段静默乘除。

## 论文数值绑定

在state.claims为每一次重要数字引用登记：

~~~json
{
  "id": "C001",
  "requirement_id": "Q2.a",
  "experiment_id": "E001",
  "result_file": "results/e001.json",
  "pointer": "/metrics/accuracy",
  "decimals": 4,
  "context": {"split": "test", "method": "baseline"},
  "paper": "paper/paper.md"
}
~~~

JSON pointer支持字典和数组及标准~0/~1转义。源指标context必须包含相同requirement_id，并满足引用声明的场景。context需有实际语义，不能为了通过检查随意填值。

论文写法：

~~~markdown
测试集准确率为 <!-- mm:C001 -->0.9200<!-- /mm:C001 -->。
~~~

带单位的显示例如：

~~~markdown
成本为 <!-- mm:C002 -->1234.50 元<!-- /mm:C002 -->。
~~~

审计读取全部引用，检查源实验成功且仍有效、结果文件属于该实验、文件SHA256未变化、任务与场景一致、数值按声明精度四舍五入、单位一致、引用恰好出现一次。摘要和正文重复引用同一指标时使用不同引用ID。

显示采用十进制ROUND_HALF_UP，保留decimals位。无需人工重算；审计报告expected_claim_displays会给出应显示文本。零、负数和小于1的数值都检查。布尔值、NaN、Infinity、数字字符串不能冒充数值指标。

此机制不能自动发现所有未绑定数字，也不能判断文献或场景是否真实。G6/G7必须检查全部主要结论、未绑定常数、推导和语义。

## 实际审查与状态

完成检查后写报告：检查对象、依据、方法、实际发现、结论、未执行项、局限。然后登记：

~~~bash
python3 <技能目录>/scripts/project.py record-check --root <项目目录> --id G5 --status PASS --note "在相同划分和约束下完成基线比较，误差及失败情景已说明" --evidence reports/validation.md --input code/q1.py --input results/e001.json
~~~

PASS必须有审查报告与被查输入的快照。数据、代码或论文变化后相应检查失效，重新实际核验并登记。

G0—G8由当前scope决定必要性，不可删除或设成可选来绕过验收。其他自定义可选检查可以NA，但必须说明真实不适用理由。基础理论题的G2/G4等仍可检查题设、边界、推导和小实例，不要求制造训练集或大规模实验。

任务DONE要有实际evidence文件、预期outputs文件及已完成依赖。要求DONE要关联完成任务与证据；完整论文还要有答题锚点。

审查报告可使用reports/review.md；不要把会被反复覆盖的reports/audit.json当作record-check输入或证据，以免形成自引用校验。

## 审计命令与边界

~~~bash
python3 <技能目录>/scripts/project.py sync --root <项目目录>
python3 <技能目录>/scripts/audit.py --root <项目目录> --require-complete --output reports/audit.json
~~~

退出码：0为实际结构检查通过且符合所选完整性要求；1为错误；2为要求完整交付但仍有未完成任务/检查。普通进行中审计允许INCOMPLETE且退出0，读取scope_completion判断真实完成状态。

structural_status只表示程序检查的结构与记录一致性。scope_completion只有当前范围全部必要任务、要求与检查满足才为READY。scientific_status始终提醒需要已有科学审查证据，不能当作数学证明。official_submission_status始终NOT_ASSESSED。

analysis范围依据独立的分析状态与证据判定scope_completion，不要求提前完成题目中的实际计算。answer_completion报告题目解答是否全部被记录为完成；RECORDED_COMPLETE仅是台账状态，还须结合结构检查和科学审查。分析范围READY时markdown_delivery_ready仍为false。

完成检查、G8及交付说明后：

~~~bash
python3 <技能目录>/scripts/audit.py --root <项目目录> --freeze
~~~

冻结保存核心记录、论文、当前实验输入输出、证据和交付材料的摘要。之后只读核验不加--output；改变被记录文件会失败。创建新修订时保留旧快照，用新项目版本并重新核验受影响内容。

最终交付只报告已完成的检查。Markdown就绪不等同当届官方格式或实际提交成功。
