# 激光能量传输系统

站点维护与网页适配：[@poiiiiiiiiiiiii](https://github.com/poiiiiiiiiiiiii) · [打开 `index.html`](https://poiiiiiiiiiiiii.github.io/space-energy-tools/)

## 功能

站点首页集中进入光伏、TCT、轨道和 JA 等工具。输入各级转换效率、传播距离、发射口径和接收直径后，截获比例、光功率、电功率和光斑图会同步更新。光电效率子窗口的 PCE 可回填首页。

## 算法依据

把电源转换、电光转换、跟瞄透过率、光路透过率和光电效率按链路相乘。将出射直径 `D` 的一半作为近似束腰半径，按 [BPP 的半径与发散半角定义](https://www.edmundoptics.eu/knowledge-center/application-notes/lasers/beam-quality-and-strehl-ratio/)作远场估算：`r = BPP × L / (D/2)`。同轴均匀圆斑假设下，截获比例为 `min(1, 接收面积 / 光斑面积)`。接收光功率由出射光功率扣除跟瞄、传播和截获损失；再乘光电效率得到接收端电功率。波长用于标记工况，发散由输入的 BPP 决定。

## 适用范围

用于链路初估。面积比不考虑偏心、非均匀光强或湍流；要模拟光强分布及阵列外损失，可使用 [TCT 激光版](tctdemo_laser.md)。
