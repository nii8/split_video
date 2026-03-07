import config
import time
from sse_server import update_socket_status

def clean_status():
    url_cfg = config.get_json_data()
    # socket_status.json
    for key_num, value in url_cfg.items():
        status = value['status']
        user_id = value.get('user_id')
        if 'cur_time' not in value:
            continue
        dif_time = int(time.time() - value['cur_time'])
        if 'busy4' in status or 'done4' in status:
            if dif_time > 100 * 60 and user_id:
                print(f'clean_status {status} backend_key={key_num} user_id={user_id}')
                update_socket_status(key_num, 'free', user_id)
                return
        if 'busy1' in status or 'busy2' in status or 'busy3' in status or 'done1' in status or 'done2' in status or 'done3' in status:
            if dif_time > 15 * 60 and user_id:
                print(f'clean_status {status} backend_key={key_num} user_id={user_id}')
                update_socket_status(key_num, 'free', user_id)
                return

if __name__ == '__main__':
    while True:
        clean_status()
        time.sleep(30)

