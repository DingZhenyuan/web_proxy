# coding:utf-8
import socket
import datetime
import time
import threading
import redis

BUFSIZE = 1024  # 缓存容量
LIVE_TIME = 30  # 生存时间
HOST = '127.0.0.1'  # 本机
PORT = 8899 # 本机端口

data = redis.StrictRedis(host='127.0.0.1', port=6379)  # 缓存数据库


# 定义线程
class WebThread(threading.Thread):
    def __init__(self, func, args, name=''):
        threading.Thread.__init__(self)
        self.name = name
        self.func = func
        self.args = args
        print('创建新的线程：', self.name)

    def run(self):
        print('-' * 100)
        print("线程：" + self.name + "开始运行")
        self.func(*self.args)


class Access_to_Host(object):

    def handler(self, conn, addr):
        """
        对获得的客户端socket和地址进行以下的处理工作
        :param conn: 客户端socket
        :param addr: 客户端地址
        :return:
        """
        self.conn = conn
        self.addr = addr

        # 解析客户端发送给代理服务器的包
        all_src_data, hostname, port, ssl_flag = self.get_dst_host_from_header(self.conn, self.addr)
        # 进行缓存判断
        file_exist, filename = self.exist_buff(all_src_data)
        if not file_exist:
            # Buffer中没有缓存响应报文
            # 将包转发给目标服务器，并从中获取信息。（HTTPS只建立连接）
            print("响应报文不在缓存中。")
            all_dst_data = self.get_data_from_host(hostname, port, all_src_data, ssl_flag)
            if all_dst_data and not ssl_flag:
                # HTTP
                self.ssl_client_server_client(self.conn, self.conn_dst, all_dst_data, ssl_flag, filename)
            elif ssl_flag:
                # HTTPS
                sample_data_to_client = b"HTTP/1.0 200 Connection Established\r\n\r\n"
                self.ssl_client_server_client(self.conn, self.conn_dst, sample_data_to_client, ssl_flag, filename)
            else:
                print('请检查网络！连接不到目标服务器：' + hostname)

        else:
            # 文件在缓存中找到
            print("响应报文在缓存中。")
            all_dst_data = data.get(filename)
            self.conn_dst = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.buff_client_server_client(self.conn, self.conn_dst, all_dst_data, ssl_flag)

    def respond_end_recv(self, server_socket):
        """
        判断并解析响应数据，一个可以接收一个完整的包
        :param server_socket:
        :return:
        """
        recv_data = ''
        respond_header = ''  # 响应头字符串
        respond_headers = {}  # 响应头解析后的字典
        content_entity = ''  # 实体
        content_length = 0  # 实体长度
        respond_line = ''  # 响应行
        while True:
            # 完整读取响应数据
            recv_data_s = server_socket.recv(256)

            try:
                recv_data_s = recv_data_s.decode()
                # print(recv_data_s)
            except Exception as e:
                # recv_data_s = recv_data_s.decode('gbk')
                print(e)
                pass
            if "\r\n\r\n" not in recv_data and respond_header == '':
                recv_data += recv_data_s
            else:
                if respond_header == '':
                    # 第一次接收到空行,说明请求头结束
                    # 定位到空行
                    space_line_index = recv_data.index("\r\n\r\n")
                    # 提取出头部
                    respond_header = recv_data[0: space_line_index]
                    # 提取出实体部分
                    content_entity = recv_data[space_line_index + 4:]
                    # 将头部切割，以字典的形式保存
                    for index, respond in enumerate(respond_header.split('\r\n')):
                        if index == 0:
                            respond_line = respond
                        else:
                            # 冒号之前的为key
                            key = respond.split(':')[0]
                            # 设定值
                            value = respond.lstrip(key).lstrip(':')
                            # 去掉所有的空格，key为小写
                            key = key.strip(' ').lower()
                            value = value.strip(' ')
                            # 加入字典中，得到respond_headers
                            respond_headers[key] = value

                    if "content-length" in respond_headers.keys():
                        # 查看content_length是否在响应头部,若在，需要获取其值
                        content_length = int(respond_headers['content-length'])
                        if content_length == len(content_entity.encode()):
                            return respond_line, respond_header, respond_headers, content_entity
                    else:
                        # 不存在则说明只有响应头,没有实体
                        return respond_line, respond_header, respond_headers, content_entity
                else:
                    # 继续接受实体数据
                    content_entity += recv_data_s
                    if content_length == len(content_entity.encode()) + 256:
                        return respond_line, respond_header, respond_headers, content_entity

    def request_end_recv(self, client_socket):
        """
        接受并解析请求数据，一次可以收一个完整的包
        :param client_socket: 接收信息的套接字
        :return: request_line, request_header, request_headers, content_entity
        """
        recv_data = ''
        request_header = ''  # 请求头字符串
        request_headers = {}  # 请求头解析后的字典
        content_entity = ''  # 实体
        content_length = 0  # 实体长度
        request_line = ''  # 请求行
        while True:
            # 完整读取请求数据
            recv_data_s = client_socket.recv(256)
            # print('请求接收长度为', len(recv_data_s))
            if recv_data_s == b'':
                request_line = '0'
                return request_line, request_header, request_headers, content_entity
            try:
                recv_data_s = recv_data_s.decode()
            except Exception as e:
                # recv_data_s = recv_data_s.decode('gbk')
                pass
            if "\r\n\r\n" not in recv_data:
                recv_data += recv_data_s
            if "\r\n\r\n" not in recv_data:
                pass
            else:
                if request_header == '':
                    # 第一次接收到， 空行 说明请求头结束
                    # 定位到空行
                    space_line_index = recv_data.index("\r\n\r\n")
                    # 提取出头部
                    request_header = recv_data[0: space_line_index]
                    # 提取出实体部分
                    content_entity = recv_data[space_line_index + 4:]
                    # 将头部切割，以字典的形式保存
                    for index, request in enumerate(request_header.split('\r\n')):
                        if index == 0:
                            request_line = request
                        else:
                            # 冒号之前的为key
                            key = request.split(':')[0]
                            # 设定值
                            value = request.lstrip(key).lstrip(':')
                            # 去掉所有的空格，key为小写
                            key = key.strip(' ').lower()
                            value = value.strip(' ')
                            # 加入字典中，得到request_headers
                            request_headers[key] = value

                    if "content-length" in request_headers.keys():
                        # 查看content_length是否在请求头,若在，需要获取其值
                        content_length = int(request_headers['content-length'])
                        if content_length == len(content_entity.encode()):
                            return request_line, request_header, request_headers, content_entity
                    else:
                        # 不存在则说明只有请求头,没有实体
                        return request_line, request_header, request_headers, content_entity
                else:
                    # 继续接受实体数据
                    content_entity += recv_data_s
                    if content_length == len(content_entity.encode()):
                        return request_line, request_header, request_headers, content_entity

    def exist_buff(self, all_src_data):
        """
        判断客户端的请求文件是否在缓存中
        :param all_src_data: 客户端发出的报文
        :return: 是否存在，输出存在的信息, 解析获得的路径
        """
        filename = ""
        file_exist = False
        try:
            # 从数据包中解析出路径
            # print(all_src_data)
            all_src_data = all_src_data.decode()
            print(all_src_data)
            # 取http://或者https://后面的作为路径,/替换为_
            filename = all_src_data.split()[1].partition("//")[2].replace('/', '_')
        except Exception as e:
            print("获得路径失败！")
            print(e)
            return file_exist, filename

        file_exist = filename != "" and data.exists(filename)
        return file_exist, filename

    def ssl_client_server_client(self, src_conn, dst_conn, all_dst_data, ssl_flag, filename):
        """
        将从目标获得的数据发送给客户端
        :param src_conn: 客户端socket
        :param dst_conn: 目标socket
        :param all_dst_data: 从目标获取的数据
        :return:
        """
        self.src_conn = src_conn
        self.dst_conn = dst_conn
        try:
            # 发送数据给客户端服务器
            self.src_conn.sendall(all_dst_data)
        except Exception as e:
            print(e)
            print("发送数据给客户端失败！")
            return False
        # 加入获取的报文
        data.set(filename, all_dst_data)
        if data.expire(filename, LIVE_TIME):
            print("缓存" + filename + "在" + str(LIVE_TIME) + "s之后会失效")
        else:
            print("设置缓存时间失败！")
        # print(data.get(filename))

        # 缓存页面
        try:
            tmp_file = open("./buffer/" + filename, "w")
            tmp_file.writelines(all_dst_data.decode().replace('\r\n', '\n'))
            tmp_file.close()
            print(filename + "页面成功缓存！")
        except Exception as e:
            print("页面缓存失败！")
            print(e)

        if ssl_flag:
            threadlist = []
            t1 = threading.Thread(target=self.ssl_client_server, args=(self.src_conn, self.dst_conn))
            t2 = threading.Thread(target=self.ssl_server_client, args=(self.src_conn, self.dst_conn))
            threadlist.append(t1)
            threadlist.append(t2)
            for t in threadlist:
                t.start()
            # t.join()
            # 线程控制,等待线程结束后,远程主机关闭socket后，客户端到主机的socket也关闭。
            while not self.dst_conn._closed:
                time.sleep(1)
        self.src_conn.close()

    def buff_client_server_client(self, src_conn, dst_conn, all_dst_data, ssl_flag):
        """
        将从buffer获得的数据发送给客户端
        :param src_conn: 客户端socket
        :param dst_conn: 目标socket
        :param all_dst_data: 从目标获取的数据
        :return:
        """
        self.src_conn = src_conn
        self.dst_conn = dst_conn
        try:
            # 发送数据给客户端服务器
            self.src_conn.sendall(all_dst_data)
            print("从缓存中读取···")
        except Exception as e:
            print(e)
            print("读取失败！")
            return False
        print("成功从缓存中读取！")

        if ssl_flag:
            threadlist = []
            t1 = threading.Thread(target=self.ssl_client_server, args=(self.src_conn, self.dst_conn))
            t2 = threading.Thread(target=self.ssl_server_client, args=(self.src_conn, self.dst_conn))
            threadlist.append(t1)
            threadlist.append(t2)
            for t in threadlist:
                t.start()
            # t.join()
            # 线程控制,等待线程结束后,远程主机关闭socket后，客户端到主机的socket也关闭。
            while not self.dst_conn._closed:
                time.sleep(1)
        self.src_conn.close()

    def http_client_server(self, src_conn, dst_conn):
        """
        对于http后续的从客户端接收的包的处理
        :param src_conn:
        :param dst_conn:
        :return:
        """
        self.src_conn = src_conn
        self.dst_conn = dst_conn
        while True:
            try:
                # 从客户端接收一个完整的包
                request_line, request_header, request_headers, content_entity = self.request_end_recv(self.s_src)
                ssl_client_data = (request_header + "\r\n\r\n" + content_entity).encode()
            except Exception as e:
                # 获取失败，客户端断开连接
                print("客户端断开链接。")
                print(e)
                self.src_conn.close()
                return False
            if request_line == '0':
                # 获取失败，客户端断开连接
                print("客户端断开链接。")
                self.src_conn.close()
                return False
            # 获取数据成功
            if ssl_client_data:
                # 发送数据给服务器
                # 进行缓存判断
                file_exist, filename = self.exist_buff(ssl_client_data)
                if file_exist:
                    # 文件在缓存中找到
                    print("响应报文在缓存中。")
                    all_dst_data = data.get(filename)
                    print("从缓存中直接读取响应报文。")
                    try:
                        # 发送数据给客户端服务器
                        self.src_conn.sendall(all_dst_data)
                        print("成功从缓存中读取！")
                    except Exception as e:
                        print(e)
                        print("发送数据给客户端失败！")
                        # add
                        self.dst_conn.close()
                        return False
                else:
                    # 文件不在缓存中
                    try:
                        # 直接把数据发送给服务器
                        self.dst_conn.sendall(ssl_client_data)
                        print("发送数据给服务器。")
                    except Exception as e:
                        # 发送失败，服务器断开连接
                        print("服务器断开链接。")
                        self.dst_conn.close()
                        return False
                    # 发送成功
                    t = threading.Thread(target=self.http_server_client, args=(self.src_conn, self.dst_conn, filename))
                    t.start()
                    # 线程控制,等待线程结束后,远程主机关闭socket后，客户端到主机的socket也关闭。
                    # while not self.dst_conn._closed:
                    #     time.sleep(1)
                    # self.src_conn.close()
                    # return False
            else:
                self.dst_conn.close()
                self.src_conn.close()
                return False

    def http_server_client(self, src_conn, dst_conn, filename):
        """
        对于http的从服务器后续接收的包的处理
        :param src_conn:
        :param dst_conn:
        :return:
        """
        self.src_conn = src_conn
        self.dst_conn = dst_conn
        # 从服务器获取数据
        try:
            respond_line, respond_header, respond_headers, content_entity = self.respond_end_recv(self.conn_dst)
            ssl_server_data = (respond_header + "\r\n\r\n" + content_entity).encode()
        except Exception as e:
            # 获取失败，服务器断开连接
            print("服务器断开链接。")
            self.dst_conn.close()
            return False
        if ssl_server_data:
            # 发送数据到客户端
            try:
                self.src_conn.sendall(ssl_server_data)
            except Exception as e:
                # 发送失败，客户端断开连接
                print("客户端断开链接。")
                self.src_conn.close()
                return False
            # 发送成功，加入获取的报文
            data.set(filename, ssl_server_data)
            if data.expire(filename, LIVE_TIME):
                print("缓存" + filename + "在" + str(LIVE_TIME) + "s之后会失效。")
            else:
                print("设置生存时间失败！")
        else:
            self.dst_conn.close()
            return False
        self.dst_conn.close()

    def ssl_client_server(self, src_conn, dst_conn):
        """
        从客户端不断收包发送给目标服务器
        :param src_conn: 客户端socket
        :param dst_conn: 目标socket
        :return: 成功与否
        """
        self.src_conn = src_conn
        self.dst_conn = dst_conn
        while True:
            # 从客户端获取数据
            try:
                ssl_client_data = self.src_conn.recv(BUFSIZE)
            except Exception as e:
                # 获取失败，客户端断开连接
                print("客户端断开链接。")
                print(e)
                self.src_conn.close()
                return False

            # 获取数据成功
            if ssl_client_data:
                # 发送数据给服务器
                try:
                    self.dst_conn.sendall(ssl_client_data)
                except Exception as e:
                    # 发送失败， 服务器断开连接
                    print("服务器断开链接。")
                    self.dst_conn.close()
                    return False
            else:
                self.src_conn.close()
                return False

    def ssl_server_client(self, src_conn, dst_conn):
        """
        不断从目标服务器收包发送给客户端
        :param src_conn: 客户端socket
        :param dst_conn: 目标socket
        :return: 成功与否
        """
        self.src_conn = src_conn
        self.dst_conn = dst_conn

        while True:
            # 从服务器获取数据
            try:
                ssl_server_data = self.dst_conn.recv(BUFSIZE)
            except Exception as e:
                # 获取失败，服务器断开连接
                print("服务器断开链接。")
                self.dst_conn.close()
                return False

            if ssl_server_data:
                # 发送数据到客户端
                try:
                    self.src_conn.sendall(ssl_server_data)
                except Exception as e:
                    # 发送失败，客户端断开连接
                    print("客户端断开链接。")
                    self.src_conn.close()
                    return False
            else:
                self.dst_conn.close()
                return False

    def get_dst_host_from_header(self, conn_sock, addr):
        """
        从获取的socket和地址解析出header, hostname, port, ssl_flag。
        :param conn_sock: 客户端socket
        :param addr: 客户端地址
        :return: header, hostname, int(port), ssl_flag
        """
        self.s_src = conn_sock
        self.addr = addr
        header = ""
        ssl_flag = False  # 是否为HTTPS

        while True:
            # header = self.s_src.recv(BUFSIZE)
            # 接收完整的报文
            request_line, request_header, request_headers, content_entity = self.request_end_recv(self.s_src)
            header = (request_header + "\r\n\r\n" + content_entity).encode()
            # print('#' * 50)
            # print(header)
            if header:
                # header的一行含有CONNECT，即为SSL（HTTPS）
                indexssl = header.split(b"\n")[0].find(b"CONNECT")
                # print("indexsll:"+str(indexssl))
                if indexssl > -1:
                    # 说明为HTTPS报文
                    # CONNECT===7  +8 前面一个空格
                    hostname = str(header.split(b"\n")[0].split(b":")[0].decode())
                    hostname = hostname[indexssl + 8:]
                    port = 443  # HTTPS服务端口号443
                    ssl_flag = True
                    return header, hostname, port, ssl_flag

                # 对HTTP查找Host
                index1 = header.find(b"Host:")
                # print(index1)
                index2 = header.find(b"GET http")
                # print(index2)
                index3 = header.find(b"POST http")
                # print(index3)
                if index1 > -1:
                    indexofn = header.find(b"\n", index1)
                    # host:===5
                    host = header[index1 + 5:indexofn]
                elif index2 > -1 or index3 > -1:
                    # no host sample :'GET http://saxn.sina.com.cn/mfp/view?......
                    host = header.split(b"/")[2]
                else:
                    # 找不到host
                    print("src socket host:")
                    print(self.s_src.getpeername())
                    print("找不到host:" + repr(header))
                    return
                break

        # 对host处理为str形式
        host = str(host.decode().strip("\r").lstrip())
        if len(host.split(":")) == 2:
            port = host.split(":")[1]
            hostname = host.split(":")[0].strip("")
            print("host:" + hostname)
        else:
            port = 80  # HTTP端口
            hostname = host.split(":")[0].strip("")
            print("host:" + hostname)
        ssl_flag = False
        return header, hostname, int(port), ssl_flag

    def get_data_from_host(self, host, port, sdata, ssl_flag):
        """ 从host获取数据
        从host获取数据
        :param host: 目标网站ip
        :param port: 目标端口
        :param sdata: 客户端发的包
        :param ssl_flag: HTTPS标识
        :return: rc_data: 从目标获得的数据
        """
        # 创建TCP套接字
        self.conn_dst = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        all_dst_data = ""
        try:
            # 连接到目标服务器
            self.conn_dst.connect((str(host), port))
        except Exception as e:
            # 连接失败
            print(e)
            print("从host获得数据: 获得host失败:" + host)
            self.conn_dst.close()
            return False
        print("成功链接。")
        try:
            if ssl_flag:
                # https只建立链接，直接返回空
                print("https 只建立链接")
                return all_dst_data
            else:
                # 将客户端的包发出
                self.conn_dst.sendall(sdata)
        except Exception as e:
            # 发包失败
            print(e)
            print("发送数据给host失败:" + host)
            self.conn_dst.close()
            return False
        print("发送数据成功！")
        # 接收服务器发来的包
        respond_line, respond_header, respond_headers, content_entity = self.respond_end_recv(self.conn_dst)
        rc_data = (respond_header + "\r\n\r\n" + content_entity).encode()
        return rc_data


# 服务器类
class Server(object):

    def Handle_Rec(conn_socket, addr):
        pass

    # 构造函数
    def __init__(self, host, port):
        print("开始运行......")
        self.host = host
        self.port = port
        # 创建TCP/IP套接字
        self.s_s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # 当socket关闭后，本地端用于该socket的端口号立刻就可以被重用。
        self.s_s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s_s.bind((host, port))
        self.s_s.listen(20)

    # 开始运行
    def start(self):
        count = 0
        while True:
            try:
                # 获得客户端套接字和地址
                conn, addr = self.s_s.accept()
                # 每次获得客户端socket和地址之后就开启线程进行处理
                count = count + 1
                # threading.Thread(target=Access_to_Host().handler, args=(conn, addr)).start()
                WebThread(func=Access_to_Host().handler, args=(conn, addr), name=str(count)).start()
            except Exception as e:
                print(str(e))
                print("\nExcept happened!")


if __name__ == "__main__":
    if data.dbsize() > 0:
        keys = data.keys()
        print(data.delete(*keys))
    svr = Server(HOST, PORT)
    svr.start()