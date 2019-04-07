# coding:utf-8
import socket
import time
import threading
BUFSIZE = 10240


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
        file_exist, all_dst_data, filename = self.exist_buff(all_src_data)
        # all_dst_data = all_dst_data
        if not file_exist:
            # Buffer中没有缓存响应报文
            # 将包转发给目标服务器，并从中获取信息。（HTTPS只建立连接）
            all_dst_data = self.get_data_from_host(hostname, port, all_src_data, ssl_flag)

            if not ssl_flag:
                self.save_in_buff(all_dst_data, filename)

            if all_dst_data and not ssl_flag:
                # HTTP
                # self.send_data_to_client(self.conn,all_dst_data)
                self.ssl_client_server_client(self.conn, self.conn_dst, all_dst_data)
            elif ssl_flag:
                # HTTPS
                sample_data_to_client = b"HTTP/1.0 200 Connection Established\r\n\r\n"
                self.ssl_client_server_client(self.conn, self.conn_dst, sample_data_to_client)
                # print("\nSSL_Flag-3")
            else:
                print('please check network. cannot get hostname:' + hostname)
            # self.conn.close()

        else:
            # 文件在缓存中找到
            print("read from the buffer" + '!' * 50)
            self.conn_dst = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            if all_dst_data and not ssl_flag:
                # HTTP
                self.buff_client_server_client(self.conn, self.conn_dst, all_dst_data)
            elif ssl_flag:
                # HTTPS
                sample_data_to_client = b"HTTP/1.0 200 Connection Established\r\n\r\n"
                self.ssl_client_server_client(self.conn, self.conn_dst, sample_data_to_client)
            else:
                print('please check network. cannot get hostname:' + hostname)
            # self.conn.close()

    def buff_client_server_client(self, src_conn, dst_conn, all_dst_data):
        """
        HTTP下将从目标获得的数据发送给客户端
        :param src_conn: 客户端socket
        :param dst_conn: 目标socket
        :param all_dst_data: 从目标获取的数据
        :return:
        """
        self.src_conn = src_conn
        self.dst_conn = dst_conn
        try:
            # 发送数据给客户端服务器
            for i in range(0, len(all_dst_data)):
                src_conn.send(all_dst_data[i].encode())
        except Exception as e:
            print(e)
            print("cannot sent data(HTTP/1.0 200) to SSL client")
            return False
        print("success to send the data from buff")

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


    def save_in_buff(self, all_dst_data, filename):
        """
        将获得的HTTP响应报文缓存下来
        :param all_dst_data: 从服务器获得的响应报文
        :param filename: 缓存路径
        :return: 是否缓存成功
        """
        try:
            # 存储获得的数据
            tmp_file = open("./buffer/" + filename, "w")
            # 保存的时候必须转成utf_8的编码保存
            tmp_file.writelines(all_dst_data.decode().replace('\r\n', '\n'))
            tmp_file.close()
        except Exception as e:
            print("can not save the data")
            print(e)
            return False
        print("success to save the data")
        return True

    def read_from_buff(self, src_conn, output_data):
        """
        把从buffer中读取的数据发送出去
        :param src_conn: 客户端套接字
        :param output_data: buffer中读取的数据
        :return: 成功与否
        """
        try:
            for i in range(0, len(output_data)):
                src_conn.send(output_data[i].encode(encoding='utf_8'))
        except Exception as e:
            print("can not read from the buffer")
            print(e)
            return False
        print("read from the buffer")
        return True

    def exist_buff(self, all_src_data):
        """
        判断客户端的请求文件是否在缓存中
        :param all_src_data: 客户端发出的报文
        :return: 是否存在，输出存在的信息, 解析获得的路径
        """
        filename = ""
        file_exist = False
        output_data = ""
        try:
            # 从数据包中解析出路径
            all_src_data = all_src_data.decode()
            filename = all_src_data.split()[1].partition("//")[2].replace('/', '_')
            # 去掉解析过程中filename最后一个字符是'_'的情况
            if filename[-1] == '_':
                filename = filename[:-1]
        except Exception as e:
            print("cann't get the filename")
            print(e)
            return file_exist, output_data, filename

        try:
            # 检查缓存中是否存在该文件
            f = open("./buffer/" + filename, "r")
            output_data = f.readlines()
            print("the data is in the buffer")
        except Exception as e:
            print("the data is not in the buffer")
            return file_exist, output_data, filename

        file_exist = True
        return file_exist, output_data, filename

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
                print("client disconnct ")
                print(e)
                self.src_conn.close()
                # self.dst_conn.close()
                return False

            # 获取数据成功
            if ssl_client_data:
                # 发送数据给服务器
                try:
                    self.dst_conn.sendall(ssl_client_data)
                except Exception as e:
                    # 发送失败， 服务器断开连接
                    print("server disconnct Err")
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
                print("server disconnct ")
                self.dst_conn.close()
                return False

            if ssl_server_data:
                # 发送数据到客户端
                try:
                    self.src_conn.sendall(ssl_server_data)
                except Exception as e:
                    # 发送失败，客户端断开连接
                    print("Client disconnct Err")
                    self.src_conn.close()
                    return False
            else:
                self.dst_conn.close()
                return False

    def ssl_client_server_client(self, src_conn, dst_conn, all_dst_data):
        """
        HTTP下将从目标获得的数据发送给客户端
        :param src_conn: 客户端socket
        :param dst_conn: 目标socket
        :param all_dst_data: 从目标获取的数据
        :return:
        """
        self.src_conn = src_conn
        self.dst_conn = dst_conn
        try:
            # print(all_dst_data)
            # 发送数据给客户端服务器
            self.src_conn.sendall(all_dst_data)
        except Exception as e:
            print(e)
            print("cannot sent data(HTTP/1.0 200) to SSL client")
            return False

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

    def get_src_client(self):
        """
        获取客户端ip
        :return: 客户端ip
        """
        self.src_ip = self.s_src.getpeername()
        return self.src_ip

    def send_data_to_client(self, conn_src, data):
        """
        发送数据给客户端
        :param conn_src: 客户端socket
        :param data: 数据
        :return: 成功与否
        """
        self.conn_src = conn_src
        try:
            self.conn_src.sendall(data)
        except Exception as e:
            print(e)
            print("cannot sent data to client")
            return False
        # self.conn_dst.close()

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
            # print("Loop Loop Loop")
            header = self.s_src.recv(BUFSIZE)
            # header非空的情况下进行判断
            if header:
                # header的一行含有CONNECT，即为SSL（HTTPS）
                indexssl = header.split(b"\n")[0].find(b"CONNECT")
                # print("indexsll:"+str(indexssl))
                if indexssl > -1:
                    # CONNECT===7  +8 前面一个空格
                    hostname = str(header.split(b"\n")[0].split(b":")[0].decode())
                    hostname = hostname[indexssl + 8:]
                    port = 443  # HTTPS服务端口号443
                    ssl_flag = True
                    return header, hostname, port, ssl_flag

                # 查找Host
                index1 = header.find(b"Host:")
                index2 = header.find(b"GET http")
                index3 = header.find(b"POST http")
                if index1 > -1:
                    indexofn = header.find(b"\n", index1)
                    # host:===5
                    host = header[index1 + 5:indexofn]
                elif index2 > -1 or index3 > -1:
                    # no host sample :'GET http://saxn.sina.com.cn/mfp/view?......
                    host = header.split(b"/")[2]
                else:
                    print("src socket host:")
                    print(self.s_src.getpeername())
                    print("cannot find out host!!:" + repr(header))
                    return
                break

        # 对HTTP进行处理
        host = str(host.decode().strip("\r").lstrip())
        if len(host.split(":")) == 2:
            port = host.split(":")[1]
            hostname = host.split(":")[0].strip("")
        else:
            port = 80  # HTTP端口
            hostname = host.split(":")[0].strip("")
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
            print("get_data_from_host: cannot get host:" + host)
            self.conn_dst.close()
            return False
        # con_string="("+server+","+port+")"

        try:
            if ssl_flag:
                # https只建立链接，直接返回空
                return all_dst_data
            else:
                # 将客户端的包发出
                self.conn_dst.sendall(sdata)
        except Exception as e:
            # 发包失败
            print(e)
            print("cannot send data to host:" + host)
            self.conn_dst.close()
            return False
        # buffer=[]
        # 获得目标返回的包
        rc_data = self.conn_dst.recv(BUFSIZE)
        # 剩下的data交给线程去获取
        return rc_data


# 服务器类
class Server(object):

    def Handle_Rec(conn_socket, addr):
        print("This is Handler Fun")
        pass

    # 构造函数
    def __init__(self, host, port):
        print("Server starting......")
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
        while True:
            try:
                # 获得客户端套接字和地址
                conn, addr = self.s_s.accept()
                # 每次获得客户端socket和地址之后就开启线程进行处理
                threading.Thread(target=Access_to_Host().handler, args=(conn, addr)).start()
            except Exception as e:
                print(str(e))
                print("\nExcept happened!")


if __name__ == "__main__":
    svr = Server("127.0.0.1", 8899)
    svr.start()

