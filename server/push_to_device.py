#!/usr/bin/env python3
"""
推送脚本到 AutoJs6 设备
协议: 8字节帧头 (int32BE length + int32BE type=1 for JSON)
"""
import socket
import json
import struct
import sys
import os
import base64

HOST = "192.168.0.109"
PORT = 7347

HEADER_SIZE = 8
TYPE_JSON = 1
TYPE_BYTES = 2


def send_json(sock, data):
    """发送 JSON 帧"""
    payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
    header = struct.pack(">ii", len(payload), TYPE_JSON)
    sock.sendall(header + payload)


def send_bytes(sock, data):
    """发送二进制帧"""
    header = struct.pack(">ii", len(data), TYPE_BYTES)
    sock.sendall(header + data)


def recv_json(sock):
    """接收一个 JSON 帧"""
    header = recv_exact(sock, HEADER_SIZE)
    data_length, data_type = struct.unpack(">ii", header)
    if data_type != TYPE_JSON:
        return None
    payload = recv_exact(sock, data_length)
    return json.loads(payload.decode("utf-8"))


def recv_exact(sock, n):
    """精确接收 n 字节"""
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("连接断开")
        buf += chunk
    return buf


def connect():
    """连接 AutoJs6 设备"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    sock.connect((HOST, PORT))
    print(f"已连接到 {HOST}:{PORT}")
    return sock


def handshake(sock):
    """握手"""
    # 发送 hello
    send_json(sock, {
        "type": "hello",
        "id": 1,
        "data": {
            "name": "OpenClaw",
            "app_version": "6.7.0",
            "app_version_code": "670",
        }
    })
    
    # 接收响应
    try:
        resp = recv_json(sock)
        print(f"握手响应: {json.dumps(resp, ensure_ascii=False)[:200]}")
        return True
    except Exception as e:
        print(f"握手失败: {e}")
        return False


def save_file(sock, filename, content, remote_path=None):
    """推送文件到设备"""
    if remote_path is None:
        remote_path = filename
    
    send_json(sock, {
        "type": "command",
        "id": 2,
        "data": {
            "\xa0cmd\xa0": "save",
            "path": remote_path,
            "content": content,
        }
    })


def save_file_as_bytes(sock, filepath, remote_name):
    """用二进制方式推送文件"""
    with open(filepath, "rb") as f:
        content = f.read()
    
    # 先发送 JSON 命令
    send_json(sock, {
        "type": "command",
        "id": 3,
        "data": {
            "\xa0cmd\xa0": "save",
            "path": remote_name,
            "content_base64": base64.b64encode(content).decode("ascii"),
        }
    })


def run_script(sock, script_path):
    """运行脚本"""
    send_json(sock, {
        "type": "command",
        "id": 4,
        "data": {
            "\xa0cmd\xa0": "run",
            "path": script_path,
        }
    })


def main():
    script_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mobile")
    script_dir = os.path.abspath(script_dir)
    
    print(f"脚本目录: {script_dir}")
    
    # 连接
    sock = connect()
    
    # 握手
    if not handshake(sock):
        print("握手失败，退出")
        sock.close()
        return
    
    # 推送脚本文件
    scripts = ["config.js", "browse.js", "publish.js", "main.js"]
    
    for script_name in scripts:
        filepath = os.path.join(script_dir, script_name)
        if not os.path.exists(filepath):
            print(f"文件不存在: {filepath}")
            continue
        
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        
        print(f"推送: {script_name} ({len(content)} 字节)")
        save_file(sock, script_name, content)
    
    print("\n所有脚本已推送完成！")
    
    # 接收可能的响应
    try:
        sock.settimeout(2)
        while True:
            resp = recv_json(sock)
            if resp:
                print(f"设备响应: {json.dumps(resp, ensure_ascii=False)[:200]}")
    except:
        pass
    
    sock.close()
    print("连接已关闭")


if __name__ == "__main__":
    main()
