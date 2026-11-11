# TandEx 网页计算器

站点维护与浏览器适配：[@poiiiiiiiiiiiii](https://github.com/poiiiiiiiiiiiii) · [打开 `tandex.html`](https://poiiiiiiiiiiiii.github.io/space-energy-tools/tandex.html)

## 功能

计算钙钛矿/硅叠层太阳能电池的 2T 和 4T 效率、短路电流、开路电压、填充因子及 J–V 曲线。支持选择预置顶层光学、EQE 和透过率数据，也能导入数据。另提供透明导电电极串联电阻及硅体寿命估算。

## 算法依据

模型使用 AM1.5G 光谱、EQE 与光学数据计算光生电流。按所选光学输入，使用传输矩阵法（TMM）计算层间透射与吸收，或采用给定 EQE 和透过率。考虑透明导电电极的片电阻、光学损失、金属栅线遮光及间距的权衡。用多二极管等效电路扫描工作电压并找最大功率点。

2T 以共同串联电流求整器件的 J–V 曲线；4T 分别求顶层和经过顶层滤光的硅底层最大功率并相加，单独受光的硅曲线仅用于对照。浏览器版把原 Flask/PySpice 计算路径改为 Pyodide Web Worker 内运行的 Python 数值求解，不需要运行后端。计算是模型预测，不能当作实测器件认证值。

## 上游署名

- 原始项目：[Oxford-eMat-Lab/TandEx](https://github.com/Oxford-eMat-Lab/TandEx)，牛津大学材料系研究团队。原模型文件 `tandex_func_02.py` 的[提交记录](https://github.com/Oxford-eMat-Lab/TandEx/commit/0241d50d6f03d779d0994943cd543c6acaffccff)对应 Ruy Sebastian Bonilla（[@seb-bonilla](https://github.com/seb-bonilla)）。本站使用了该模型及其数据的改编版，不是上游 notebook 的原样发布。
- 算法参考：Ruy Sebastian Bonilla, *The impact of transparent conducting electrodes on tandem solar cell efficiency*, Joule 9, 102211 (2025), [DOI: 10.1016/j.joule.2025.102211](https://doi.org/10.1016/j.joule.2025.102211)。
- 模型许可：上游 GitHub 仓库标注 GPL-3.0，站点保留[模型许可证](https://poiiiiiiiiiiiii.github.io/space-energy-tools/tandex-assets/LICENSE)。本站署名仅指网页适配与维护，不替代原始模型署名。
