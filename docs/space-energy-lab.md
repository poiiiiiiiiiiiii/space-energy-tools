# 空间能量实验室

站点维护与网页适配：[@poiiiiiiiiiiiii](https://github.com/poiiiiiiiiiiiii) · [打开 `space-energy-lab.html`](https://poiiiiiiiiiiiii.github.io/space-energy-tools/space-energy-lab.html)

## 功能

读取内置 LEO 样本或手动选择 Excel 文件，查看能量与粒子数的表格、趋势和散点图。可调整插值方法、采样点数和能量区间，导出处理后的 CSV。

## 算法依据

清理无效值，按能量排序，合并重复能量节点，并将用于拟合的粒子数约束为非增。支持线性、对数纵轴、双对数或自动插值。每个自定义区间用中点插值作为代表值，并限制在两端估计值之间；它不是对粒子通量的区间积分。散点关系另计算 Pearson 相关系数。

## 适用范围

适合整理样本和比较分布趋势，不是辐射环境或轨道粒子输运求解器。插值约束会平滑局部上升，原始点和插值结果应区分。Excel 解析和字体均从站点加载，无需远程数据接口。
