import os
import shutil
import subprocess

from swarm_prompt.prompt_swarm_robot import task_name

# 指定要处理的文件夹路径
origin_directory = '/home/derrick/Comparative-Swarm/workspace'

import subprocess
from concurrent.futures import ThreadPoolExecutor


def run_app(app_run_number: int):
    print(f"Running the app for the {app_run_number + 1} time...")
    subprocess.run(["python", "metagpt/software_company.py"])  # 替换为你的 app 所在的脚本路径
    print(f"Finished run {app_run_number + 1}")


def run_app_multiple_times(times: int, max_workers: int = 30):
    # 使用 max_workers 参数限制最大线程数
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 当超过 max_workers 时，其余任务会排队等待空闲线程
        executor.map(run_app, range(times))


if __name__ == "__main__":
    run_app_multiple_times(120)

    for filename in os.listdir(origin_directory):
        if filename.startswith(f'{task_name}_'):  # 根据需要的前缀过滤文件
            folder_name = task_name  # 获取前缀部分
            folder_path = os.path.join(origin_directory, 'metagpt', task_name)  # 创建文件夹路径

            # 如果文件夹不存在，则创建它
            if not os.path.exists(folder_path):
                os.makedirs(folder_path, exist_ok=True)

            # 移动文件到对应的文件夹
            shutil.move(os.path.join(origin_directory, filename), os.path.join(folder_path, filename))

    print("文件已成功移动到对应的文件夹中。")
