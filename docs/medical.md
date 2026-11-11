# 医疗植入模拟

站点维护与网页适配：[@poiiiiiiiiiiiii](https://github.com/poiiiiiiiiiiiii) · [打开 `medical.html`](https://poiiiiiiiiiiiii.github.io/space-energy-tools/medical.html)

## 功能

演示激光经组织衰减后由植入端光电接收器转换为电能的过程。可查看反射、透射、吸收和接收功率估算，以及温升、充电和吸收分项图表。

## 算法依据

模型将黑色素、血红蛋白、水的经验吸收项与散射项合并为等效衰减系数，用类似 Beer–Lambert 的指数衰减关系估算透射，再乘以接收面积比例和转换效率。温升和充电曲线由等效模型生成，不是组织测量结果。

## 适用范围

仅用于研究演示与趋势比较。页面的温升、风险和充电结果不构成激光安全认证、临床判断或人体照射建议。
