import os
import shutil
import subprocess

from swarm_prompt.prompt_swarm_robot import task_name

import subprocess
from concurrent.futures import ThreadPoolExecutor


def run_app(app_run_number: int):
    print(f"Running the app for the {app_run_number + 1} time...")
    subprocess.run(["python", "./Interactive_Demo.py"])  # 替换为你的 app 所在的脚本路径
    print(f"Finished run {app_run_number + 1}")


def run_app_multiple_times(times: int):
    with ThreadPoolExecutor(max_workers=30) as executor:
        executor.map(run_app, range(times))


if __name__ == "__main__":
    run_app_multiple_times(120)

    print("CaP运行完成")
