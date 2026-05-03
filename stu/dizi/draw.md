# draw.py 说明

`draw.py` 用来调用阿里云百炼的图像模型生成图片，并保存到本地。

## 用法

```bash
python draw.py --prompt "一只可爱的橘猫"
python draw.py --prompt "一只可爱的橘猫" --out imgs/mao.png
```

## 参数

- `--prompt`：必填，绘图提示词。
- `--out`：可选，输出文件路径。不传时默认保存为 `imgs/draw.png`。

## 当前实现

- 使用官方 SDK：`dashscope` + `MultiModalConversation.call(...)`
- 当前模型：`qwen-image-2.0-2026-03-03`
- 当前地域：北京
- 图片地址从返回结构 `response.output.choices[0].message.content[0]['image']` 读取

## 省钱规则

- 如果 `--out` 指定的文件已经存在，脚本会直接打印路径并退出，不会重复调用接口。
- 想重新生成同一路径文件，先手动删除旧文件，或者改一个新的输出文件名。

## API Key

代码里优先读取环境变量 `DASHSCOPE_API_KEY`，读不到时会使用 `draw.py` 里的明文 Key。
