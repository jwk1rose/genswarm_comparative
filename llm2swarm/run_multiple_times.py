"""
Copyright (c) 2024 WindyLab of Westlake University, China
All rights reserved.
"""

import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from datetime import datetime
from pathlib import Path
from collections import Counter


def run_command(index, command, timeout):
    try:
        print(f"[{index}] Running: {command}")
        result = subprocess.run(command, shell=True, timeout=timeout, capture_output=True, text=True)
        return f"[✓] {index} SUCCESS | {command}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    except subprocess.TimeoutExpired:
        return f"[⏱] {index} TIMEOUT | {command}"
    except Exception as e:
        return f"[✗] {index} ERROR | {command} | {str(e)}"


def run_all(llm_list, prompt_list, task_list, repeat_count=1, max_workers=1, timeout=1800, log_path="run_log.txt"):
    commands = []
    index = 0

    for llm in llm_list:
        for prompt in prompt_list:
            for task in task_list:
                for repeat in range(repeat_count):
                    cmd = (
                        f"python syntax-generator.py "
                        f"--task_name {task} "
                        f"--prompt_type {prompt} "
                        f"--llm {llm}"
                    )
                    commands.append((index, cmd))
                    index += 1

    results = []
    stats = Counter()
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)

    with open(log_path, "w", encoding="utf-8") as log_file:
        log_file.write(f"=== Run started at {datetime.now()} ===\n\n")
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(run_command, idx, cmd, timeout): idx for idx, cmd in commands}
            with tqdm(total=len(futures), desc="Executing Tasks", ncols=100) as pbar:
                for future in as_completed(futures):
                    result = future.result()
                    results.append(result)
                    log_file.write(result + "\n")

                    # 分类统计
                    if "SUCCESS" in result:
                        stats["success"] += 1
                    elif "TIMEOUT" in result:
                        stats["timeout"] += 1
                    elif "ERROR" in result:
                        stats["error"] += 1
                    else:
                        stats["other"] += 1

                    # 更新进度条显示
                    pbar.set_postfix({
                        "✓": stats["success"],
                        "⏱": stats["timeout"],
                        "✗": stats["error"]
                    })
                    pbar.update(1)

        # 生成统计报告
        total = len(results)
        summary = (
            f"\n=== Execution Summary ===\n"
            f"Total Tasks: {total}\n"
            f"✓ Success:   {stats['success']}\n"
            f"⏱ Timeout:   {stats['timeout']}\n"
            f"✗ Error:     {stats['error']}\n"
        )
        print(summary)
        log_file.write(summary)


if __name__ == "__main__":
    llm_model_list = ["gpt4o"]
    prompt_type_list = [
        "default",
        # "simple",
        # "simple_strategy",
        # "narrative",
        # "structured_default",
        # "structured_strategy"
    ]
    task_list = [
        # "shaping",
        "encircling",
        # "covering",
        # "exploration"
    ]
    repeat_each = 100  # 每种组合重复几次
    max_concurrent = 100
    per_task_timeout = 1800
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file_path = f"logs/run_log_{timestamp}.txt"

    run_all(
        llm_list=llm_model_list,
        prompt_list=prompt_type_list,
        task_list=task_list,
        repeat_count=repeat_each,
        max_workers=max_concurrent,
        timeout=per_task_timeout,
        log_path=log_file_path,
    )
