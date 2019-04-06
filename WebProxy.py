# coding:utf-8
from socket import *
import re


def get_host(message):  # 提取头部
    a = re.search("Host: (.*)\r\n", message)
    while type(a) == 'NoneType':
        a = re.search("Host: (.*)", message)

    host = a.group(1)
    a = host.split()
    filename = message.split()[1].partition("//")[2].replace('/', '_')
    if len(a) == 1:
        return a[0], 80, filename
    else:
        return a[0], int(a[1]), filename


# 创建socket，绑定到端口，开始监听
tcp_ser_host = ''
tcp_ser_port = 8899
tcp_ser_addr = (tcp_ser_host, tcp_ser_port)

buff_size = 10240

tcp_ser_sock = socket(AF_INET, SOCK_STREAM)  # 创建套接字
tcp_ser_sock.bind(tcp_ser_addr)  # 绑定地址

tcp_ser_sock.listen(5)

while True:
    # 开始从客户端接收请求
    # print('Ready to serve...')
    print('接受请求')
    tcp_cli_sock, tcp_cli_addr = tcp_ser_sock.accept()
    # print('Received a connection from: ', tcp_cli_addr)
    print('收到连接来自：', tcp_cli_addr)

    message = tcp_cli_sock.recv(buff_size)
    print('*' * 50)
    print(message)
    print('*' * 50)
    message = message.decode()
    print('*' * 50)
    print(message)
    print('*' * 50)

    # 从请求中解析出filename
    # filename = message.split()[1].partition("//")[2].replace('/', '_')
    server, port, filename = get_host(message)

    file_exist = "false"
    try:
        # 检查缓存中是否存在该文件
        f = open("./buffer/" + filename, "r")
        output_data = f.readlines()
        file_exist = "true"
        # print('File Exists!')
        print('存在文件！')

        # 向客户端发送
        for i in range(0, len(output_data)):
            tcp_cli_sock.send(output_data[i].encode())
        # print('Read from cache')
        print('从cache读取')

    # 缓存中不存在该文件，异常处理
    except IOError:
        # print('File Exist: ', file_exist)
        print('文件是否存在：', file_exist)
        if file_exist == "false":
            # 在代理服务器上创建一个tcp socket
            # print('Creating socket on proxy server')
            print('创建代理服务器套接字')
            c = socket(AF_INET, SOCK_STREAM)

            hostn = message.split()[1].partition("//")[2].partition("/")[0]
            # print('Host Name: ', hostn)
            print('Host 名字：', hostn)
            try:
                # 连接到远程服务器80端口
                c.connect((hostn, 80))
                # print('Socket connected to port 80 of the host')
                print('连接到host的80端口')

                c.sendall(message.encode())
                # 读入buffer
                buff = c.recv(buff_size)

                tcp_cli_sock.sendall(buff)

                tmp_file = open("./buffer/" + filename, "w")
                tmp_file.writelines(buff.decode().replace('\r\n', '\n'))
                tmp_file.close()
                # print("Save into the buffer.")
                print('缓存存下')
            except:
                # print("Illegal request")
                print('非法请求')

        else:
            # 未找到HTTP相应内容
            # print('File Not Found...Stupid Andy')
            print('未找到文件')
    tcp_cli_sock.close()
tcp_ser_sock.close()

