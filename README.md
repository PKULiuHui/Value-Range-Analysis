Value Range Analysis
====================

SSA => eSSA
-----------

`\src\ssa2essa`: 读取并解析.c和.ssa文件，处理条件判断，转换成.essa格式，存放在`eSSA`类中

`\src\t1.essa`: 手动将`t1.ssa`翻译成essa结果，供参考比较

eSSA => Constraint Graph
------------------------

`\src\build_graph.py`: 从eSSA解析结果中提取Constraints，同时处理函数调用的情况，将多个函数的Constraints合并成一个Contraints，然后建立Constraints Graph，求极大连通分量，并将它们按照拓扑序排序

`\src\computeSCC.py`: 使用Kosaraju算法求解极大强连通分量的例子，与主程序无关

