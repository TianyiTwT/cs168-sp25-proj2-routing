"""
Berkeley CS168 距离矢量路由器项目的框架代码

作者：
  zhangwen0411, MurphyMc, lab352
"""

# 注意：此文件以 POX 风格编写。


import sim.api as api


# 主机发现数据包被视为实现细节——
# 我们通过它们知道何时调用 add_static_route()。
# 因此，我们在模拟器中将它们设置为不可见。
from sim.basics import HostDiscoveryPacket

HostDiscoveryPacket.outer_color = [0, 0, 0, 0]
HostDiscoveryPacket.inner_color = [0, 0, 0, 0]


# TODO：把这个改成 namedtuple？
class RoutePacket(api.Packet):
    """
    一个 DV 路由通告

    注意这些数据包同时有 .dst 和 .destination 属性。
    前者是数据包的目的地址，与所有数据包都有目的地址一样。
    后者是此路由通告所针对的目的地。
    """

    def __init__(self, destination, latency):
        super(RoutePacket, self).__init__()
        self.latency = latency
        self.destination = destination
        self.outer_color = [1, 0, 1, 1]
        self.inner_color = [1, 0, 1, 1]

    def __repr__(self):
        return "<RoutePacket to %s at cost %s>" % (self.destination, self.latency)


class Ports:
    def __init__(self):
        self.link_to_lat = {}

    def add_port(self, port, latency):
        self.link_to_lat[port] = latency

    def remove_port(self, port):
        del self.link_to_lat[port]

    def get_all_ports(self):
        return self.link_to_lat.keys()

    def get_latency(self, port):
        return self.link_to_lat[port]

    def get_underlying_dict(self):
        return self.link_to_lat


class DVRouterBase(api.Entity):
    """
    实现距离矢量路由器的基类
    """

    TIMER_INTERVAL = 5  # Default timer interval.
    ROUTE_TTL = 15

    def start_timer(self, interval=None):
        """
        启动定时器，定时调用 handle_timer()

        这应该在构造函数中调用。

        !!! 不要重写此方法 !!!
        """
        if interval is None:
            interval = self.TIMER_INTERVAL
            if interval is None:
                return
        api.create_timer(interval, self.handle_timer)

    def handle_rx(self, packet, port):
        """
        当此路由器收到数据包时由框架调用。

        该实现根据收到的数据包的具体类型调用相应的方法处理。
        你应该在这些方法中实现数据包处理逻辑，而不是修改此方法。

        !!! 不要重写此方法 !!!
        """
        if isinstance(packet, RoutePacket):
            self.expire_routes()
            self.handle_route_advertisement(packet.destination, packet.latency, port)
        elif isinstance(packet, HostDiscoveryPacket):
            self.add_static_route(packet.src, port)
        else:
            self.handle_data_packet(packet, port)

    def handle_timer(self):
        """
        当路由器应定期向邻居发送路由表时调用

        你可能需要重写此方法。
        """
        self.expire_routes()
        self.send_routes(force=True)

    def add_static_route(self, host, port):
        """
        当你需要向路由表添加静态路由时调用

        你可能需要重写此方法。
        """
        pass

    def handle_route_advertisement(self, route_dst, route_latency, port):
        """
        当此路由器收到路由通告数据包时调用

        你可能需要重写此方法。
        """
        pass

    def handle_data_packet(self, packet, in_port):
        """
        当此路由器收到数据包时调用

        你可能需要重写此方法。
        """
        pass

    def send_route(self, port, dst, latency):
        """
        从 dst 和 latency 创建控制数据包并发送。
        """

        pkt = RoutePacket(destination=dst, latency=latency)
        self.send(pkt, port=port)

    def s_log(self, format, *args):
        """
        仅当节点在模拟器中被选中时记录这些消息。

        不要移除此方法中的任何现有代码。

        :param message: 要记录的消息。
        :returns: 无。
        """
        try:
            if api.netvis.selected.name == self.name:
                self.log(format, *args)
        except:
            self.log(format, *args)


# TODO：把这些移到文件顶部？

# import abc
from collections import namedtuple
from numbers import Number  # Available in Python >= 2.7.
import unittest

from sim.api import HostEntity, get_name, current_time


# 用于表示未来的无限长时间。
# （例如，对于不应过期的路由）
FOREVER = float("+inf")  # Denotes forever in time.
INFINITY = 100

# FIXME：把 FOREVER 变成内部实现，并修复其在 __str__ 中的格式化方式？
#       改为让过期时间 expiration time = None（默认？）表示永远？（在内部，
#       我们可能想将其设为 +inf，因为它应该能正常工作？）


