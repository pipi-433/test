# 灵境导游设计规范

## 游客端 UI-01 基线

本阶段游客端以 `docs/ui-references/` 内样图为视觉基准，目标是样图级复刻，不再自由发挥成营销首页或长功能堆叠页。

### 设计语气

- 安静、可信、文化感、工具化。
- 主色使用湖水绿 / 深松绿，强调色使用铜金 / 佛教金。
- 背景以象牙白、浅砂色、轻灰和墨色文字为主。
- 禁止紫色主色、装饰性渐变圆点、结构性 emoji、卡片套卡片。

### 游客端分页

底部固定导航为 5 个真实 tab：

- 推荐
- 游灵山
- 识景
- 路线
- 我的

点击底部 tab 只切换状态，不用 `scrollIntoView` 冒充分页。每个 tab 只显示自己的主要任务内容。

### 图标

主要文化图标和底部导航优先使用透明 PNG：

- `frontend/public/assets/icons/lingshan/*.png`
- 通过 `ImageIcon` / `LingshanImageIcons.tsx` 接入。
- 常用尺寸为 24px、28px、32px，保持等比，不拉伸。
- SVG 仅作为后续 fallback 或非文化小图标使用。

### 触控

- 手机触控目标不小于 44px。
- 底部导航整块 tab 可点击，不只点击图标或文字。
- 固定底栏需要给页面内容预留底部空间，不能遮挡主按钮。

## Visitor Visual Tokens UI-04

The visitor mobile UI follows a warm new-Chinese scenic guide direction:

- Primary pine green: `#1F5B4A`.
- Deep pine green: `#123D33`.
- Soft green background: `#DDEBE4` / `#EEF5F0`.
- App background: `#F7F3EA`, with the bottom kept lighter as `#FBFAF6`.
- Card surface: `#FFFDF8`.
- Warm border: `#E8DFD0`.
- Buddhist gold accent: `#B89A5E`.
- Main text: `#263B34`.
- Secondary text: `#7A817B`.

Do not use bright technology green such as `#00B050`, `#00C853`, or `#1ABC9C` for the visitor side.

Radius guidance for visitor UI:

- Large hero/panel surfaces: `20px` to `24px`.
- Normal cards: `16px`.
- Buttons and inputs: `12px` to `16px`.
- Bottom navigation active block: `12px` to `14px`.
- Small tags: `8px` to `10px`.
