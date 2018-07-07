2017春季编译原理Project —— Value Range Analysis
=============================================

小组成员
-------
刘辉（1500012855），杨靖锋（）

基本思路
------
参考论文*A fast and low-overhead technique to secure programs against integer overflows*中的算法，首先解析输入的SSA文件，生成对应的eSSA代码，然后从eSSA代码中抽取constraints，将多个函数的constraints合并进主函数`foo`的constraints中，这样可以处理函数调用，之后构建constraints graph，求图中的强连通分量，按照拓扑序遍历每个强连通分量，对每个强连通分量执行Widening，Future resolution，Narrowing三步处理，最终求得各变量的取值范围。

组员分工
------
刘辉负责前半部分：解析SSA文件生成eSSA代码、constraints graph的构建、求强连通分量。杨靖锋负责后半部分：对每个强连通分量按照拓扑序执行Widening，Future resolution，Narrowing三步处理，最终求得各变量的取值范围。

测试方法
-------
```
cd src
python3 widen.py -data_dir=<benchmark-dir> -phase=<benchmark-id>
```
比如想要执行./benchmark/中的t1，则输入以下命令
```
python3 widen.py -data_dir=../benchmark/ -phase=t1
```
命令行参数都有默认值，默认情况下-data_dir的值为"../benchmark/"，-phase的值为"t1"。

需要注意的一点是如果想要执行t1，t1.c和t1.ssa两个文件都是需要的，并且输入输出的格式需要与t1.c中的一致，否则会解析失败。

测试结果
-------
对已给的10个phase进行测试，10组样例范围完全正确的有6组，具体结果如下：

测试样例|标准结果|输出结果
:-:|:-:|:-:
t1|[100, 100]|[100.0, 100.0]
t2|[200, 300]|[200.0, 300.0]
t3|[20, 50]|[20.0, 50.0]
t4|[0, +inf]|[0.0, inf]
t5|[210.0, 210.0]|[0.0, 210.0]
t6|[-9, 10]|[-9.0, 10.0]
t7|[16, 30]|[16.0, 30.0]
t8|[-3.22, 5.94]|[-3.22, 14.70]
t9|[9791, 9791]|[-10, inf]
t10|[-10, 40]|[-49.0, inf]

需要指出的是，我们的程序应该是完全实现了以上论文中的算法，但该算法的本身的缺陷导致了它并不能准确地分析每一个变量的范围，举个例子，比如t10.ssa中有如下代码：

```
<bb 5>:
# j_2 = PHI <j_4(4), j_7(5)>
j_7 = j_2 + 1;
_8 = i_1 + j_7;
if (_8 < b_9(D))
  goto <bb 5>;
else
  goto <bb 6>;

<bb 6>:
_10 = j_7 - i_1;
```
算法希望通过条件判断来给出变量的范围信息，在这个例子中，我们希望通过`if (_8 < b_9(D))`给出`j_7`的范围，然而条件判断针对的是`_8`，尽管`_8`随着`j_7`变化，但在这个算法中`_8`的范围不能给`j_7`的范围有效的信息，所以最后的分析结果不准。但可以保证的是，最后的结果一定是准确结果的一个超集。


`src`源码简介
------------

`ssa2essa.py`:

利用正则表达式读取并解析.c文件和.ssa文件，同时处理条件判断，生成essa格式代码，解析结果存储在相关的`eSSA`类中。

`build_graph.py`:

针对得到的`eSSA`类，为每个函数提取constraints，如果程序中涉及了函数调用，代码会合并多个函数的constraints，得到一组最终的，变量名互不冲突的constraints。  
之后利用这组constraints构建constraints grpah，每条语句和每个变量分别为图中节点，变量和语句间的def-use关系形成了图中的有向边。  
图构建好之后，利用Kosaraju算法求图中的强连通分量，并拓扑排序。

`widen.py`:
对排好序的极大联通子图依次进行widening, future resolution, narrowing三步
widening：对于每个联通子图，除去2边（future依赖）后再通过Kosaraju算法求得极大联通子图，对于其中每一个widening 
future resolution：每个联通子图future resolution，如果依赖变量为空集
narrowing: 对于每个联通子图，除去2边（future依赖）后再通过Kosaraju算法求得极大联通子图，对于其中每一个narrowing
widening和narrowing遍历图直到没有更新，每个变量节点和constraint节点都有一个范围，遍历到该节点时根据规则更新或不更新范围
输出最后输出节点的范围
widening, future resolution, narrowing的规则在论文中给出
