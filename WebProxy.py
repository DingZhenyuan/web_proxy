# coding:utf-8
from socket import *
import threading


# 线程定义
class MyThread(threading.Thread):
    def __init__(self, func, args, name=''):
        threading.Thread.__init__(self)
        self.name = name
        self.func = func
        self.args = args
        print('-' * 100)
        print('创建新的线程：', self.name)

    def run(self):
        self.func(*self.args, self.name)


# 获取filename
def get_filename(message):
    try:
        filename = message.split()[1].partition("//")[2].replace('/', '_')
    except:
        print('!' * 100)
        return -1
    return filename


# 线程目标函数
def serve(tcp_cli_sock, buff_size, name):
    # 获取请求数据包
    try:
        message = tcp_cli_sock.recv(buff_size)  # 阻塞
    except:
        print(name + "--" + "连接被中断！")
        return

    # 对message译码
    try:
        message = message.decode()
    except:
        print(name + "--" + "字符解析出现错误！")
        return

    # 从请求中解析出filename
    filename = get_filename(message)
    if filename == -1:
        print(name + "--" + "收到报文filename为空，忽略！")
        return

    file_exist = "false"
    try:
        # 检查缓存中是否存在该文件
        f = open("./buffer/" + filename, "r")
        output_data = f.readlines()
        file_exist = "true"
        print(name + "--" + '已经存在文件！')

        # 存在则向客户端发送
        for i in range(0, len(output_data)):
            tcp_cli_sock.send(output_data[i].encode())
        print(name + "--" + '从缓存中读取')

    # 缓存中不存在该文件
    except IOError:
        print(name + "--" + '文件是否存在：', file_exist)
        if file_exist == "false":
            # 在代理服务器上创建一个tcp socket
            print(name + "--" + '创建代理服务器套接字')
            c = socket(AF_INET, SOCK_STREAM)
            # 获得host name
            hostn = message.split()[1].partition("//")[2].partition("/")[0]
            print(name + "--" + 'Host 名字：', hostn)
            try:
                # 连接到远程服务器80端口
                c.connect((hostn, 80))
                print(name + "--" + '连接到host的80端口')

                c.sendall(message.encode())
                buff = c.recv(buff_size)
                tcp_cli_sock.sendall(buff)

                tmp_file = open("./buffer/" + filename, "w")
                tmp_file.writelines(buff.decode().replace('\r\n', '\n'))
                tmp_file.close()
                print(name + "--" + '缓存存下。')
            except:
                print(name + "--" + '非法请求!')

        else:
            # 未找到HTTP相应内容
            print(name + "--" + '未找到文件！')
    tcp_cli_sock.close()


# 入口
def main():
    # 定义host, port, buff_size
    tcp_ser_host = ''
    tcp_ser_port = 8899
    buff_size = 10240
    tcp_ser_addr = (tcp_ser_host, tcp_ser_port)

    # 创建套接字
    tcp_ser_sock = socket(AF_INET, SOCK_STREAM)
    tcp_ser_sock.bind(tcp_ser_addr)
    tcp_ser_sock.listen(5)

    count = 0
    while True:
        # 开始从客户端接收请求
        print('准备开始...')
        tcp_cli_sock, tcp_cli_addr = tcp_ser_sock.accept()
        print('收到连接来自：', tcp_cli_addr)
        count = count + 1
        t = MyThread(serve, (tcp_cli_sock, buff_size), serve.__name__ + str(count))
        t.start()

    tcp_ser_sock.close()


if __name__ == '__main__':
    main()
