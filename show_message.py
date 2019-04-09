import os
from tkinter import *
from time import sleep
import main as mn

class DirList(object):

    def __init__(self, initdir=None):
        self.top = Tk()
        # 标题
        self.label = Label(self.top, text='SHOW SOME INFO', font=('Helvetica', 12, 'bold'))
        self.label.pack()

        self.cwd = StringVar(self.top)

        # 滚动条
        self.dirfm = Frame(self.top)
        self.dirsb = Scrollbar(self.dirfm)
        self.dirsb.pack(side=RIGHT, fill=Y)

        # 显示框
        self.dirs = Listbox(self.dirfm, height=20, width=100, yscrollcommand=self.dirsb.set)
        # self.dirs.bind('<Double-1>', self.setDirAndGo)
        self.dirsb.config(command=self.dirs.yview)
        self.dirs.pack(side=LEFT, fill=BOTH)
        self.dirfm.pack()

        # 下方按钮组合
        self.bfm = Frame(self.top)
        # 清空
        self.clr = Button(self.bfm, text='Clear', command=self.clrDir,
                          activeforeground='white', activebackground='blue', width=20)
        # 刷新
        self.update = Button(self.bfm, text='Update', command=self.doLS,
                             activeforeground='white', activebackground='green', width=20)
        # 退出
        self.quit = Button(self.bfm, text='Quit', command=self.top.quit,
                           activeforeground='white', activebackground='red', width=20)
        self.clr.pack(side=LEFT)
        self.update.pack(side=LEFT)
        self.quit.pack(side=LEFT)
        self.bfm.pack()

        if initdir:
            self.doLS()

    def clrDir(self, ev=None):
        # 清空数据库
        if mn.data.dbsize() > 0:
            keys = mn.data.keys()
            print(mn.data.delete(*keys))
        self.doLS()

    def doLS(self, ev=None):
        self.dirs.delete(0, END)
        list = []
        if mn.data.dbsize() > 0:
            list = mn.data.keys()
        for eachFile in list:
            self.dirs.insert(END, eachFile)
        self.dirs.config(selectbackground='LightSkyBlue')


def main():
    d = DirList(os.curdir)
    mainloop()


if __name__ == '__main__':
    main()