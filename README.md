# Comparative使用说明

## 前述

​	本仓库的大框架是fork了MetaGPT的仓库, 因为其文件体量最大, 其他用于对比试验的还有Code as Policies(只有1个python文件), GPT(只有1一个python文件), 由于CaP和GPT的文件量为最低单位, 不再新开一个仓库, 都放在了该仓库中, 一起做对比试验

​	注意, 要使用v0.8-release分支, main分支暂时有bug不要使用

## 文件夹说明

- CaP: 存储了用于对比试验的CaP的代码
- metagpt: 存储了做对比试验的MetaGPT的主体代码
- config: 用于配置集群任务的task ， 配置LLM的代理网址、api token
- swarm_prompt: 存储了集群任务的全部提示词
- workspace: 内部将会有CaP, metagpt三个子文件夹, 分别存储各自的对比试验生成的代码
- requirements.txt: MetaGPT的依赖包（和CaP需要的不一样）
- 根目录下其他文件夹和文件: 均为metagpt的自带文件, 不必关注

## 环境说明



建议python =3.10

#### MetaGPT对比试验：

```
conda create -n comparative_metagpt_py310 python=3.10
```

```
conda activate comparative_metagpt_py310
```

```
pip install -r requirements.txt
```

#### CaP对比试验：

``` 
conda create -n comparative_cap_py310 python=3.10
```

```
conda activate comparative_cap_py310
```

```
pip install -r CaP/requirements.txt
```



## 运行

### metagpt

​	metagpt需要关注这几个文件夹: 

- config/config2.yaml: 在这里设置LLM的网址和API, 注意, 网址要有/v1后缀
- config/experiment_config.yaml: 这里设置集群任务 task_name
- metagpt/multi_run.py: 主函数入口, 可以设置运行几次softward_company.py文件, 也就生成几份代码
- metagpt/software_company.py: 这里在startup()函数的idea中输入集群任务指令 user_requirements
- metagpt/actions/action.py: 在这里set_prefix()函数中 设置system_prompt, 输入集群环境描述/机器人API等要求
- metagpt/provider/base_llm.py： 这里根据o1mini没有system prompt的特性，把system prompt直接和task requirement合并在一个str里
使用安装好依赖的python环境直接运行`metagpt/multi_run_metagpt.py`即可在workspace中得到对应的集群控制代码

```
conda activate comparative_metagpt_py310
python metagpt/multi_run_metagpt.py
```



### **CaP**

​	CaP的关键文件有这几个：

- Interactive_Demo.py： 运行一次对比试验的文件
- multi_run_cap.py： 多次运行Interactive_Demo.py
- prompt_swarm_robot.py： 提示词管理

使用安装好依赖的python运行`CaP/multi_run_cap.py`即可在workspace的CaP文件夹得到对应的代码

```
conda activate comparative_cap_py310
```

```
python CaP/multi_run_cap.py
```





