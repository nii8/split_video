import config
import os
cfg_data = config.get_cfg_data()

'''
vim /etc/systemd/system/runvi.service
[Unit]
Description=Run Video
After=network.target

[Service]
User=root
WorkingDirectory=/root/xiu
ExecStart=/usr/bin/python3 run_video.py
Restart=always
RestartSec=5
StandardOutput=file:/var/log/runvi.log
StandardError=file:/var/log/runvi_error.log

[Install]
WantedBy=multi-user.target



vim /etc/systemd/system/viserver.service
[Unit]
Description=Video Server
After=network.target

[Service]
User=root
WorkingDirectory=/root/xiu
ExecStart=/usr/bin/python3 video_server.py
Restart=always
RestartSec=5
StandardOutput=file:/var/log/viserver.log
StandardError=file:/var/log/viserver_error.log

[Install]
WantedBy=multi-user.target

systemctl daemon-reload
systemctl restart viserver
systemctl start runvi



systemctl daemon-reload
systemctl restart app
systemctl restart upsta
systemctl restart backend1
systemctl restart backend2
systemctl restart backend3
systemctl restart backend4
systemctl restart backend5
systemctl restart backend6
systemctl restart backend7
systemctl restart backend8
systemctl restart backend9
systemctl restart backend10
systemctl restart backend11
systemctl restart backend12
systemctl restart backend13
systemctl restart backend14
systemctl restart backend15
systemctl restart backend16

'''
def write_code(backend_key, backend_id, backend_name):
    if not os.path.exists('sse_server.py'):
        print(f"错误：文件 sse_server.py 不存在！")
        return False
    with open('sse_server.py', 'r', encoding='utf-8') as f:
        total_str = ''
        for line in f:
            if "else 'backend1'" in line:
                line = line.replace("else 'backend1'", f"else '{backend_name}'")
            if "else '001'" in line:
                line = line.replace("else '001'", f"else '{backend_key}'")
            if "else 'c0929290-6d79-40de-af54-e8aae8072060'" in line:
                line = line.replace("else 'c0929290-6d79-40de-af54-e8aae8072060'", f"else '{backend_id}'")
            if '1 else 5001' in line:
                line = line.replace("1 else 5001", f"1 else {5000 + int(backend_key)}")
            total_str += line

        # 将拼接好的完整字符串写入新文件
        with open(f'sse_server_{backend_name}.py', 'w', encoding='utf-8') as f:
            f.write(total_str)  # 写入整个字符串

        print(f"文件已成功保存为: sse_server_{backend_name}")
    return True


def write_sys_cmd(backend_name):
    sys_path = f'/etc/systemd/system/{backend_name}.service'
    sys_str = f'''[Unit]
Description=Backend Server
After=network.target

[Service]
User=root
WorkingDirectory=/root/ttt
ExecStart=/usr/bin/python3 sse_server_{backend_name}.py
Restart=always
RestartSec=5
StandardOutput=file:/var/log/backend/{backend_name}.log
StandardError=file:/var/log/backend/{backend_name}.log

[Install]
WantedBy=multi-user.target
'''
    with open(sys_path, 'w') as f:
        f.write(sys_str)


def update_sse_code():
    backend_dir = f'/var/log/backend'
    os.makedirs(backend_dir, exist_ok=True)
    name_dic = cfg_data['name_dic']
    for backend_key, value in name_dic.items():
        backend_id = value.split('-backend')[0]
        backend_name = value.replace(f'{backend_id}-', '')
        write_code(backend_key, backend_id, backend_name)
        write_sys_cmd(backend_name)

if __name__ == '__main__':
    update_sse_code()