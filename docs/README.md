# Space Energy Tools 网页说明

站点维护与网页适配：[@poiiiiiiiiiiiii](https://github.com/poiiiiiiiiiiiii)  
[公开首页](https://poiiiiiiiiiiiii.github.io/space-energy-tools/) · [GitHub 仓库](https://github.com/poiiiiiiiiiiiii/space-energy-tools)

本目录覆盖发布包里的 12 个 HTML。每页单独说明功能、算法依据和适用范围。开发测试文件及同名副本不重复列入。

| 网页 | 功能与算法速览 | 独立说明 |
| --- | --- | --- |
| `index.html` | 站点导航、分段效率乘积和光斑覆盖估算 | [激光能量传输系统](index.md) |
| `bec.html` | 单结与叠层光伏效率，基于光谱、EQE 与详细平衡近似 | [太阳能电池性能计算器](bec.md) |
| `tandex.html` | 钙钛矿/硅 2T、4T 光电耦合模型与 J–V 曲线 | [TandEx 网页计算器](tandex.md) |
| `tmp.html` | 晶硅与钙钛矿电池的轨道热平衡估算 | [轨道温度模拟](tmp.md) |
| `perovskite.html` | 脉冲氙灯回收的成本、LCOE 与简化 LCA | [钙钛矿模组回收](perovskite.md) |
| `medical.html` | 组织光衰减、接收功率与简化温升演示 | [医疗植入模拟](medical.md) |
| `space-energy-lab.html` | LEO 能量与粒子数据的插值、分区间统计和导出 | [空间能量实验室](space-energy-lab.md) |
| `tctdemo_am0.html` | 固定损坏样本、旁路与阵列重组的功率比较 | [TCT AM0 版](tctdemo_am0.md) |
| `tctdemo_laser.html` | 到靶光斑、湍流、阵列截获与 TCT 重组 | [TCT 激光版](tctdemo_laser.md) |
| `tctdemo_html.html` | 激光和太阳光切换的早期五组 TCT 演示 | [TCT 合并旧版](tctdemo_html.md) |
| `ja_solar_wing_albedo.html` | JA 太阳翼整面正背面入射反照光回放 | [JA 太阳翼整面反照光](ja_solar_wing_albedo.md) |
| `ja_attitude_albedo_compare.html` | 同一轨道下三种姿态的反照光对比 | [JA 三种姿态对比](ja_attitude_albedo_compare.md) |

## 运行与来源

站点由 GitHub Pages 提供静态文件。轨道温度、回收和医疗页共用仓库内的 Chart.js；空间能量实验室使用同站的字体和内置 LEO 数据。TandEx 无需后端，但初次运行需联网加载 Pyodide。JA 页展示已预计算并内嵌的轨道数据，不会在网页上重新求解完整轨道。

TandEx 原始模型归功于牛津大学 [Oxford-eMat-Lab/TandEx](https://github.com/Oxford-eMat-Lab/TandEx) 与 [Ruy Sebastian Bonilla（@seb-bonilla）](https://github.com/seb-bonilla)。论文、许可证与浏览器适配说明见 [TandEx 专页](tandex.md)。
