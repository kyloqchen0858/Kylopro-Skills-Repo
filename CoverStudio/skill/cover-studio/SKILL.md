---
name: cover-studio
description: 与设计师在本地封面工坊共同制作封面。读取构图与历史版本、原位试素材、编辑蒙版、分层并输出工艺候选稿。
---

从工作台根目录运行 Python 3.10+。把本目录中的 skill 交给其他 Agent 时，同时指向含 studio.py 的工作台目录。运行命令时指定目标工程。默认工程是 projects/wish。

```text
python studio.py --project projects/new-cover init --concept "月光下的航行" --width 148 --height 210 --bleed 6
python studio.py --project projects/new-cover state
python studio.py --project projects/new-cover history
python studio.py --project projects/new-cover import element.png
python studio.py --project projects/new-cover apply step.json
python studio.py --project projects/new-cover preview review.svg
python studio.py --project projects/new-cover export
```

读取 state 返回的 rev、objects、locks 和已选构图。先说明一个对象的视觉任务，例如“用朝右上的轮廓呼应对角线”。用当前 Agent 已有的搜索或图像生成能力取得合适的独立图片，导入后用返回的素材键替换目标对象，source 写来源或生成说明。候选用独立版本试放，保留可比较的几何位置。设计者锁定的属性只能由其主动解锁。

每个有意义的步骤提交一次，label 写画面发生的变化。下例的 base 换成刚读取的版本。from 可填历史版本号，从该快照建立分支。省略 from 表示从最新版继续。版本冲突时重新读取工程，对照人工修改后再决定如何继续。

```json
{"base":1,"label":"把主体向右移 5 mm","ops":[{"action":"edit","id":"subject","values":{"x":101}}]}
```

- 坐标和成品外画布共用毫米，x/y 是对象中心，w/h 是尺寸，angle 是顺时针度数。path 与蒙版笔触使用对象自身的 0–100 坐标。
- choices 使用 recommend:true 推荐，省略时随机，或提供三个 choices。layout 的 layout 值见 design.py 的 LAYOUTS。设定位置也可直接 edit。
- edit 支持位置、尺寸、角度、fill、text、font、italic、align、uv、mask、name、kind、asset、source、blend、opacity、gradientMap。原位替图写 kind=image 和 import 返回的 asset。替换图后复核已有轮廓，必要时移除旧 outline。锁分 layout、asset、mask。
- blend 支持 normal、multiply、screen、overlay、soft-light、color-burn、darken、lighten；opacity 为 0–1。
- add 接受 name、kind 和 values。repeat 接受 id、pivot（毫米坐标对）、degrees、count。order 接受 id 和 by。lock 接受 id 和 locks 数组。texture 设置画布最顶层的全局质感层。
- 修改 mask 时先读已有对象并合并。cut 是遮挡来源对象 ID，fade 为布尔，crop 为局部 [左,上,宽,高]；strokes 为 [{points:[[x,y],...],size:宽度百分比,restore:false}]；outline 接收 SVG 路径；organic 启用不规则噪点边缘与细金属描边；knockout 为文字自动生成带羽化的反向遮罩以挖空底层线条。UV 导出沿用对象的变换、蒙版与文字避让。
- process 接受 plate、machine、name。分版导出到工程的 exports 中，UV 文件黑色为覆盖，透明为留空。设备未知时留空。用交接包的 Illustrator.jsx 在 Illustrator 另存、重开并检验一份独立的 UV 修改副本。查看 verification.txt 核验实际结果。
- 复制完整工作台与项目目录即可迁移，核心无模型依赖。SAM2 是可选的独立本地环境，迁移方式见工作台 README。

