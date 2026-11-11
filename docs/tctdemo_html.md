# TCT 光斑优化合并旧版

站点维护与网页适配：[@poiiiiiiiiiiiii](https://github.com/poiiiiiiiiiiiii) · [打开 `tctdemo_html.html`](https://poiiiiiiiiiiiii.github.io/space-energy-tools/tctdemo_html.html)

## 功能

保留同页切换激光和太阳光的早期演示。可调整串并联阵列、湍流或遮挡，比较原始分布与五组重组结果，并查看时序功率和组指标。

## 算法依据

用二维高斯生成激光分布，用基础照度与遮挡区间生成太阳光分布；时序加入随机扰动，启用激光湍流时再施加近似扰动。电学模型由单片近似 I–V 构建，串联组按电流上限求最大功率，TCT2026 通过排序初分组与组间移动提高总功率。

## 适用范围

本页用于兼容旧演示。不要把旧版光斑归一化、太阳光波动或固定五组逻辑与新版混用。稳态损坏与旁路以 [AM0 版](tctdemo_am0.md) 为准；矩形电池和阵列外光损失以 [激光版](tctdemo_laser.md) 为准。
