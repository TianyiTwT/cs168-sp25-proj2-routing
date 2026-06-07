"""
你的 CS 168 距离向量路由器

基于骨架代码：
  MurphyMc, zhangwen0411, lab352
"""

import sim.api as api
from cs168.dv import (
    RoutePacket,
    Table,
    TableEntry,
    DVRouterBase,
    Ports,
    FOREVER,
    INFINITY,
)


class DVRouter(DVRouterBase):

    # 一条路由在此间隔后应超时
    ROUTE_TTL = 15

    # -----------------------------------------------
    # 这两个标志最多只能同时开启一个
    SPLIT_HORIZON = False
    POISON_REVERSE = True
    # -----------------------------------------------

    # 是否对已过期路由发送毒性逆转
    POISON_EXPIRED = True

    # 是否在链路开启时发送更新
    SEND_ON_LINK_UP = False

    # 是否在链路断开时发送毒性逆转
    POISON_ON_LINK_DOWN = False

    def __init__(self):
        """
        当实例被初始化时调用。
        不要删除此方法中的任何现有代码。
        但在最终阶段，欢迎为内存追踪目的添加代码！
        """
        assert not (
            self.SPLIT_HORIZON and self.POISON_REVERSE
        ), "水平分割和毒性逆转不能同时开启"

        self.start_timer()  # Starts signaling the timer at correct rate.

        # 包含所有当前端口及其延迟。
        # 详见课程文档。
        self.ports = Ports()

        # 包含所有当前路由的表
        self.table = Table()
        self.table.owner = self

        ##### Begin Stage 10A #####

        ##### End Stage 10A #####

    def add_static_route(self, host, port):
        """
        向此路由器的路由表添加一条静态路由。

        当主机连接到该路由器时，由框架自动调用。

        :param host: 主机。
        :param port: 主机所连接的端口。
        :returns: 无返回值。
        """
        # 当链路开启时，`handle_link_up` 应该已将 `port` 添加到 `peer_tables`
        assert port in self.ports.get_all_ports(), "Link should be up, but is not."

        ##### Begin Stage 1 #####
        self.table[host] = TableEntry(dst=host,
                                      port=port,
                                      latency=self.ports.get_latency(port),
                                      expire_time=FOREVER)
        ##### End Stage 1 #####

    def handle_data_packet(self, packet, in_port):
        """
        当数据包到达该路由器时被调用。

        在此处转发或丢弃数据包等。

        :param packet: 到达的数据包。
        :param in_port: 数据包到达的端口。
        :return: 无返回值。
        """
        
        ##### Begin Stage 2 #####
        if packet.dst in self.table:
            t = self.table[packet.dst]
            if t.latency >= INFINITY:
                return
            self.send(packet,t.port)
        ##### End Stage 2 #####

    def send_routes(self, force=False, single_port=None):
        """
        发送路由表中所有路由的路由通告。

        :param force: 若为 True，则通告路由表中的所有路由；
                      否则仅通告自上次通告以来发生变更的路由。
               single_port: 若不为 None，则仅向该端口发送更新；
                             与 handle_link_up 配合使用。
        :return: 无返回值。
        """
        
        ##### Begin Stages 3, 6, 7, 8, 10 #####
        for p in self.ports.get_all_ports():
            for dst,entry in self.table.items():

                if entry.port == p:
                    if self.SPLIT_HORIZON:
                        pass
                    elif self.POISON_REVERSE:
                        self.send_route(p,dst,INFINITY)
                    else:
                        self.send_route(p,dst,entry.latency)
                else:
                    if entry.latency >= INFINITY:
                        self.send_route(p,dst,INFINITY)
                    else:
                        self.send_route(p,dst,entry.latency)
        ##### End Stages 3, 6, 7, 8, 10 #####

    def expire_routes(self):
        """
        从路由表中清除已过期的路由。
        """
        
        ##### Begin Stages 5, 9 #####
        expired_table = []

        for dst,entry in self.table.items():
            if entry.expire_time == FOREVER:
                continue
            if entry.expire_time < api.current_time():
                if dst not in expired_table:
                    expired_table.append(dst)

        for t in expired_table:
            if self.POISON_EXPIRED == True:
                table = self.table[t]
                self.table_update(table.dst,table.port,INFINITY)
            else:
                self.s_log(f"delete {t}")
                self.table.pop(t)
        ##### End Stages 5, 9 #####

    def handle_route_advertisement(self, route_dst, route_latency, port):
        """
        当路由器收到来自邻居的路由通告时被调用。

        :param route_dst: 被通告路由的目的地。
        :param route_latency: 从邻居到目的地的延迟。
        :param port: 通告到达的端口。
        :return: 无返回值。
        """
        
        ##### Begin Stages 4, 10 #####
        latency = self.ports.get_latency(port)
        total_latency = route_latency + latency
        if route_dst not in self.table:
            self.table_update(route_dst,port,total_latency)
        else:
            t = self.table[route_dst]
            if t.port == port:
                self.table_update(route_dst,port,total_latency)
            if total_latency < t.latency:
                self.table_update(route_dst,port,total_latency)
        ##### End Stages 4, 10 #####

    def handle_link_up(self, port, latency):
        """
        当连接到此路由器的链路开启时由框架调用。

        :param port: 链路所连接的端口。
        :param latency: 链路延迟。
        :returns: 无返回值。
        """
        self.ports.add_port(port, latency)

        ##### Begin Stage 10B #####

        ##### End Stage 10B #####

    def handle_link_down(self, port):
        """
        当连接到此路由器的链路断开时由框架调用。

        :param port: 链路使用的端口号。
        :returns: 无返回值。
        """
        self.ports.remove_port(port)

        ##### Begin Stage 10B #####

        ##### End Stage 10B #####

    # 随意添加任何辅助方法！
    def table_update(self,dst,port,latency,TTL=ROUTE_TTL):
        self.table[dst] = TableEntry(dst=dst,port=port,latency=latency,expire_time=api.current_time()+TTL)