## 设计协作
读取 state.discussion，按意见的 target、targetName、purpose 与 refs 处理。参考图位于本工程 assets。依据用途借鉴配色、材质、版式或生成新的独立图层，元素题材由概念决定。项目长期配色偏好为干净中性白、冷白或明确指定的色彩；禁用米黄、纸黄作为底色。保留已锁对象。
用 comment 提交意见，用 reply 回写实际结果（note 为意见 ID，reply 为回复，status 为已处理或待处理）。删除对象用 remove 与 id，旧版可恢复。浏览器的「交给本机 Agent」调用已配置的 Codex CLI，传入本条意见引用的图片；其他模型可用同一套 state / apply 命令。活字可设置 font、italic 和 align=left。

## 接手续作 · 从产品开始
新对话先定位品牌与 SKU，运行 `python studio.py --project projects/wish handoff`。对照 state.workflow 的原始理念、items 的交付物/依赖/状态/证据/下一动作、反馈及已批准方案。每次新增产品先拆解组件，包括独立附件、跨组件联动、工艺与纸样。向用户列出总数、完成数及剩余数；每有实际产物或用户决定，用 item_update 更新，完成须有可追溯依据。
先 plan_edit 写视觉稿及 routes（每项含 id/title/motif/intent/elements/front/spine/back/craft），再展示多个完整外封布局。前封、脊、封底应共同承担叙事。选择方案和批准生图是独立状态。plan_approve 专供用户确认；Agent 不得代替用户执行。在 approved=false 时只做文字、参考拆解、元素清单与几何版式示意。新的视觉稿或方向反馈使批准失效。后续对话从用户确认的版本继续。装订、内页页数、纸厚和实测脊宽仍待确认时，展示意图图，不将其交给制版。
每个 SKU 独立保存 project.sqlite。品牌工作台各阶段通过 stage_note 记载纸张及工艺依据，已实现的前封编辑器保留用于查看历史作品。

## 视觉稿中的底图选择
用户选定的展开草图定义轮廓、字区、留白及封底锚点。按原图复用路径与坐标；底图提供纹理，记录素材、混合模式、不透明度、遮罩与调色范围。先看骨架，再加局部材质，对照原稿判断主体是否仍清晰。回望之弧与回声地形分别在 projects/wish/jackets/orbit 和 echo。INKA+ 单独出 DEBOSS.svg。

## PS 级像素合成管线（Codex 续作必读）

不要再用“纯白矩形盖在线条上”或“硬贴未处理图片”的方式拼贴。严格采用 **三层分离** 流程：
1. **原始素材层**：优先导入高反差黑白/灰度纹理素材（月面、水墨、大理石、星空噪点、暗纹等），方便程序统一上色。
2. **合成处理层（在对象属性与 mask 上配置，无需重新生成整张图）**：
   - `gradientMap`：灰度到 2–5 色带重映射（SVG sRGB `<feColorMatrix saturate=0>` + 33 采样 `<feComponentTransfer>`）。
   - `mask.organic`：基于 `<feTurbulence>` + `<feDisplacementMap>` 的有机海岸线/撕纸边缘（仅置换蒙版 alpha，保持内部纹理清晰不扭曲），支持沿该边缘生成 1–2px 金属描边与金箔微闪。
   - `blend` + `opacity`：`screen` 去黑底、`multiply` 去白底、`overlay` / `soft-light` 融入底纹。
3. **矢量骨架、文字避让与全局质感层**：
   - 禁止在文字下方垫纯白实心矩形遮挡线条；在文字对象上设置 `mask.knockout` 自动挖空下方矢量线条并保留底层背景纹理。
   - 使用 `action: "texture"` 在画布最顶层叠加 `paper` / `grain` / `fiber` / `asset` 全局质感层（`multiply` / `overlay` / `soft-light`，推荐不透明度 0.12–0.22），导出 `ART.svg` 自动合成、`UV.svg` / `DEBOSS.svg` 自动排除。

### 可直接调用的 JSON 操作示例

