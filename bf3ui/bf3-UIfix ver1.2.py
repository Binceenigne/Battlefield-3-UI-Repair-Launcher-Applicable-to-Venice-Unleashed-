import os
import subprocess
import time
import pymem
import pymem.exception
import sys
import tkinter as tk
from tkinter import messagebox
import win32gui 
import win32process 

def show_error_popup(message):
    root = tk.Tk()
    root.withdraw()  
    messagebox.showerror("[战地3UI修复启动器] 错误", message)
    root.destroy()

def find_target_process_by_window_title(title_prefix):
    def callback(hwnd, hwnds):
        if win32gui.IsWindowVisible(hwnd) and title_prefix in win32gui.GetWindowText(hwnd):
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            hwnds.append(pid)
        return True

    hwnds = []
    win32gui.EnumWindows(callback, hwnds)
    return hwnds[0] if hwnds else None

def main():
    # ================= 配置区 =================
    PROCESS_NAME = "vu.exe"               # 目标进程名称
    WINDOW_TITLE_PREFIX = "Battlefield 3 - Venice Unleashed"  # 窗口标题部分内容
    MAX_WAIT_PROCESS = 30                 # 最大等待进程时间（秒）
    RETRY_INTERVAL = 2                    # 内存校验重试间隔（秒）
    MAX_ATTEMPTS = 10                     # 单地址最大尝试次数
    
    # 内存修改配置
    PATCHES = [
        {   
            "name": "1",
            "address": 0x01766A97,
            "original": bytes.fromhex("81FF0005"),
            "new": bytes.fromhex("81FF00FF")
        },
        {
            "name": "2",
            "address": 0x01766A9F,
            "original": bytes.fromhex("81FBD002"),
            "new": bytes.fromhex("81FBD0FF")
        },
        {
            "name": "3",
            "address": 0x0094FC88,
            "original": bytes.fromhex("81F90005"),
            "new": bytes.fromhex("81F900FF")
        },
        {
            "name": "4",
            "address": 0x0094FC61,
            "original": bytes.fromhex("3DD00200"),
            "new": bytes.fromhex("3DD002FF")
        }
    ]
    # ================= 以下为执行逻辑 =================

    # 获取当前工作目录
    script_dir = os.getcwd()
    exe_path = os.path.join(script_dir, PROCESS_NAME)

    # 调试信息输出
    print(f"[系统信息] 脚本目录：{script_dir}")
    print(f"[路径检测] 目标路径：{exe_path}")
    print(f"[目录列表] 当前内容：{os.listdir(script_dir)}")

    # 验证目标文件存在性
    if not os.path.isfile(exe_path):
        print(f"\n[致命错误] 未找到 {PROCESS_NAME}")
        print("可能原因：")
        print("1. 文件未与脚本放于同一目录")
        print("2. 文件名大小写不匹配（实际名称：{0}）".format(
            next((f for f in os.listdir(script_dir) if f.lower() == PROCESS_NAME.lower()), "未找到相似文件")
        ))
        print("3. 文件被隐藏或系统保护（尝试取消隐藏属性）")
        print("4. 防病毒软件拦截")
        show_error_popup(f"[启动错误] 未找到 {PROCESS_NAME}\n请检查脚本目录下是否存在 {PROCESS_NAME} 文件。\n可能原因：\n1. 文件未与脚本放于同一目录\n2. 文件名大小写不匹配\n3. 文件被隐藏或系统保护\n4. 防病毒软件拦截")
        return

    # 启动目标程序
    print(f"\n[启动器] 正在启动 {PROCESS_NAME}...")
    try:
        subprocess.Popen(exe_path, cwd=script_dir)
    except Exception as e:
        print(f"[启动错误] 无法执行程序：{str(e)}")
        show_error_popup(f"[启动错误] 无法执行程序：{str(e)}\n请检查 {PROCESS_NAME} 的系统权限以及是否使用管理员权限启动UI修复启动器。")
        return

    # 等待进程初始化
    print("\n[进程监控] 等待目标进程启动...")
    pm = None
    start_time = time.time()
    target_pid = None

    while time.time() - start_time < MAX_WAIT_PROCESS:
        try:
            # 通过窗口标题查找目标进程
            target_pid = find_target_process_by_window_title(WINDOW_TITLE_PREFIX)
            if target_pid:
                pm = pymem.Pymem()
                pm.open_process_from_id(target_pid)  # 通过PID附加到进程
                print(f"[进程就绪] 成功附加到进程 (PID: {target_pid})")
                time.sleep(3)
                break
            else:
                print(f"等待中... 已耗时 {int(time.time()-start_time)} 秒", end='\r')
                time.sleep(1)
        except pymem.exception.ProcessNotFound:
            print(f"等待中... 已耗时 {int(time.time()-start_time)} 秒", end='\r')
            time.sleep(1)
    else:
        print("\n[超时错误] 进程未在指定时间内启动")
        show_error_popup(f"[超时错误] 进程未在指定时间内启动\n请检查 {PROCESS_NAME} 是否正常运行以及是否使用管理员权限启动UI修复启动器。")
        return

    # 执行内存修改
    print("\n[内存操作] 开始注入...")
    success_count = 0
    error_messages = []  # 用于存储错误信息

    for patch in PATCHES:
        attempts = 0
        print(f"\n处理 {patch['name']} ({hex(patch['address'])})")
        current_error = None  # 用于存储当前补丁的错误信息

        while attempts < MAX_ATTEMPTS:
            try:
                # 读取当前内存值
                current = pm.read_bytes(patch["address"], len(patch["original"]))
                
                if current == patch["original"]:
                    # 执行写入操作
                    pm.write_bytes(patch["address"], patch["new"], len(patch["new"]))
                    # 二次验证
                    verify = pm.read_bytes(patch["address"], len(patch["new"]))
                    if verify == patch["new"]:
                        print(f"  ✓ 成功写入 {patch['new'].hex().upper()}")
                        success_count += 1
                        break
                    else:
                        print(f"  ! 写入验证失败（当前值：{verify.hex().upper()}）")
                        current_error = f"[写入错误] 写入验证失败（当前值：{verify.hex().upper()}）\n 请检查 {PROCESS_NAME} 内存状态以及是否使用管理员权限启动UI修复启动器。"
                else:
                    print(f"  ! 内存不匹配（预期：{patch['original'].hex().upper()}，实际：{current.hex().upper()}）")
                    current_error = f"内存不匹配（预期：{patch['original'].hex().upper()}，实际：{current.hex().upper()}）\n 请检查 {PROCESS_NAME} 内存状态以及是否有杀毒软件拦截。"

                attempts += 1
                if attempts < MAX_ATTEMPTS:
                    time.sleep(RETRY_INTERVAL)
                    
            except Exception as e:
                print(f"  × 操作异常：{str(e)}")
                current_error = f"操作异常：{str(e)}"
                attempts += 1
                time.sleep(RETRY_INTERVAL)
        else:
            print(f"  × 达到最大重试次数（{MAX_ATTEMPTS}次）")
            if current_error:
                error_messages.append(current_error)

    # 在所有补丁处理完成后，检查是否有错误信息并弹窗
    if error_messages:
        full_error_message = "\n".join(error_messages)
        show_error_popup(full_error_message)
            

    # 收尾处理
    pm.close_process()
    print(f"\n[完成统计] 成功注入 {success_count}/{len(PATCHES)} 个补丁")
    print("提示：若注入未完全成功，请检查：")
    print("1. 以管理员身份重新运行脚本")
    print("2. 先打开客户端再运行服务器")
    print("3. 关闭内存保护类软件")

if __name__ == "__main__":
    print("=== 内存修改工具 (请以管理员权限运行) ===")
    main()
    print("\n[提示] 脚本将在5秒后自动退出，请享受游戏...")
    time.sleep(5)
    sys.exit()