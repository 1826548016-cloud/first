from django.db import migrations


def seed_items(apps, schema_editor):
    Exam408Item = apps.get_model("tasks", "Exam408Item")
    rows = []
    order = 0

    def pack(pillar, modules):
        nonlocal order
        for module, labels in modules:
            for label in labels:
                order += 1
                rows.append(
                    Exam408Item(
                        pillar=pillar,
                        module=module,
                        label=label,
                        sort_order=order,
                        owner_id=None,
                    )
                )

    pack(
        "ds",
        [
            (
                "线性表",
                [
                    "顺序表定义",
                    "顺序表插入删除",
                    "链表（单链表、双链表）",
                    "循环链表",
                ],
            ),
            (
                "栈与队列",
                [
                    "栈的基本操作",
                    "栈的应用（括号匹配）",
                    "队列（顺序队列、链队列）",
                    "循环队列",
                ],
            ),
            (
                "树",
                [
                    "二叉树基本性质",
                    "二叉树遍历（前中后序）",
                    "线索二叉树",
                    "二叉排序树（BST）",
                    "平衡二叉树（AVL）",
                    "哈夫曼树",
                ],
            ),
            (
                "图",
                [
                    "图的存储（邻接矩阵/表）",
                    "深度优先搜索（DFS）",
                    "广度优先搜索（BFS）",
                    "最短路径（Dijkstra）",
                    "最小生成树（Prim/Kruskal）",
                ],
            ),
            (
                "查找",
                ["顺序查找", "折半查找（二分）", "哈希表"],
            ),
            (
                "排序",
                [
                    "插入排序",
                    "冒泡排序",
                    "选择排序",
                    "快速排序",
                    "堆排序",
                    "归并排序",
                ],
            ),
        ],
    )

    pack(
        "os",
        [
            (
                "进程与线程",
                ["进程概念", "线程与进程区别", "进程状态转换"],
            ),
            (
                "CPU调度",
                ["FCFS", "SJF", "时间片轮转", "优先级调度"],
            ),
            (
                "内存管理",
                ["分页", "分段", "虚拟内存", "页面置换算法（LRU/FIFO）"],
            ),
            (
                "文件系统",
                ["文件结构", "目录管理"],
            ),
            (
                "死锁",
                ["死锁条件", "死锁避免（银行家算法）"],
            ),
        ],
    )

    pack(
        "co",
        [
            ("数据表示", ["原码/反码/补码", "浮点数表示"]),
            ("运算方法", ["加减法运算", "乘除法运算"]),
            ("存储系统", ["Cache", "主存", "局部性原理"]),
            ("CPU", ["指令周期", "流水线", "控制器"]),
            ("总线", ["数据总线", "地址总线", "控制总线"]),
        ],
    )

    pack(
        "cn",
        [
            ("网络体系结构", ["OSI模型", "TCP/IP模型"]),
            ("数据链路层", ["差错检测", "MAC协议"]),
            ("网络层", ["IP协议", "路由算法"]),
            ("传输层", ["TCP", "UDP", "拥塞控制"]),
            ("应用层", ["HTTP", "DNS"]),
        ],
    )

    Exam408Item.objects.bulk_create(rows)


def unseed_items(apps, schema_editor):
    Exam408Item = apps.get_model("tasks", "Exam408Item")
    Exam408Item.objects.filter(owner_id__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("tasks", "0005_exam408_item_and_progress"),
    ]

    operations = [
        migrations.RunPython(seed_items, unseed_items),
    ]