```json
{
  "base": 12,
  "label": "应用深海蓝白渐变映射 + 海岸线细金边 + 文字避让 + 全局纸纹",
  "ops": [
    {
      "action": "edit",
      "id": "p2",
      "values": {
        "blend": "normal",
        "opacity": 1,
        "gradientMap": {
          "enabled": true,
          "stops": [
            {"offset": 0.0, "color": "#091334"},
            {"offset": 0.52, "color": "#1d4ed8"},
            {"offset": 1.0, "color": "#f5f8ff"}
          ],
          "invert": false,
          "strength": 1.0
        },
        "mask": {
          "organic": {
            "enabled": true,
            "scale": 10.0,
            "frequency": 0.055,
            "octaves": 4,
            "seed": 17,
            "inset": 2.5,
            "feather": 0.12,
            "rimEnabled": true,
            "rimColor": "#d4af37",
            "rimWidth": 0.55,
            "rimOpacity": 0.94,
            "rimShimmer": true
          }
        }
      }
    },
    {
      "action": "edit",
      "id": "p34",
      "values": {
        "mask": {
          "knockout": {
            "enabled": true,
            "pad": 3.5,
            "feather": 2.2,
            "scope": "linework"
          }
        }
      }
    },
    {
      "action": "texture",
      "values": {
        "enabled": true,
        "kind": "paper",
        "blend": "multiply",
        "opacity": 0.16,
        "scale": 1.0,
        "contrast": 1.0
      }
    }
  ]
}
```

### 字段速查
- `gradientMap`：`enabled`（bool）、`stops`（2–5 项 `{offset: 0..1, color: "#rrggbb"}`）、`invert`（bool）、`strength`（0..1）。传 `null` 或 `{}` 清除。
- `mask.organic`：`enabled`（bool）、`scale`（0..40 mm）、`frequency`（0.005..0.3）、`octaves`（1..6）、`seed`（0..9999）、`inset`（0..30 mm）、`feather`（0..5 mm）、`rimEnabled`（bool）、`rimColor`（hex）、`rimWidth`（0.1..4.0 mm，约 0.55 mm ≈ 1.5–2px）、`rimOpacity`（0..1）、`rimShimmer`（bool）。
- `mask.knockout`：`enabled`（bool）、`pad`（0..25 mm）、`feather`（0..15 mm）、`scope`（`"linework"` 仅挖空下方 `linework`/`ring`/`trail`，或 `"below"` 挖空下方全部非底图层）。
- `action: "texture"`：`enabled`（bool）、`kind`（`"paper"` | `"grain"` | `"fiber"` | `"asset"`）、`blend`（`"multiply"` | `"overlay"` | `"soft-light"`）、`opacity`（0..1）、`scale`（0.25..4.0）、`contrast`（0.3..2.5）、`asset`（当 `kind="asset"` 时填已导入的素材键）。
- 导出后可在 `job.json` 的 `compositing` 字段核对已启用的渐变映射、有机边缘、文字避让与全局质感层。


## 整幅生成后拆层
愿望本曾使用原排版生成无字整幅，再按画面拆解透明素材，按原排版叠放活字。generatedSource 指向工程 assets 内的生成原稿；materialFocus 记录默认主素材对象。用工程版本核对拆层重组，再做局部调色。素材配方 JSON 的 schema 为 cover-material/1，effects 包含 gradientMap、organic、blend 和 opacity；导入时保留目标对象的几何、图像和其余蒙版设置。

## 封面审阅与描金
在 /review?edition=orbit 或 /review?edition=echo 点选封面后提交意见。意见的 target 标识对象，purpose 记录所见版本与毫米位置。接单后先读取当前版本、意见与锁，提交局部修改，在 reply 中写明结果。金线使用独立 linework 对象与 foil=true；导出 FOIL.svg 与 ART.svg 同原点。布局已选定，先保持跨脊曲线、书名位置与图幅关系。

## 构成风续作
愿望本「回望之弧」及用户指定使用构成风的任务，采用 notebook-design 技能中的构成式分支。若本机已有完整愿望本工程，再读取工程内的《构成风续作.md》。接手时读取当前工程版本。该款采用原材单独加工后拼贴的流程。