class _ValidatedDict(dict):
    #  __metaclass__ = abc.ABCMeta
    #
    def __init__(self, *args, **kwargs):
        super(_ValidatedDict, self).__init__(*args, **kwargs)
        for k, v in self.items():
            self.validate(k, v)

    def __setitem__(self, key, value):
        self.validate(key, value)
        return super(_ValidatedDict, self).__setitem__(key, value)

    def update(self, *args, **kwargs):
        super(_ValidatedDict, self).update(*args, **kwargs)
        for k, v in self.items():
            self.validate(k, v)

    # @abc.abstractmethod
    def validate(self, key, value):
        """如果 (key, value) 无效则抛出 ValueError。"""
        # pass
        raise NotImplementedError("Dict validation not implemented")


class Table(_ValidatedDict):
    """
    路由表

    你应该使用 `Table` 实例作为 `dict`，将目的主机映射到 `TableEntry` 对象。
    """

    owner = None

    def validate(self, dst, entry):
        """如果 dst 和 entry 类型不正确则抛出 ValueError。"""
        if not isinstance(dst, HostEntity):
            raise ValueError("destination %s is not a host" % (dst,))

        if not isinstance(entry, TableEntry):
            raise ValueError("entry %s isn't a table entry" % (entry,))

        if entry.dst != dst:
            raise ValueError(
                "entry destination %s doesn't match key %s" % (entry.dst, dst)
            )

    def __str__(self):
        o = "=== Table"
        if self.owner and getattr(self.owner, "name"):
            o += " for " + str(self.owner.name)
        o += " ===\n"

        if not self:
            o += "(empty table)"
        else:
            o += "%-6s %-3s %-4s %s\n" % ("name", "prt", "lat", "sec")
            o += "------ --- ---- -----\n"
            o += "\n".join("{}".format(v) for v in self.values())
        return o


class TableEntry(namedtuple("TableEntry", ["dst", "port", "latency", "expire_time"])):
    """
    Table 中的一个条目，表示从某个邻居到某个目的主机的路由。

    使用示例：
      rte = TableEntry(
        dst=h1, latency=10, expire_time=api.current_time()+10
      )
    """

    def __new__(cls, dst, port, latency, expire_time):
        """
        创建一个对等表条目，表示邻居通告的路由。

        TableEntry 是不可变的。

        :param dst: 路由的目的主机。
        :param port: 此路由使用的端口。
        :param latency: 路由通告的延迟（不包括到该邻居的链路延迟）。#FIXME: 还是应该包含？
        :param expire_time: 此路由过期的时间点（秒）。
        """
        if not isinstance(dst, HostEntity):
            raise ValueError("Provided destination %s is not a host" % (dst,))

        if not isinstance(port, int):
            raise ValueError("Provided port %s is not an integer" % (port,))

        if not isinstance(expire_time, Number):
            raise ValueError("Provided expire time %s is not a number" % (expire_time,))

        if not isinstance(latency, Number):
            raise ValueError("Provided latency %s is not a number" % latency)

        self = super(TableEntry, cls).__new__(cls, dst, port, latency, expire_time)
        return self

    @property
    def has_expired(self):
        return current_time() > self.expire_time

    def __str__(self):
        latency = self.latency
        if int(latency) == latency:
            latency = int(latency)
        return "%-6s %-3s %-4s %0.2f" % (
            get_name(self.dst),
            self.port,
            latency,
            self.expire_time - current_time(),
        )


# FIXME：添加端口测试
class TestTableEntry(unittest.TestCase):
    """TableEntry 的单元测试。"""

    def test_init_success(self):
        """确保 __init__ 接受有效参数。"""

    def test_init_None(self):
        """确保 __init__ 不接受 None 参数。"""

    def test_init_types(self):
        """确保 __init__ 拒绝类型错误的参数。"""

    def test_equality(self):
        """测试 __eq__、__ne__ 和 __hash__ 实现。"""

    def test_equality_forever(self):
        """确保 expire_time=FOREVER 不影响相等性测试。"""
        host1 = HostEntity()
        host1.name = "host1"

        rte1 = TableEntry(dst=host1, latency=10, expire_time=TableEntry.FOREVER)
        rte2 = TableEntry(dst=host1, latency=10, expire_time=TableEntry.FOREVER)
        self.assertEqual(rte1, rte2)
        self.assertTrue(rte1 == rte2)
        self.assertFalse(rte1 != rte2)
        self.assertEqual(hash(rte1), hash(rte2))
